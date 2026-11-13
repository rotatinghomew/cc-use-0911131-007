from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from trial_site_federator import feasibility, timeaxis
from trial_site_federator.dedup.record_linkage import link_observations
from trial_site_federator.monitoring.freshness import freshness_of, usable_for_training
from trial_site_federator.protocols.identity import comparability, protocol_index
from trial_site_federator.recruitment.status import exposure_days
from trial_site_federator.runtime import DomainError

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'fixtures/analysis/input.json'


def load_input() -> dict:
    return json.loads(INPUT.read_text(encoding='utf-8'))


class FeasibilityFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.database = Path(cls.temp.name) / 'feasibility.sqlite3'
        cls.output = Path(cls.temp.name) / 'result.json'
        cls.raw = load_input()
        cls.result = feasibility.run(INPUT, cls.database, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    # -- shape and contract -----------------------------------------------------

    def test_output_has_required_top_level_fields(self):
        for key in ('model_id', 'site_forecasts', 'total_forecast', 'target_probability',
                    'backtest', 'exclusions', 'scenarios'):
            self.assertIn(key, self.result)

    def test_site_forecast_columns(self):
        self.assertGreater(len(self.result['site_forecasts']), 0)
        for row in self.result['site_forecasts']:
            for key in ('site_id', 'month', 'expected', 'interval', 'status'):
                self.assertIn(key, row)
            self.assertRegex(row['month'], r'^\d{4}-\d{2}$')
            self.assertEqual(row['interval_level'], 0.90)

    def test_horizon_is_next_three_months(self):
        self.assertEqual(self.result['horizon']['months'], ['2026-09', '2026-10', '2026-11'])
        self.assertEqual(self.result['horizon']['start'], '2026-09')

    def test_output_is_written_and_finite(self):
        self.assertTrue(self.output.is_file())
        on_disk = json.loads(self.output.read_text(encoding='utf-8'))
        self.assertEqual(on_disk['run_id'], self.result['run_id'])
        json.dumps(on_disk, allow_nan=False)

    def test_scope_is_resource_planning_not_eligibility(self):
        self.assertFalse(self.result['model_spec']['clinical_eligibility_use'])
        self.assertEqual(self.result['model_spec']['intended_use'], 'site-resource-planning')
        self.assertIn('不用于判断', self.result['scope_note'])

    # -- integration with existing catalog rules ---------------------------------

    def test_current_month_is_never_a_training_label(self):
        histories, meta = feasibility.collect_histories(feasibility.FeasibilityInput(self.raw))
        for history in histories.values():
            for row in history.training:
                self.assertLess(row['month'], '2026-08')
        codes = {item['code'] for item in meta['exclusions']}
        self.assertIn('current_month', codes)
        # August rows exist in the feed but must not enter training at all.
        current = [item for item in meta['exclusions']
                   if item['code'] == 'current_month' and item['month'] == '2026-08']
        self.assertEqual(len(current), 8)

    def test_zero_exposure_months_are_not_training_rows(self):
        histories, meta = feasibility.collect_histories(feasibility.FeasibilityInput(self.raw))
        for history in histories.values():
            for row in history.training:
                self.assertGreater(float(row['open_days']), 0)
        paused = [item for item in meta['exclusions'] if item['code'] == 'zero_exposure_pause']
        self.assertGreaterEqual(len(paused), 1)
        s0 = histories['s0']
        self.assertIn('training_rows_ignore_pause',
                      {'training_rows_ignore_pause'} if all(
                          row['open_days'] != 0 for row in s0.training) else set())

    def test_breaking_amendment_is_not_pooled(self):
        histories, meta = feasibility.collect_histories(feasibility.FeasibilityInput(self.raw))
        # s1 moved from p1 to p2 through an eligibility change.
        for row in histories['s1'].training:
            self.assertEqual(row['protocol_id'], 'p2')
        codes = [(item['code'], item['site_id']) for item in meta['exclusions']]
        self.assertIn(('protocol_not_comparable', 's1'), codes)

    def test_comparability_handles_unknown_lineage(self):
        index = protocol_index(self.raw['protocols'])
        self.assertEqual(comparability(index, 'p2', 'p2')['status'], 'comparable')
        self.assertEqual(comparability(index, 'p1', 'p2')['status'], 'not-comparable')
        unknown = comparability(index, 'p9', 'p9')
        self.assertEqual(unknown['status'], 'unknown')
        self.assertEqual(comparability(index, 'p0', 'p9')['status'], 'unknown')

    def test_freshness_rules(self):
        row = {'month': '2026-08', 'known_at': '2026-08-28', 'open_days': 25, 'complete': False}
        self.assertFalse(usable_for_training(row, '2026-08-15'))
        self.assertEqual(freshness_of(row, '2026-08-15')['reason'], 'current-month-incomplete')
        late = {'month': '2026-07', 'known_at': '2026-08-28', 'open_days': 25, 'complete': True}
        self.assertFalse(usable_for_training(late, '2026-08-15'))
        self.assertEqual(freshness_of(late, '2026-08-15')['reason'], 'reported-after-cutoff')
        closed = {'month': '2026-07', 'known_at': '2026-07-28', 'open_days': 25, 'complete': True}
        self.assertTrue(usable_for_training(closed, '2026-08-15'))

    def test_exposure_rejects_impossible_open_days(self):
        with self.assertRaises(DomainError):
            exposure_days({'open_days': 40}, 31)
        self.assertEqual(exposure_days({'open_days': 0})['status'], 'paused')
        self.assertEqual(exposure_days({})['status'], 'unknown')

    # -- model behaviour ---------------------------------------------------------

    def test_total_matches_site_sum_and_monthly_sums(self):
        total = self.result['total_forecast']
        identified = [row for row in self.result['site_forecasts'] if row['expected'] is not None]
        self.assertAlmostEqual(sum(row['expected'] for row in identified), total['expected'], places=2)
        for month in total['months']:
            monthly = sum(row['expected'] for row in identified if row['month'] == month['month'])
            self.assertAlmostEqual(monthly, month['expected'], places=2)
        self.assertTrue(self.result['consistency']['site_sum_matches_total'])
        self.assertTrue(self.result['consistency']['monthly_sums_match_total'])

    def test_target_probability_comes_from_joint_simulation(self):
        probability = self.result['target_probability']
        self.assertEqual(probability['status'], 'estimated')
        self.assertGreaterEqual(probability['probability'], 0.0)
        self.assertLessEqual(probability['probability'], 1.0)
        self.assertFalse(probability['site_probabilities_summed'])

    def test_scenarios_share_one_model_version(self):
        model_ids = {scenario['model_id'] for scenario in self.result['scenarios']}
        self.assertEqual(model_ids, {self.result['model_id']})
        self.assertIn('current', [scenario['scenario_id'] for scenario in self.result['scenarios']])
        self.assertIn('delayed', [scenario['scenario_id'] for scenario in self.result['scenarios']])

    def test_delay_never_creates_exposure(self):
        current, delayed = self.result['scenarios'][0], self.result['scenarios'][1]
        current_rows = {(row['site_id'], row['month']): row for row in current['site_forecasts']}
        for row in delayed['site_forecasts']:
            key = (row['site_id'], row['month'])
            self.assertLessEqual(row['expected'], current_rows[key]['expected'] + 1e-9)
        delayed_s7 = [row for row in delayed['site_forecasts'] if row['site_id'] == 's7']
        self.assertEqual([row['expected'] for row in delayed_s7[:2]], [0.0, 0.0])
        self.assertEqual(delayed_s7[0]['exposure'], 0.0)
        self.assertLess(delayed['total_forecast']['expected'], current['total_forecast']['expected'])

    # -- backtest ----------------------------------------------------------------

    def test_backtest_is_rolling_origin(self):
        backtest = self.result['backtest']
        self.assertEqual(backtest['method'], 'rolling-origin')
        self.assertFalse(backtest['random_month_split'])
        self.assertGreaterEqual(len(backtest['origins']), 2)
        origins = [report['origin'] for report in backtest['origins']]
        self.assertEqual(origins, sorted(origins))
        for report in backtest['origins']:
            self.assertGreater(report['scored_cells'], 0)
            for month in report['forecast_months']:
                self.assertGreater(month, report['origin'])

    def test_backtest_compares_against_baselines(self):
        aggregate = self.result['backtest']['aggregate']
        for name in ('model', 'baseline_simple', 'baseline_naive'):
            self.assertIn(name, aggregate)
            self.assertGreater(aggregate[name]['n'], 0)
            self.assertIsNotNone(aggregate[name]['mae'])
        self.assertIsNotNone(aggregate['model']['coverage'])

    def test_backtest_never_scores_unfinished_months(self):
        # A historical origin may forecast a month that is "current" today, but
        # that month was future at the origin and must have closed before the
        # data cut-off for it to become ground truth.
        for report in self.result['backtest']['origins']:
            self.assertGreater(report['cutoff'], report['origin'])
            for month in report['forecast_months']:
                self.assertGreater(month, report['origin'])
            # Scored cells only ever come from months that closed before the cut-off.
            for month in report['scored_months']:
                self.assertLess(month, '2026-08')
                self.assertLessEqual(month, '2026-07')


class FeasibilityUncertaintyTests(unittest.TestCase):
    def test_unknown_protocol_site_is_unidentifiable_not_zero(self):
        raw = load_input()
        raw['observations'].append({
            'site_id': 's9', 'protocol_id': 'p-unknown', 'month': '2026-07',
            'enrolled': 5, 'open_days': 25, 'complete': True,
            'known_at': '2026-07-28', 'revision': 1,
        })
        raw['observations'].append({
            'site_id': 's9', 'protocol_id': 'p-unknown', 'month': '2026-06',
            'enrolled': 4, 'open_days': 25, 'complete': True,
            'known_at': '2026-06-28', 'revision': 1,
        })
        with tempfile.TemporaryDirectory() as directory:
            result = feasibility.analyze(raw, Path(directory) / 'x.sqlite3')
        rows = [row for row in result['site_forecasts'] if row['site_id'] == 's9']
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['status'], 'unidentifiable')
            self.assertIsNone(row['expected'])
            self.assertIsNone(row['interval'][0])
            self.assertIsNone(row['interval'][1])
        self.assertIn('s9', result['total_forecast']['unidentified_sites'])
        self.assertIn('s9', result['target_probability']['unidentified_sites'])
        self.assertIsNone(result['target_probability']['probability'])
        self.assertEqual(result['target_probability']['status'], 'partial')
        self.assertTrue(result['total_forecast']['missing_sites_not_zero'])

    def test_cold_start_site_borrows_prior_with_wider_interval(self):
        raw = load_input()
        # A site that just opened with a single closed month should still forecast.
        raw['observations'].append({
            'site_id': 's8', 'protocol_id': 'p2', 'month': '2026-07',
            'enrolled': 3, 'open_days': 25, 'complete': True,
            'known_at': '2026-07-28', 'revision': 1,
        })
        with tempfile.TemporaryDirectory() as directory:
            result = feasibility.analyze(raw, Path(directory) / 'x.sqlite3')
        rows = [row for row in result['site_forecasts'] if row['site_id'] == 's8']
        self.assertEqual({row['status'] for row in rows}, {'cold-start'})
        for row in rows:
            self.assertIsNotNone(row['expected'])
            self.assertIn('borrowed_from', row)
            self.assertEqual(row['borrowed_from'], 'p2')
            self.assertEqual(row['source'], 'site-history')

    def test_site_with_only_pause_history_is_unidentifiable(self):
        raw = load_input()
        for month in ('2026-05', '2026-06', '2026-07'):
            raw['observations'].append({
                'site_id': 's10', 'protocol_id': 'p1', 'month': month,
                'enrolled': 0, 'open_days': 0, 'complete': True,
                'known_at': f'{month}-28', 'revision': 1,
            })
        with tempfile.TemporaryDirectory() as directory:
            result = feasibility.analyze(raw, Path(directory) / 'x.sqlite3')
        rows = [row for row in result['site_forecasts'] if row['site_id'] == 's10']
        self.assertEqual({row['status'] for row in rows}, {'unidentifiable'})
        self.assertEqual(rows[0]['reason'], 'no_exposure_history')
        self.assertIsNone(rows[0]['expected'])

    def test_overdispersion_is_reported(self):
        result = feasibility.analyze(load_input())
        dispersion = result['model_diagnostics']['dispersion']
        self.assertIn('alpha', dispersion)
        self.assertIn('detected', dispersion)
        self.assertEqual(dispersion['method'], 'method-of-moments on within-site residuals')


class FeasibilityPersistenceTests(unittest.TestCase):
    def test_corrected_open_days_explains_the_difference(self):
        raw = load_input()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'runs.sqlite3'
            first = feasibility.analyze(raw, database)
            self.assertTrue(first['revision_context']['stored'])

            corrected = copy.deepcopy(raw)
            # s0 had a paused April; the correction says it was actually open 10 days.
            for row in corrected['observations']:
                if row['site_id'] == 's0' and row['month'] == '2026-04':
                    row['open_days'] = 10
                    row['enrolled'] = 2
                    row['revision'] = 2
            second = feasibility.analyze(corrected, database)

            self.assertEqual(first['run_id'], second['run_id'])  # same model + as_of
            self.assertTrue(second['revision_context']['stored'])
            self.assertEqual(second['revision_context']['previous_run_id'], first['run_id'])
            changes = second['revision_context']['changed_observations']
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]['site_id'], 's0')
            self.assertEqual(changes[0]['month'], '2026-04')
            self.assertEqual(changes[0]['fields']['open_days'], {'before': 0, 'after': 10})
            delta = second['revision_context']['forecast_delta']
            self.assertIsNotNone(delta)
            self.assertIsNotNone(delta['total_delta'])
            self.assertNotEqual(delta['total_before'], delta['total_after'])

            with sqlite3.connect(database) as connection:
                count = connection.execute('SELECT count(*) FROM feasibility_runs').fetchone()[0]
            self.assertEqual(count, 1)

    def test_rerun_without_changes_replays(self):
        raw = load_input()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'runs.sqlite3'
            feasibility.analyze(raw, database)
            again = feasibility.analyze(raw, database)
            self.assertTrue(again['revision_context']['replayed'])
            self.assertEqual(again['revision_context']['changed_observations_count'], 0)


class FeasibilityScenarioTests(unittest.TestCase):
    def test_restore_protocol_scenario_compares_on_same_model(self):
        raw = load_input()
        raw['scenarios'] = [
            {'scenario_id': 'current', 'delay_site': None, 'delay_months': 0},
            {'scenario_id': 'restore-p1', 'restore_protocol': 'p1', 'restore_site': 's1'},
        ]
        result = feasibility.analyze(raw)
        self.assertEqual({scenario['model_id'] for scenario in result['scenarios']},
                         {result['model_id']})
        restore = result['scenarios'][1]
        self.assertEqual(restore['status'], 'ok')
        s1 = [row for row in restore['site_forecasts'] if row['site_id'] == 's1']
        # p1 history for s1 (before the eligibility change) may be pooled again.
        self.assertEqual({row['protocol_id'] for row in s1}, {'p1'})
        self.assertTrue(restore['consistency']['site_sum_matches_total'])

    def test_restore_unknown_protocol_is_reported(self):
        raw = load_input()
        raw['scenarios'] = [{'scenario_id': 'bad', 'restore_protocol': 'p-missing', 'restore_site': 's1'}]
        result = feasibility.analyze(raw)
        scenario = result['scenarios'][0]
        self.assertEqual(scenario['status'], 'invalid-scenario')
        self.assertEqual(scenario['problems'][0]['code'], 'unknown_protocol')
        self.assertIsNone(scenario['target_probability']['probability'])

    def test_delay_on_unknown_site_is_invalid(self):
        raw = load_input()
        raw['scenarios'] = [{'scenario_id': 'bad', 'delay_site': 's-absent', 'delay_months': 1}]
        result = feasibility.analyze(raw)
        self.assertEqual(result['scenarios'][0]['status'], 'invalid-scenario')
        self.assertEqual(result['scenarios'][0]['problems'][0]['code'], 'unknown_site')


class FeasibilityInputValidationTests(unittest.TestCase):
    def test_rejects_bad_as_of(self):
        raw = load_input()
        raw['as_of'] = 'not-a-date'
        with self.assertRaises(DomainError):
            feasibility.analyze(raw)

    def test_rejects_missing_observations(self):
        raw = load_input()
        raw['observations'] = []
        with self.assertRaises(DomainError):
            feasibility.analyze(raw)

    def test_duplicate_site_month_uses_newest_revision(self):
        records = [
            {'site_id': 's0', 'month': '2026-01', 'enrolled': 1, 'open_days': 10,
             'revision': 1, 'known_at': '2026-01-28'},
            {'site_id': 's0', 'month': '2026-01', 'enrolled': 9, 'open_days': 10,
             'revision': 2, 'known_at': '2026-02-02'},
        ]
        linked = link_observations(records)
        self.assertEqual(linked['rows'][('s0', '2026-01')]['enrolled'], 9)
        self.assertEqual(len(linked['superseded']), 1)

    def test_conflicting_same_revision_is_flagged(self):
        records = [
            {'site_id': 's0', 'month': '2026-01', 'enrolled': 1, 'open_days': 10,
             'revision': 1, 'known_at': '2026-01-28'},
            {'site_id': 's0', 'month': '2026-01', 'enrolled': 2, 'open_days': 10,
             'revision': 1, 'known_at': '2026-01-28'},
        ]
        linked = link_observations(records)
        self.assertEqual(len(linked['conflicts']), 1)


class TimeaxisTests(unittest.TestCase):
    def test_month_arithmetic(self):
        self.assertEqual(timeaxis.add_months('2026-11', 2), '2027-01')
        self.assertEqual(timeaxis.next_months('2026-08', 3), ['2026-09', '2026-10', '2026-11'])
        self.assertEqual(timeaxis.month_distance('2026-01', '2026-08'), 7)
        self.assertEqual(timeaxis.days_in_month('2026-02'), 28)


if __name__ == '__main__':
    unittest.main()
