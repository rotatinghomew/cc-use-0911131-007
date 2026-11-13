"""Recruitment feasibility by site and month, for site-resource planning only.

This module answers one operational question: given what the federated catalog
knows at a cut-off date, how many additional participants should each site be
expected to enrol over the next three months, and how likely is the programme to
reach its remaining target?  It is explicitly **not** a clinical eligibility
decision: nothing here may be used to decide whether a person fits a trial.

Design choices, all reported in the output so a planner can audit them:

* Exposure, not calendar months.  Recruitment is modelled per open site-day.
  Paused months (``open_days == 0``) are real observations about a pause but
  contribute no exposure, so they are excluded from rate fitting instead of being
  read as "this site recruits nobody".
* Only closed, reported, complete months train the model.  The current unfinished
  month is right-censored and never used as a label; records reported after the
  cut-off are invisible, matching the freshness catalog.
* A protocol amendment is only pooled across when the catalog pedigree says the
  change did not move the eligible population.  Unknown pedigree and breaking
  amendments are reported separately and never silently merged.
* Partial pooling across sites and protocol segments handles cold starts; a site
  with no own history borrows a segment/project prior with a wider interval
  rather than being assigned zero.
* Counts are negative-binomial when overdispersion is detected, and Poisson with
  rate uncertainty when it is not.  The dispersion estimate is reported.
* The project total and target probability come from one joint simulation that
  shares segment uncertainty across sites, so scenario totals are internally
  consistent and per-site probabilities are never summed.

The analysis stores each run in the supplied SQLite database.  Re-running after
correcting an earlier month produces a new run that records which inputs changed
and how the forecast moved, so a planner can explain the difference.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from trial_site_federator import timeaxis
from trial_site_federator.dedup.record_linkage import known_by, link_observations
from trial_site_federator.monitoring.freshness import freshness_of, usable_for_training
from trial_site_federator.protocols.identity import (
    comparability,
    lineage_chain,
    normalize_change_type,
    protocol_index,
)
from trial_site_federator.recruitment.status import exposure_days, exposure_summary
from trial_site_federator.runtime import DomainError, fingerprint, normalize_text, stable_json

ANALYSIS_NAME = 'recruitment_feasibility'
ANALYSIS_VERSION = '1.0'
HORIZON_MONTHS = 3
INTERVAL_LEVEL = 0.90
LOWER_QUANTILE = (1.0 - INTERVAL_LEVEL) / 2.0
UPPER_QUANTILE = 1.0 - LOWER_QUANTILE
TOTAL_DRAWS = 12000
BACKTEST_DRAWS = 1500
BACKTEST_ORIGINS = 4
BACKTEST_MIN_TRAINING_ROWS = 8
COLD_START_EXPOSURE = 1.5
MAX_ALPHA = 2.0
MAX_EXCLUSION_ITEMS = 500

MODEL_SPEC: dict[str, Any] = {
    'analysis': ANALYSIS_NAME,
    'version': ANALYSIS_VERSION,
    'intended_use': 'site-resource-planning',
    'clinical_eligibility_use': False,
    'horizon_months': HORIZON_MONTHS,
    'rate_unit': 'enrolments per open-day',
    'exposure_unit': 'open_days / 30',
    'recency_half_life_months': 3.0,
    'segment_shrinkage': 2.0,
    'site_shrinkage': 1.0,
    'dispersion': 'NB2 method-of-moments alpha, Poisson fallback',
    'interval_level': INTERVAL_LEVEL,
    'simulation_draws': TOTAL_DRAWS,
    'random_seed': 37,
    'total_probability': 'joint simulation with shared segment uncertainty',
    'backtest': 'rolling-origin expanding window, no random month split',
}
MODEL_ID = f"feas-{ANALYSIS_VERSION}-{fingerprint(MODEL_SPEC)[:12]}"

DISCLAIMER = ('仅用于安排中心资源与招募计划；不用于判断个人是否符合临床条件。'
              'Site-resource planning only; not a clinical eligibility determination.')

EXCLUSION_EXPLANATIONS = {
    'known_after_cutoff': '记录上报日晚于 as_of，按资料时效规则不进入本次分析。',
    'future_month': '月份晚于 as_of 所在月份，属于未来观察。',
    'incomplete_month': '该月观察尚未结束，累计值会被右删失，不能作为训练标签。',
    'invalid_open_days': 'open_days 非法（负数或超过当月天数），按输入错误剔除并记录。',
    'current_month': 'as_of 当月尚未结束，不能拿最终累计值训练或当作真值。',
    'zero_exposure_pause': '开放天数为零的停招/未开月，可作为停顿事实，但不能估计每开放日速率。',
    'missing_open_days': '缺少 open_days，曝光未知（不等于零曝光）。',
    'protocol_not_comparable': '协议修订改变了人群，历史计数不可与当前协议合并。',
    'unknown_lineage': '协议谱系不完整或修订类型未知，无法确认可否合并。',
    'duplicate_superseded': '同一中心月份的旧修订被较新修订覆盖。',
    'conflicting_observation': '同一中心月份同修订号出现不一致内容，已标记冲突。',
    'no_known_protocol': '截至 as_of 没有可用于确定当前协议的中心月份记录。',
    'no_closed_month': '截至 as_of 没有已结束的中心月份，只有开放计划；不把首次开放当作既有招募能力。',
    'no_site_history': '本中心没有可用自身历史，采用分段/项目先验收缩，区间相应放宽。',
    'short-history': '本中心可用曝光很少（新开或刚恢复），按分段/项目先验收缩借力，区间相应放宽。',
    'no-comparable-history': '本中心历史与当前协议不可合并，只能按分段先验借力，无法使用自身历史。',
    'non_ancestor_protocol': '计划恢复的协议不是该中心当前协议的祖先，不能按该协议合并历史。',
    'delay_beyond_horizon': '延后开放覆盖了整个预测窗口，该中心窗口内没有可招募曝光。',
    'unregistered-protocol': '当前协议不在目录谱系中，只能按同协议字符串合并历史，需人工确认。',
    'incomplete-lineage': '当前协议的父级谱系不完整，跨修订合并已停止。',
    'no_exposure_history': '本中心历史没有任何开放日，无法区分“从未开放”和“停招”，不按零人计。',
    'paused_site': '中心最近一个已结束月份停招，基准情景假设停顿延续，属保守假设而非能力为零。',
    'unknown_site': '计划中的中心不在现有目录内。',
    'unknown_protocol': '计划恢复的协议不在现有谱系内。',
    'non_ancestor_protocol': '计划恢复的协议不是该中心当前协议的祖先。',
    'delay_beyond_horizon': '延后月数覆盖整个预测窗口，该中心在窗口内没有可招募曝光。',
}

STATUS_NOTES = {
    'ok': '基于本中心可用历史估计。',
    'cold-start': '本中心可用曝光不足，按协议分段/项目先验收缩借力。',
    'paused': '最近月份停招；基准情景假设停顿延续，期望为 0 但招募能力非零。',
    'delayed': '计划延后开放，该月无可用曝光，期望为 0。',
    'unidentifiable': '证据不足或谱系不明，拒绝给出数值。',
}


# --------------------------------------------------------------------------- input


class FeasibilityInput:
    def __init__(self, raw: Mapping[str, Any]):
        if not isinstance(raw, Mapping):
            raise DomainError('input must be an object')
        self.raw = dict(raw)
        self.as_of = normalize_text(raw.get('as_of'), 'as_of', 40)
        if not self.as_of:
            raise DomainError('as_of is required')
        self.as_of_date = timeaxis.parse_date(self.as_of)
        self.current_month = self.as_of[:7]
        self.remaining_target = _number(raw.get('remaining_target'), 'remaining_target', minimum=0.0)
        self.seed = int(_number(raw.get('seed', MODEL_SPEC['random_seed']), 'seed', minimum=0.0))
        observations = raw.get('observations')
        if not isinstance(observations, list) or not observations:
            raise DomainError('observations must be a non-empty list')
        self.observations = observations
        protocols = raw.get('protocols', [])
        if not isinstance(protocols, list):
            raise DomainError('protocols must be a list')
        self.protocols = protocols
        self.protocol_index = protocol_index(protocols)
        scenarios = raw.get('scenarios') or [{'scenario_id': 'current', 'delay_site': None, 'delay_months': 0}]
        if not isinstance(scenarios, list):
            raise DomainError('scenarios must be a list')
        self.scenarios = scenarios
        self.input_digest = fingerprint(self.snapshot())

    def snapshot(self) -> dict[str, Any]:
        return {
            'as_of': self.as_of,
            'remaining_target': self.remaining_target,
            'observations': self.observations,
            'protocols': self.protocols,
            'scenarios': self.scenarios,
        }


def _number(value: Any, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise DomainError(f'{name} must be numeric')
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise DomainError(f'{name} must be numeric') from None
    if not math.isfinite(number):
        raise DomainError(f'{name} must be finite')
    if minimum is not None and number < minimum:
        raise DomainError(f'{name} must be >= {minimum}')
    return number


def _int(value: Any, name: str, minimum: int = 0) -> int:
    number = _number(value, name, minimum=float(minimum))
    if number != int(number):
        raise DomainError(f'{name} must be a whole number')
    return int(number)


# ------------------------------------------------------------------- observations


class SiteHistory:
    def __init__(self, site_id: str):
        self.site_id = site_id
        self.current_protocol: str | None = None
        self.current_protocol_known = False
        self.rows: list[dict] = []
        self.training: list[dict] = []
        self.exclusions: list[dict] = []
        self.status = 'ok'
        self.reason = ''
        self.coherence_problem = ''
        self.exposure_assumption: float | None = None
        self.exposure_borrowed = False
        self.currently_paused = False
        self.latest_month: str | None = None


def _record_view(record: Mapping[str, Any]) -> dict:
    return {
        'site_id': normalize_text(record.get('site_id'), 'site_id', 96),
        'month': normalize_text(record.get('month'), 'month', 20),
        'protocol_id': normalize_text(record.get('protocol_id'), 'protocol_id', 96),
        'enrolled': record.get('enrolled'),
        'open_days': record.get('open_days'),
        'complete': record.get('complete'),
        'known_at': normalize_text(record.get('known_at'), 'known_at', 40),
        'revision': record.get('revision'),
    }


def _exclusion(scope: str, code: str, site_id: str | None = None, month: str | None = None,
               detail: str = '', **extra: Any) -> dict:
    entry = {'scope': scope, 'code': code, 'site_id': site_id, 'month': month,
             'detail': detail or EXCLUSION_EXPLANATIONS.get(code, '')}
    entry.update(extra)
    return entry


def collect_histories(inp: FeasibilityInput) -> tuple[dict[str, SiteHistory], dict]:
    """Link, freshness-filter and protocol-filter every observation."""
    linked = link_observations(inp.observations)
    exclusions: list[dict] = []
    for item in linked['superseded']:
        exclusions.append(_exclusion('observation', 'duplicate_superseded', item['site_id'], item['month'],
                                     detail=f"revision {item['revision']} superseded",
                                     revision=item['revision']))
    for item in linked['conflicts']:
        exclusions.append(_exclusion('observation', 'conflicting_observation', item['site_id'], item['month'],
                                     detail=f"revision {item['revision']} disagrees with same revision",
                                     revision=item['revision']))

    histories: dict[str, SiteHistory] = {}
    for (site_id, month), record in sorted(linked['rows'].items()):
        view = _record_view(record)
        history = histories.setdefault(site_id, SiteHistory(site_id))
        freshness = freshness_of(view, inp.as_of)
        if freshness['status'] == 'future':
            exclusions.append(_exclusion('observation', 'future_month', site_id, month))
            continue
        if freshness['status'] == 'open':
            exclusions.append(_exclusion('observation', 'current_month', site_id, month,
                                         detail=f"as_of={inp.as_of}"))
        elif not known_by(view, inp.as_of):
            exclusions.append(_exclusion('observation', 'known_after_cutoff', site_id, month,
                                         detail=f"known_at={view['known_at']} as_of={inp.as_of}"))
            continue
        history.rows.append(view)
        history.latest_month = max(history.latest_month or month, month)

    for history in histories.values():
        _resolve_current_protocol(history, inp)
        _select_training(history, inp, exclusions)
    return histories, {'superseded': linked['superseded'], 'conflicts': linked['conflicts'],
                       'exclusions': exclusions}


def _resolve_current_protocol(history: SiteHistory, inp: FeasibilityInput) -> None:
    candidates = [row for row in history.rows if row['month'] <= inp.current_month]
    if not candidates:
        history.current_protocol_known = False
        history.status = 'unidentifiable'
        history.reason = 'no_known_protocol'
        return
    candidates.sort(key=lambda row: (row['month'], row['known_at'], str(row['revision'])))
    history.current_protocol = candidates[-1]['protocol_id']
    history.current_protocol_known = bool(history.current_protocol)
    if not history.current_protocol_known:
        history.status = 'unidentifiable'
        history.reason = 'no_known_protocol'
    return


def _select_training(history: SiteHistory, inp: FeasibilityInput, exclusions: list[dict]) -> None:
    protocol = history.current_protocol
    comparable_rows: list[dict] = []
    coherence_problem = ''
    if not history.current_protocol_known:
        for row in history.rows:
            exclusions.append(_exclusion('observation', 'no_known_protocol', history.site_id, row['month']))
        return
    for row in sorted(history.rows, key=lambda item: item['month']):
        month = row['month']
        if month >= inp.current_month:
            # Current-month rows are already recorded at ingestion; future rows
            # (planned openings) are informational for scenarios, not labels.
            if month > inp.current_month:
                exclusions.append(_exclusion('observation', 'future_month', history.site_id, month))
            continue
        freshness = freshness_of(row, inp.as_of)
        if not freshness['training_eligible']:
            exclusions.append(_exclusion('observation', freshness['reason'], history.site_id, month,
                                         detail=freshness['status']))
            continue
        if row['complete'] is not True:
            exclusions.append(_exclusion('observation', 'incomplete_month', history.site_id, month))
            continue
        try:
            exposure = exposure_days(row, timeaxis.days_in_month(month))
        except DomainError as exc:
            exclusions.append(_exclusion('observation', 'invalid_open_days', history.site_id, month,
                                         detail=str(exc)))
            continue
        if exposure['status'] == 'unknown':
            exclusions.append(_exclusion('observation', 'missing_open_days', history.site_id, month))
            continue
        if exposure['paused']:
            exclusions.append(_exclusion('observation', 'zero_exposure_pause', history.site_id, month))
            continue
        decision = comparability(inp.protocol_index, row['protocol_id'], protocol)
        if decision['status'] == 'unknown':
            exclusions.append(_exclusion('observation', 'unknown_lineage', history.site_id, month,
                                         detail=decision['reason']))
            coherence_problem = coherence_problem or decision['reason']
            continue
        if decision['status'] == 'not-comparable':
            exclusions.append(_exclusion('observation', 'protocol_not_comparable', history.site_id, month,
                                         detail=decision['reason']))
            continue
        comparable_rows.append(row)

    history.training = comparable_rows
    history.coherence_problem = coherence_problem
    # Exposure is an operational fact (how many days the site was open), not a
    # property of the eligible population, so a site's own opening pattern may
    # inform its forecast even when its counts cannot be pooled across protocols.
    operational = []
    for row in history.rows:
        if row['month'] >= inp.current_month:
            continue
        if not usable_for_training(row, inp.as_of):
            continue
        try:
            if float(row['open_days']) > 0:
                operational.append(float(row['open_days']))
        except (TypeError, ValueError):
            continue
    usable_positive = [float(row['open_days']) for row in comparable_rows if float(row['open_days']) > 0]
    reference_days = usable_positive or operational
    history.exposure_assumption = _median(reference_days) if reference_days else None
    history.exposure_borrowed = not usable_positive and bool(operational)

    paused_candidates = [row for row in history.rows if row['month'] < inp.current_month]
    if paused_candidates:
        latest = max(paused_candidates, key=lambda row: row['month'])
        try:
            history.currently_paused = exposure_days(latest)['paused']
        except DomainError:
            history.currently_paused = False

    if history.training:
        if history.currently_paused:
            history.status = 'paused'
            history.reason = 'paused_site'
        elif history.exposure_assumption is None:
            history.status = 'unidentifiable'
            history.reason = 'no_exposure_history'
        return

    # No own count can be pooled.  A site with a closed month of zero exposure is
    # unidentifiable; a site with no closed month at all is identified by the
    # prior, because "never observed" is not the same as "cannot recruit".
    if history.exposure_assumption is None:
        if any(row['code'] == 'zero_exposure_pause' for row in exclusions
               if row['site_id'] == history.site_id):
            history.status = 'unidentifiable'
            history.reason = 'no_exposure_history'
        else:
            history.status = 'unidentifiable'
            history.reason = 'no_closed_month'
        return
    if coherence_problem:
        # Unknown lineage or an unregistered protocol: the eligible population
        # cannot be established, so neither the site's own counts nor a
        # protocol-segment prior is a defensible basis for a number.
        history.status = 'unidentifiable'
        history.reason = coherence_problem
        return
    history.status = 'cold-start'
    history.reason = 'no-comparable-history'


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


# ------------------------------------------------------------------------- fitting


class ModelFit:
    def __init__(self) -> None:
        self.mu0: float | None = None
        self.segment_means: dict[str, float] = {}
        self.segment_exposure: dict[str, float] = {}
        self.segment_enrolled: dict[str, float] = {}
        self.site_means: dict[str, float] = {}
        self.site_exposure: dict[str, float] = {}
        self.site_enrolled: dict[str, float] = {}
        self.site_segment: dict[str, str] = {}
        self.site_weights: dict[str, float] = {}
        self.site_borrowed: dict[str, bool] = {}
        self.coherent: dict[str, bool] = {}
        self.alpha: float = 0.0
        self.dispersion: dict[str, Any] = {'alpha': 0.0, 'detected': False, 'method': 'none'}
        self.training_rows = 0
        self.total_exposure = 0.0
        self.total_enrolled = 0.0


def _weight(month: str, reference_month: str) -> float:
    age = timeaxis.month_distance(month, reference_month)
    if age < 0:
        return 0.0
    return 0.5 ** (age / MODEL_SPEC['recency_half_life_months'])


def fit_model(histories: Mapping[str, SiteHistory], reference_month: str) -> ModelFit:
    fit = ModelFit()
    per_site: dict[str, list[tuple[dict, float, float]]] = {}
    for site_id, history in sorted(histories.items()):
        if not history.current_protocol_known:
            continue
        segment = history.current_protocol or ''
        fit.site_segment[site_id] = segment
        fit.coherent[site_id] = not history.coherence_problem
        rows = []
        for row in history.training:
            weight = _weight(row['month'], reference_month)
            exposure = float(row['open_days']) / 30.0
            rows.append((row, weight, exposure))
        per_site[site_id] = rows
    total_exposure = sum(weight * exposure for rows in per_site.values() for _, weight, exposure in rows)
    total_enrolled = sum(weight * float(row['enrolled']) for rows in per_site.values() for row, weight, _ in rows)
    fit.training_rows = sum(len(rows) for rows in per_site.values())
    fit.total_exposure = total_exposure
    fit.total_enrolled = total_enrolled
    if total_exposure <= 0:
        return fit
    fit.mu0 = total_enrolled / total_exposure

    for site_id, rows in per_site.items():
        segment = fit.site_segment[site_id]
        exposure = sum(weight * value for _, weight, value in rows)
        enrolled = sum(weight * float(row['enrolled']) for row, weight, _ in rows)
        fit.site_exposure[site_id] = exposure
        fit.site_enrolled[site_id] = enrolled
        fit.segment_exposure[segment] = fit.segment_exposure.get(segment, 0.0) + exposure
        fit.segment_enrolled[segment] = fit.segment_enrolled.get(segment, 0.0) + enrolled

    k_segment = MODEL_SPEC['segment_shrinkage']
    for segment in set(fit.segment_exposure) | set(fit.site_segment.values()):
        exposure = fit.segment_exposure.get(segment, 0.0)
        enrolled = fit.segment_enrolled.get(segment, 0.0)
        fit.segment_means[segment] = (enrolled + k_segment * fit.mu0) / (exposure + k_segment)

    k_site = MODEL_SPEC['site_shrinkage']
    for site_id in fit.site_segment:
        segment = fit.site_segment[site_id]
        prior = fit.segment_means.get(segment, fit.mu0)
        exposure = fit.site_exposure.get(site_id, 0.0)
        enrolled = fit.site_enrolled.get(site_id, 0.0)
        fit.site_means[site_id] = (enrolled + k_site * prior) / (exposure + k_site)
        fit.site_weights[site_id] = exposure / (exposure + k_site) if exposure + k_site else 0.0
        fit.site_borrowed[site_id] = exposure <= 0 or not fit.coherent.get(site_id, True)

    fit.alpha, fit.dispersion = _estimate_dispersion(per_site, fit)
    return fit


def _estimate_dispersion(per_site: Mapping[str, list], fit: ModelFit) -> tuple[float, dict]:
    numerator = 0.0
    denominator = 0.0
    pairs = 0
    for site_id, rows in per_site.items():
        mean_rate = fit.site_means.get(site_id)
        if mean_rate is None:
            continue
        for row, _weight, exposure in rows:
            mean = mean_rate * exposure
            observed = float(row['enrolled'])
            numerator += (observed - mean) ** 2 - mean
            denominator += mean * mean
            pairs += 1
    if denominator <= 0:
        return 0.0, {'alpha': 0.0, 'detected': False, 'method': 'method-of-moments',
                     'detail': 'no informative cells'}
    raw = numerator / denominator
    alpha = min(MAX_ALPHA, max(0.0, raw))
    return alpha, {
        'alpha': round(alpha, 6),
        'raw_estimate': round(raw, 6),
        'detected': alpha > 0,
        'method': 'method-of-moments on within-site residuals',
        'detail': ('negative-binomial NB2' if alpha > 0 else
                   'no overdispersion detected; Poisson given the site rate, interval width from rate uncertainty'),
        'cells': pairs,
    }


# ---------------------------------------------------------------------- simulation


def _poisson(rng: random.Random, mean: float) -> int:
    if mean <= 0:
        return 0
    if mean < 30:
        limit = math.exp(-mean)
        count = 0
        product = rng.random()
        while product > limit:
            count += 1
            product *= rng.random()
        return count
    # Normal approximation is adequate for large means and keeps the simulation fast.
    return max(0, int(round(rng.gauss(mean, math.sqrt(mean)))))


def _count_draw(rng: random.Random, mean: float, alpha: float) -> int:
    if mean <= 0:
        return 0
    if alpha > 0:
        gamma_mean = rng.gammavariate(1.0 / alpha, alpha * mean)
        return _poisson(rng, gamma_mean)
    return _poisson(rng, mean)


class SitePlan:
    """How one site is forecast under one scenario."""

    def __init__(self, site_id: str, protocol: str | None, mean_rate: float | None,
                 exposure: list[float | None], status: str, reason: str,
                 segment: str | None, borrowed: str | None,
                 prior_strength: float = 1.0, source: str = 'site-history'):
        self.site_id = site_id
        self.protocol = protocol
        self.mean_rate = mean_rate
        self.exposure = exposure
        self.status = status
        self.reason = reason
        self.segment = segment
        self.borrowed = borrowed
        self.prior_strength = prior_strength
        self.source = source

    @property
    def identified(self) -> bool:
        return self.mean_rate is not None and all(value is not None for value in self.exposure)


def simulate(plans: Sequence[SitePlan], months: Sequence[str], fit: ModelFit,
             draws: int, rng: random.Random) -> dict:
    """Jointly simulate all sites so the total and its probability are coherent.

    Segment means are redrawn once per iteration and shared by every site in the
    segment; site rates are then drawn from their partial-pooling posterior.  The
    total is the sum of the same draws, never the sum of separately computed
    probabilities, and a site that borrows a prior gets a wider rate interval
    instead of a narrower one.
    """
    identified = [plan for plan in plans if plan.identified]
    site_month_draws = {plan.site_id: [[] for _ in months] for plan in identified}
    monthly_totals: list[list[float]] = [[] for _ in months]
    grand_totals: list[float] = []
    alpha = fit.alpha
    if not identified or draws <= 0:
        return {'site_month_draws': site_month_draws,
                'site_totals': {plan.site_id: [] for plan in identified},
                'monthly_totals': monthly_totals, 'grand_totals': grand_totals, 'draws': 0}

    for _ in range(draws):
        segment_multiplier: dict[str, float] = {}
        for segment, mean in fit.segment_means.items():
            exposure = fit.segment_exposure.get(segment, 0.0)
            shape = exposure + MODEL_SPEC['segment_shrinkage']
            if shape <= 0 or mean <= 0:
                segment_multiplier[segment] = 1.0
                continue
            drawn = rng.gammavariate(shape, mean / shape)
            segment_multiplier[segment] = drawn / mean
        total = 0
        for index in range(len(months)):
            monthly = 0
            for plan in identified:
                rate = plan.mean_rate * segment_multiplier.get(plan.segment or '', 1.0)
                exposure = plan.exposure[index] or 0.0
                if exposure <= 0 or rate <= 0:
                    count = 0
                else:
                    # Rate uncertainty: own effective exposure plus the borrowed
                    # prior strength.  Borrowing means a smaller shape, hence a
                    # wider interval, not a tighter one.
                    shape = max(0.25, plan.prior_strength / (1.0 + alpha * rate))
                    rate_draw = rng.gammavariate(shape, rate / shape)
                    count = _count_draw(rng, rate_draw * exposure, alpha)
                site_month_draws[plan.site_id][index].append(count)
                monthly += count
            monthly_totals[index].append(monthly)
            total += monthly
        grand_totals.append(total)
    site_totals = {
        plan.site_id: [sum(values[index] for values in site_month_draws[plan.site_id])
                       for index in range(draws)]
        for plan in identified
    }
    return {'site_month_draws': site_month_draws, 'site_totals': site_totals,
            'monthly_totals': monthly_totals, 'grand_totals': grand_totals,
            'draws': draws}


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def _interval(values: Sequence[float]) -> list[float]:
    return [round(_quantile(values, LOWER_QUANTILE), 3), round(_quantile(values, UPPER_QUANTILE), 3)]


# ---------------------------------------------------------------------- scenarios


def _scenario_specs(inp: FeasibilityInput) -> list[dict]:
    specs = []
    for index, raw in enumerate(inp.scenarios):
        if not isinstance(raw, Mapping):
            raise DomainError('scenario entries must be objects')
        scenario_id = normalize_text(raw.get('scenario_id'), 'scenario_id', 96) or f'scenario-{index + 1}'
        specs.append({
            'scenario_id': scenario_id,
            'delay_site': normalize_text(raw.get('delay_site'), 'delay_site', 96) or None,
            'delay_months': _int(raw.get('delay_months', 0), 'delay_months'),
            'restore_protocol': raw.get('restore_protocol', False),
            'restore_site': normalize_text(raw.get('restore_site'), 'restore_site', 96) or None,
        })
    if not specs:
        specs.append({'scenario_id': 'current', 'delay_site': None, 'delay_months': 0,
                      'restore_protocol': False, 'restore_site': None})
    return specs


def _restore_target(inp: FeasibilityInput, history: SiteHistory, spec: Mapping[str, Any]) -> tuple[str | None, str]:
    requested = spec.get('restore_protocol')
    if not requested:
        return None, ''
    if requested is True:
        chain = lineage_chain(inp.protocol_index, history.current_protocol or '')
        root = chain[-1]['protocol_id'] if chain else None
        if root is None:
            return None, 'unknown_lineage'
        return root, ''
    protocol_id = normalize_text(requested, 'restore_protocol', 96)
    chain = lineage_chain(inp.protocol_index, history.current_protocol or '')
    if any(entry.get('missing') for entry in chain):
        return None, 'unknown_lineage'
    if protocol_id not in inp.protocol_index:
        return None, 'unknown_protocol'
    if protocol_id not in [entry['protocol_id'] for entry in chain]:
        return None, 'non_ancestor_protocol'
    return protocol_id, ''


def _scenario_plan(inp: FeasibilityInput, spec: Mapping[str, Any], histories: Mapping[str, SiteHistory],
                   fit: ModelFit, months: Sequence[str]) -> tuple[list[SitePlan], list[dict]]:
    """Turn each site's fitted rate into this scenario's exposure calendar.

    Delaying a site only removes exposure.  It never adds open days, never
    changes the fitted rate, and never borrows exposure from another site, so a
    delay can only hold or lower that site's expected enrolments.
    """
    plans: list[SitePlan] = []
    problems: list[dict] = []
    delay_site = spec['delay_site']
    delay_months = spec['delay_months']
    restore_protocol = spec['restore_protocol']
    restore_site = spec['restore_site']

    if delay_site and delay_site not in histories:
        problems.append(_exclusion('scenario', 'unknown_site', delay_site, detail=spec['scenario_id']))
    if restore_site and restore_site not in histories:
        problems.append(_exclusion('scenario', 'unknown_site', restore_site, detail=spec['scenario_id']))
    if restore_protocol not in (False, True, None):
        protocol_id = normalize_text(restore_protocol, 'restore_protocol', 96)
        if protocol_id not in inp.protocol_index:
            problems.append(_exclusion('scenario', 'unknown_protocol', restore_site, detail=protocol_id))
    if problems:
        return [], problems

    k_site = MODEL_SPEC['site_shrinkage']
    for site_id, history in sorted(histories.items()):
        segment = fit.site_segment.get(site_id)
        restore_applies = bool(restore_protocol) and (restore_site is None or restore_site == site_id)
        protocol = history.current_protocol
        source = 'site-history'
        own_strength = fit.site_exposure.get(site_id, 0.0) + k_site
        mean_rate = fit.site_means.get(site_id)
        exposure_assumption = history.exposure_assumption

        if restore_applies:
            target, reason = _restore_target(inp, history, spec)
            if target is None:
                plans.append(SitePlan(site_id, history.current_protocol, None, [None] * len(months),
                                      'unidentifiable', reason, segment, None))
                continue
            protocol = target
            rows = _rows_comparable_to(inp, history, target)
            exposure_sum = sum(_weight(row['month'], inp.current_month) * float(row['open_days']) / 30.0
                               for row in rows)
            enrolled_sum = sum(_weight(row['month'], inp.current_month) * float(row['enrolled'])
                               for row in rows)
            prior = fit.segment_means.get(target, fit.mu0)
            mean_rate = ((enrolled_sum + k_site * prior) / (exposure_sum + k_site)
                         if prior is not None else None)
            own_strength = exposure_sum + k_site
            positive = [float(row['open_days']) for row in rows if float(row['open_days']) > 0]
            exposure_assumption = (_median(positive) if positive
                                   else history.exposure_assumption)
            source = 'restored-protocol' if rows else 'restored-protocol-prior'

        if history.status == 'unidentifiable' and not restore_applies:
            plans.append(SitePlan(site_id, history.current_protocol, None, [None] * len(months),
                                  'unidentifiable', history.reason, segment, None))
            continue
        if protocol is None:
            plans.append(SitePlan(site_id, None, None, [None] * len(months),
                                  'unidentifiable', 'no_known_protocol', segment, None))
            continue
        if mean_rate is None:
            plans.append(SitePlan(site_id, protocol, None, [None] * len(months),
                                  'unidentifiable', 'no_known_protocol', segment, None))
            continue
        if exposure_assumption is None:
            # Never observed open: exposure is unknown, not zero, so no zero claim.
            plans.append(SitePlan(site_id, protocol, None, [None] * len(months),
                                  'unidentifiable', 'no_exposure_history', segment, None))
            continue

        exposure_values: list[float] = []
        for index, month in enumerate(months):
            if delay_site == site_id and index < delay_months:
                exposure_values.append(0.0)
            else:
                exposure_values.append(min(exposure_assumption, timeaxis.days_in_month(month)) / 30.0)

        borrowed: str | None = None
        status, reason = 'ok', ''
        if restore_applies and history.status != 'cold-start':
            if own_strength - k_site < COLD_START_EXPOSURE:
                status, reason = 'cold-start', 'short-history'
                borrowed = protocol
        elif history.status == 'cold-start':
            status = 'cold-start'
            reason = history.reason
            borrowed = segment or 'project'
        elif history.status == 'paused':
            status, reason = 'paused', history.reason
        elif history.exposure_borrowed:
            status = 'cold-start'
            reason = history.reason or 'no-comparable-history'
            borrowed = segment or 'project'

        if delay_site == site_id and delay_months:
            delayed_count = min(delay_months, len(months))
            for index in range(delayed_count):
                exposure_values[index] = 0.0
            if delay_months >= len(months):
                status, reason = 'delayed', 'delay_beyond_horizon'
            elif status == 'ok':
                status, reason = 'delayed', 'delayed-open'

        if status != 'delayed' and own_strength - k_site < COLD_START_EXPOSURE:
            if status == 'ok':
                status, reason = 'cold-start', 'short-history'
                borrowed = protocol if source.startswith('restored-protocol') else (segment or 'project')

        plans.append(SitePlan(site_id, protocol, mean_rate, exposure_values,
                              status, reason, segment, borrowed,
                              prior_strength=max(0.25, own_strength), source=source))
    return plans, problems


def _rows_comparable_to(inp: FeasibilityInput, history: SiteHistory, protocol: str) -> list[dict]:
    rows = []
    for row in sorted(history.rows, key=lambda item: item['month']):
        if row['month'] >= inp.current_month:
            continue
        if not usable_for_training(row, inp.as_of):
            continue
        if float(row['open_days']) <= 0:
            continue
        decision = comparability(inp.protocol_index, row['protocol_id'], protocol)
        if decision['status'] == 'comparable':
            rows.append(row)
    return rows


# --------------------------------------------------------------------- assembling


def _site_forecast_rows(inp: FeasibilityInput, plans: Sequence[SitePlan], months: Sequence[str],
                        fit: ModelFit, simulation: Mapping[str, Any]) -> list[dict]:
    rows: list[dict] = []
    for plan in plans:
        for index, month in enumerate(months):
            exposure = plan.exposure[index]
            if plan.status == 'unidentifiable':
                expected = None
                interval = [None, None]
                draw_values = []
            else:
                expected = round((plan.mean_rate or 0.0) * (exposure or 0.0), 3)
                draw_values = simulation['site_month_draws'].get(plan.site_id, [])
                interval = _interval(draw_values[index]) if draw_values else [0.0, 0.0]
            row = {
                'site_id': plan.site_id,
                'month': month,
                'expected': expected,
                'interval': interval,
                'status': plan.status,
                'protocol_id': plan.protocol or None,
                'exposure': round(exposure, 3) if exposure is not None else None,
                'interval_level': INTERVAL_LEVEL,
                'status_note': STATUS_NOTES.get(plan.status, ''),
            }
            if plan.status == 'unidentifiable':
                row['reason'] = plan.reason
            if plan.borrowed:
                row['borrowed_from'] = plan.borrowed
            row['source'] = plan.source
            if plan.status == 'paused':
                row['assumption'] = 'continued-pause'
                row['ability_positive'] = True
            rows.append(row)
    return rows


def _total_forecast(inp: FeasibilityInput, plans: Sequence[SitePlan], months: Sequence[str],
                    fit: ModelFit, simulation: Mapping[str, Any], remaining_target: float) -> dict:
    monthly = []
    cumulative_values = simulation['grand_totals']
    cumulative_expected = 0.0
    for index, month in enumerate(months):
        values = simulation['monthly_totals'][index]
        expected = sum((plan.mean_rate or 0.0) * (plan.exposure[index] or 0.0)
                       for plan in plans if plan.identified)
        cumulative_expected += expected
        monthly.append({
            'month': month,
            'expected': round(expected, 3),
            'interval': _interval(values) if values else [0.0, 0.0],
            'interval_level': INTERVAL_LEVEL,
        })
    unidentified = [plan.site_id for plan in plans if not plan.identified]
    paused = [plan.site_id for plan in plans if plan.status == 'paused']
    all_unidentified = bool(plans) and not any(plan.identified for plan in plans)
    status = 'ok' if not unidentified else ('unidentifiable' if all_unidentified else 'partial')
    total = {
        'months': monthly,
        'expected': round(cumulative_expected, 3),
        'interval': _interval(cumulative_values) if cumulative_values else [0.0, 0.0],
        'interval_level': INTERVAL_LEVEL,
        'remaining_target': remaining_target,
        'status': status,
        'unidentified_sites': unidentified,
        'paused_sites': paused,
        'probability_method': 'joint-simulation',
        'site_probabilities_additive': False,
    }
    if unidentified:
        total['reason_codes'] = sorted({plan.reason for plan in plans
                                        if not plan.identified and plan.reason})
        total['missing_sites_not_zero'] = True
        if all_unidentified:
            total['note'] = '没有任何中心可估计，因此不给总量数值；缺证据不等于零人。'
        else:
            # The displayed number covers only identified sites.  It is a lower
            # bound of what the programme might enrol, not a programme total.
            total['scope'] = 'identified-sites-lower-bound'
            total['note'] = ('总量仅汇总可估计中心，未把不可估中心按零人计入；'
                             '如需整体总量，先补齐缺失中心证据。')
    if paused:
        total['conservative_assumptions'] = ['continued-pause']
    return total


def _target_probability(inp: FeasibilityInput, plans: Sequence[SitePlan], simulation: Mapping[str, Any],
                        remaining_target: float) -> dict:
    unidentified = [plan.site_id for plan in plans if not plan.identified]
    identified = [plan for plan in plans if plan.identified]
    values = simulation['grand_totals']
    if not identified:
        return {'status': 'unidentifiable', 'probability': None,
                'reason_codes': sorted({plan.reason for plan in plans if plan.reason}) or ['no-identified-site'],
                'unidentified_sites': unidentified,
                'note': '没有任何中心可以在现有证据下估计；缺证据不按零人处理。'}
    if unidentified:
        # The identified subset can only be a lower bound on the programme: the
        # missing sites are unmeasured, not empty.  A subset probability that
        # already clears the target is therefore not evidence that the whole
        # programme is safe, so it is labelled as a subset figure only.
        subset_values = simulation['grand_totals']
        subset_probability = _probability(subset_values, remaining_target)
        return {'status': 'partial', 'probability': None,
                'identified_subset_probability': subset_probability,
                'identified_expected': round(sum((plan.mean_rate or 0.0) * sum(v or 0.0 for v in plan.exposure)
                                                  for plan in identified), 3),
                'unidentified_sites': unidentified,
                'missing_sites_treated_as_zero': False,
                'reason_codes': sorted({plan.reason for plan in plans if not plan.identified}),
                'note': ('部分中心不可估，未把缺失中心按零人计入；整体达标概率不给数值。'
                         'identified_subset_probability 只是已识别中心的下界参考，'
                         '不能当作整体计划安全，也不能与各中心成功概率相加。')}
    probability = _probability(values, remaining_target)
    return {'status': 'estimated', 'probability': probability,
            'draws': len(values),
            'method': 'joint-simulation P(total >= remaining_target)',
            'target': remaining_target,
            'site_probabilities_summed': False}


def _probability(values: Sequence[float], target: float) -> float:
    if not values:
        return 0.0
    if target <= 0:
        return 1.0
    hits = sum(1 for value in values if value >= target)
    return round(hits / len(values), 6)


def _scenario_result(inp: FeasibilityInput, spec: Mapping[str, Any], plans: Sequence[SitePlan],
                     problems: Sequence[dict], months: Sequence[str], fit: ModelFit,
                     rng: random.Random) -> dict:
    if problems:
        # An invalid plan is reported, never silently treated as the base case.
        return {
            'scenario_id': spec['scenario_id'],
            'status': 'invalid-scenario',
            'model_id': MODEL_ID,
            'changes': _scenario_changes(spec),
            'problems': list(problems),
            'site_forecasts': [],
            'total_forecast': None,
            'target_probability': {'status': 'unidentifiable', 'probability': None,
                                   'reason_codes': sorted({item['code'] for item in problems}),
                                   'site_probabilities_summed': False},
            'consistency': {'scenario_valid': False, 'total_from_joint_simulation': True,
                            'per_site_probabilities_summed': False},
        }
    simulation = simulate(plans, months, fit, TOTAL_DRAWS, rng)
    rows = _site_forecast_rows(inp, plans, months, fit, simulation)
    total = _total_forecast(inp, plans, months, fit, simulation, inp.remaining_target)
    probability = _target_probability(inp, plans, simulation, inp.remaining_target)
    consistency = _consistency(rows, total, probability)
    return {
        'scenario_id': spec['scenario_id'],
        'status': total['status'],
        'model_id': MODEL_ID,
        'changes': _scenario_changes(spec),
        'site_forecasts': rows,
        'total_forecast': total,
        'target_probability': probability,
        'consistency': consistency,
    }


def _scenario_changes(spec: Mapping[str, Any]) -> dict:
    return {
        'delay_site': spec['delay_site'],
        'delay_months': spec['delay_months'],
        'restore_protocol': spec['restore_protocol'],
        'restore_site': spec['restore_site'],
    }


def _scenario_comparison(scenarios: Sequence[Mapping[str, Any]]) -> dict:
    """Side-by-side view of plans evaluated on the same model version.

    Every scenario is fitted from the same histories and the same model_id; only
    the exposure calendar (delay) or the protocol being restored differs.  The
    totals here are copied from each scenario's own joint simulation, so they
    remain comparable without being recomputed under a different model.
    """
    rows = []
    base = next((item for item in scenarios if item.get('status') != 'invalid-scenario'), None)
    base_total = ((base or {}).get('total_forecast') or {}).get('expected')
    for scenario in scenarios:
        total = scenario.get('total_forecast') or {}
        probability = scenario.get('target_probability') or {}
        total_expected = total.get('expected')
        rows.append({
            'scenario_id': scenario['scenario_id'],
            'status': scenario['status'],
            'model_id': scenario['model_id'],
            'total_expected': total_expected,
            'total_interval': total.get('interval'),
            'target_probability': probability.get('probability'),
            'target_probability_status': probability.get('status'),
            'delta_vs_base': (round(total_expected - base_total, 3)
                              if isinstance(total_expected, (int, float))
                              and isinstance(base_total, (int, float)) else None),
        })
    return {'model_id': MODEL_ID, 'same_model_all_scenarios': True, 'base_scenario_id':
            (base or {}).get('scenario_id'), 'scenarios': rows,
            'note': '各情景共用同一 model_id 与同一拟合样本，仅改变曝光日历或恢复协议；总量与概率各自来自联合模拟。'}


def _consistency(rows: Sequence[dict], total: Mapping[str, Any], probability: Mapping[str, Any]) -> dict:
    identified = [row for row in rows if row['expected'] is not None]
    summed = round(sum(row['expected'] for row in identified), 3)
    monthly_sum = {}
    for row in identified:
        monthly_sum[row['month']] = round(monthly_sum.get(row['month'], 0.0) + row['expected'], 3)
    monthly_ok = all(
        abs(monthly_sum.get(month['month'], 0.0) - month['expected']) < 0.01
        for month in total['months']
    )
    return {
        'site_expected_sum': summed,
        'total_expected': total['expected'],
        'site_sum_matches_total': abs(summed - total['expected']) < 0.01,
        'monthly_sums_match_total': monthly_ok,
        'total_from_joint_simulation': True,
        'per_site_probabilities_summed': False,
        'target_probability_scope': probability.get('status'),
    }


def _exclusions_summary(exclusions: Sequence[dict], histories: Mapping[str, SiteHistory]) -> dict:
    counts: dict[str, int] = {}
    affected: dict[str, set] = {}
    for item in exclusions:
        counts[item['code']] = counts.get(item['code'], 0) + 1
        if item.get('site_id'):
            affected.setdefault(item['code'], set()).add(item['site_id'])
    summary = []
    for code in sorted(counts):
        summary.append({
            'code': code,
            'count': counts[code],
            'sites': sorted(affected.get(code, [])),
            'explanation': EXCLUSION_EXPLANATIONS.get(code, ''),
        })
    site_reasons = []
    for site_id, history in sorted(histories.items()):
        if history.status == 'unidentifiable':
            site_reasons.append({'site_id': site_id, 'code': history.reason,
                                 'explanation': EXCLUSION_EXPLANATIONS.get(history.reason, '')})
        elif history.status == 'cold-start':
            site_reasons.append({'site_id': site_id, 'code': history.reason or 'no_site_history',
                                 'explanation': EXCLUSION_EXPLANATIONS.get(history.reason or 'no_site_history', '')})
    return {
        'summary': summary,
        'items': list(exclusions)[:MAX_EXCLUSION_ITEMS],
        'items_truncated': len(exclusions) > MAX_EXCLUSION_ITEMS,
        'total_items': len(exclusions),
        'site_reasons': site_reasons,
    }


# ----------------------------------------------------------------------- backtest


def _truth_lookup(inp: FeasibilityInput) -> dict[tuple[str, str], float]:
    linked = link_observations(inp.observations)
    truth = {}
    for (site_id, month), record in linked['rows'].items():
        if month >= inp.current_month:
            continue
        if not known_by(record, inp.as_of):
            continue
        if record.get('complete') is not True:
            continue
        try:
            truth[(site_id, month)] = float(record.get('enrolled'))
        except (TypeError, ValueError):
            continue
    return truth


def backtest(inp: FeasibilityInput) -> dict:
    """Rolling-origin validation against a simple-rate and a naive baseline."""
    all_truth = _truth_lookup(inp)
    origins = _backtest_origins(inp)
    records: list[dict] = []
    origin_reports: list[dict] = []
    for origin in origins:
        cutoff = timeaxis.month_end(origin)
        cutoff_text = cutoff.isoformat()
        truth = {
            key: value for key, value in all_truth.items()
            if timeaxis.month_distance(origin, key[1]) in (1, 2, 3)
        }
        if not truth:
            continue
        try:
            subset = _subset_input(inp, cutoff_text)
            histories, _meta = collect_histories(subset)
            fit = fit_model(histories, origin)
        except DomainError:
            continue
        if fit.mu0 is None or fit.training_rows < BACKTEST_MIN_TRAINING_ROWS:
            continue
        months = timeaxis.next_months(origin, HORIZON_MONTHS)
        plans, problems = _scenario_plan(subset, {'scenario_id': 'backtest', 'delay_site': None,
                                                  'delay_months': 0, 'restore_protocol': False,
                                                  'restore_site': None}, histories, fit, months)
        if problems:
            continue
        rng = random.Random(inp.seed + 1000 + timeaxis.month_distance('2026-01', origin))
        simulation = simulate(plans, months, fit, BACKTEST_DRAWS, rng)
        model_rows = _site_forecast_rows(subset, plans, months, fit, simulation)
        baseline_rows = _baseline_rows(subset, histories, fit, plans, months)
        naive_rows = _naive_rows(inp, histories, plans, months)
        origin_records = []
        for row in model_rows:
            key = (row['site_id'], row['month'])
            if key not in truth or row['expected'] is None:
                continue
            origin_records.append({
                'origin': origin,
                'site_id': row['site_id'],
                'month': row['month'],
                'truth': truth[key],
                'model': row['expected'],
                'model_lower': row['interval'][0],
                'model_upper': row['interval'][1],
                'baseline_simple': baseline_rows.get(key),
                'baseline_naive': naive_rows.get(key),
            })
        records.extend(origin_records)
        scored_months = sorted({record['month'] for record in origin_records})
        origin_reports.append({
            'origin': origin,
            'cutoff': cutoff_text,
            'forecast_months': months,
            'scored_months': scored_months,
            'training_rows': fit.training_rows,
            'scored_cells': len(origin_records),
            'model': _score([record['model'] for record in origin_records],
                            [record['truth'] for record in origin_records],
                            [record['model_lower'] for record in origin_records],
                            [record['model_upper'] for record in origin_records]),
            'baseline_simple': _score([record['baseline_simple'] for record in origin_records],
                                      [record['truth'] for record in origin_records]),
            'baseline_naive': _score([record['baseline_naive'] for record in origin_records],
                                     [record['truth'] for record in origin_records]),
            'sites': sorted({record['site_id'] for record in origin_records}),
        })
    aggregate = {
        'model': _score([record['model'] for record in records], [record['truth'] for record in records],
                        [record['model_lower'] for record in records],
                        [record['model_upper'] for record in records]),
        'baseline_simple': _score([record['baseline_simple'] for record in records],
                                  [record['truth'] for record in records]),
        'baseline_naive': _score([record['baseline_naive'] for record in records],
                                 [record['truth'] for record in records]),
        'cells': len(records),
    }
    return {
        'method': 'rolling-origin',
        'random_month_split': False,
        'horizon_months': HORIZON_MONTHS,
        'interval_level': INTERVAL_LEVEL,
        'origins': origin_reports,
        'aggregate': aggregate,
        'notes': {
            'baseline_simple': '同一可用训练集上的池化每开放日速率（无收缩、无时间衰减）。',
            'baseline_naive': '按日历月平均新增（含停招月、跨协议合并），即容易高估的旧口径。',
            'truth_rule': '仅使用已结束、已上报且在 as_of 前已知的月份作为真值。',
        },
    }


def _backtest_origins(inp: FeasibilityInput) -> list[str]:
    """Origins whose next months already carry reported, complete ground truth.

    The month of the origin is the last month known at the cut-off; its own
    outcome is never scored.  Origins with no truth in the horizon are skipped
    rather than reported as a silent zero.
    """
    truth = _truth_lookup(inp)
    linked = link_observations(inp.observations)
    months = sorted({month for (_site, month) in linked['rows'] if month < inp.current_month})
    origins = []
    for month in reversed(months):
        ahead = timeaxis.next_months(month, HORIZON_MONTHS)
        if not any((site, candidate) in truth for (site, _m) in truth for candidate in ahead):
            continue
        origins.append(month)
        if len(origins) >= BACKTEST_ORIGINS:
            break
    return sorted(origins)


def _subset_input(inp: FeasibilityInput, cutoff: str) -> FeasibilityInput:
    return FeasibilityInput({
        'as_of': cutoff,
        'remaining_target': inp.remaining_target,
        'observations': inp.observations,
        'protocols': inp.protocols,
        'scenarios': inp.scenarios,
        'seed': inp.seed,
    })


def _baseline_rows(inp: FeasibilityInput, histories: Mapping[str, SiteHistory], fit: ModelFit,
                   plans: Sequence[SitePlan], months: Sequence[str]) -> dict:
    """Pooled rate over the same eligible rows: no decay, no shrinkage."""
    total_exposure = 0.0
    total_enrolled = 0.0
    for history in histories.values():
        for row in history.training:
            total_exposure += float(row['open_days']) / 30.0
            total_enrolled += float(row['enrolled'])
    rate = total_enrolled / total_exposure if total_exposure > 0 else 0.0
    rows = {}
    for plan in plans:
        if plan.status == 'unidentifiable':
            continue
        for index, month in enumerate(months):
            rows[(plan.site_id, month)] = round(rate * (plan.exposure[index] or 0.0), 4)
    return rows


def _naive_rows(inp: FeasibilityInput, histories: Mapping[str, SiteHistory],
                plans: Sequence[SitePlan], months: Sequence[str]) -> dict:
    """Mean enrolled per calendar month across all known closed months, zero months included."""
    rows = {}
    for plan in plans:
        if plan.status == 'unidentifiable':
            continue
        history = histories.get(plan.site_id)
        values = []
        if history is not None:
            for row in history.rows:
                if row['month'] >= inp.current_month:
                    continue
                if not known_by(row, inp.as_of) or row['complete'] is not True:
                    continue
                try:
                    values.append(float(row['enrolled']))
                except (TypeError, ValueError):
                    continue
        rate = sum(values) / len(values) if values else 0.0
        for month in months:
            rows[(plan.site_id, month)] = round(rate, 4)
    return rows


def _score(predictions: Sequence[float | None], truth: Sequence[float],
           lower: Sequence[float] | None = None, upper: Sequence[float] | None = None) -> dict:
    pairs = [(float(prediction), float(actual)) for prediction, actual in zip(predictions, truth)
             if prediction is not None and actual is not None]
    if not pairs:
        return {'n': 0, 'mae': None, 'rmse': None, 'coverage': None, 'pinball': None}
    errors = [prediction - actual for prediction, actual in pairs]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    report = {'n': len(pairs), 'mae': round(mae, 4), 'rmse': round(rmse, 4),
              'coverage': None, 'pinball': None}
    if lower is not None and upper is not None:
        covered = 0
        pinball = 0.0
        counted = 0
        for (prediction, actual), low, high in zip(pairs, lower, upper):
            if low is None or high is None:
                continue
            counted += 1
            if low <= actual <= high:
                covered += 1
            pinball += _pinball(actual, low, LOWER_QUANTILE)
            pinball += _pinball(actual, high, UPPER_QUANTILE)
        if counted:
            report['coverage'] = round(covered / counted, 4)
            report['pinball'] = round(pinball / (2 * counted), 4)
    return report


def _pinball(actual: float, predicted: float, quantile: float) -> float:
    delta = actual - predicted
    return quantile * delta if delta >= 0 else (quantile - 1.0) * delta


# ---------------------------------------------------------------------- persistence


def _connect(database: str | Path) -> sqlite3.Connection:
    path = Path(database)
    if path.parent and str(path.parent) not in ('', '.'):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=20, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=20000')
    connection.execute("""
        CREATE TABLE IF NOT EXISTS feasibility_runs(
          run_id TEXT PRIMARY KEY,
          model_id TEXT NOT NULL,
          as_of TEXT NOT NULL,
          input_digest TEXT NOT NULL,
          input_json TEXT NOT NULL,
          result_json TEXT NOT NULL,
          created_at TEXT NOT NULL)""")
    connection.execute("""
        CREATE INDEX IF NOT EXISTS feasibility_runs_lookup
        ON feasibility_runs(model_id, as_of, created_at)""")
    return connection


def _load_previous(connection: sqlite3.Connection, run_id: str, model_id: str, as_of: str) -> dict | None:
    # The row is keyed by (model_id, as_of); the previous revision of that same
    # analysis is the row we are about to replace, so it is not excluded here.
    row = connection.execute(
        "SELECT * FROM feasibility_runs WHERE model_id=? AND as_of=? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (model_id, as_of)).fetchone()
    if row is None:
        return None
    return {'run_id': row['run_id'], 'input_digest': row['input_digest'],
            'input': json.loads(row['input_json']), 'result': json.loads(row['result_json']),
            'created_at': row['created_at']}


def _persist(connection: sqlite3.Connection, run_id: str, model_id: str, as_of: str,
             input_digest: str, snapshot: Mapping[str, Any], result: Mapping[str, Any]) -> bool:
    created = datetime.now(timezone.utc).isoformat(timespec='seconds')
    # One analysis per (model_id, as_of): a correction replaces the stored
    # snapshot in place.  The pre-correction totals survive inside the new
    # result's ``revision_context`` so the difference stays explainable.
    connection.execute(
        """INSERT OR REPLACE INTO feasibility_runs VALUES(?,?,?,?,?,?,?)""",
        (run_id, model_id, as_of, input_digest, stable_json(snapshot), stable_json(result), created))
    return True


OBSERVATION_FIELDS = ('enrolled', 'open_days', 'complete', 'protocol_id', 'revision', 'known_at')


def _input_changes(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> dict:
    if previous is None:
        return {'previous_run_id': None, 'changed_observations': [], 'changed_scenarios': False,
                'changed_target': False, 'changed_protocols': False, 'changed_observations_count': 0}
    old = previous['input']
    old_observations = {(row.get('site_id'), row.get('month')): row
                        for row in old.get('observations', []) if isinstance(row, Mapping)}
    new_observations = {(row.get('site_id'), row.get('month')): row
                        for row in current.get('observations', []) if isinstance(row, Mapping)}
    changed = []
    for key in sorted(set(old_observations) | set(new_observations)):
        before = old_observations.get(key, {})
        after = new_observations.get(key, {})
        fields = {}
        for field in OBSERVATION_FIELDS:
            if before.get(field) != after.get(field):
                fields[field] = {'before': before.get(field), 'after': after.get(field)}
        if fields:
            changed.append({'site_id': key[0], 'month': key[1], 'fields': fields})
    return {
        'previous_run_id': previous['run_id'],
        'previous_created_at': previous.get('created_at'),
        'previous_input_digest': previous['input_digest'],
        'changed_observations': changed,
        'changed_observations_count': len(changed),
        'changed_scenarios': old.get('scenarios') != current.get('scenarios'),
        'changed_target': old.get('remaining_target') != current.get('remaining_target'),
        'changed_protocols': old.get('protocols') != current.get('protocols'),
    }


def _forecast_delta(previous: Mapping[str, Any] | None, result: Mapping[str, Any]) -> dict | None:
    if previous is None:
        return None
    old = previous['result']
    old_rows = {(row['site_id'], row['month']): row for row in old.get('site_forecasts', [])}
    new_rows = {(row['site_id'], row['month']): row for row in result.get('site_forecasts', [])}
    changed = []
    for key in sorted(set(old_rows) | set(new_rows)):
        before = old_rows.get(key, {})
        after = new_rows.get(key, {})
        if before.get('expected') != after.get('expected'):
            changed.append({'site_id': key[0], 'month': key[1],
                            'before': before.get('expected'), 'after': after.get('expected'),
                            'delta': _delta(before.get('expected'), after.get('expected'))})
    old_total = (old.get('total_forecast') or {}).get('expected')
    new_total = (result.get('total_forecast') or {}).get('expected')
    old_probability = (old.get('target_probability') or {}).get('probability')
    new_probability = (result.get('target_probability') or {}).get('probability')
    return {
        'changed_site_months': changed,
        'total_before': old_total,
        'total_after': new_total,
        'total_delta': _delta(old_total, new_total),
        'target_probability_before': old_probability,
        'target_probability_after': new_probability,
        'target_probability_delta': _delta(old_probability, new_probability),
    }


def _delta(before: Any, after: Any) -> float | None:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return round(float(after) - float(before), 4)
    return None


# ----------------------------------------------------------------------------- main


def analyze(raw: Mapping[str, Any], database: str | Path | None = None) -> dict:
    inp = FeasibilityInput(raw)
    histories, meta = collect_histories(inp)
    fit = fit_model(histories, inp.current_month)
    months = timeaxis.next_months(inp.current_month, HORIZON_MONTHS)
    specs = _scenario_specs(inp)
    rng = random.Random(inp.seed)

    scenario_results = []
    base_result = None
    for spec in specs:
        plans, problems = _scenario_plan(inp, spec, histories, fit, months)
        result = _scenario_result(inp, spec, plans, problems, months, fit, rng)
        scenario_results.append(result)
        if base_result is None:
            base_result = result

    base_result = scenario_results[0]
    comparison = _scenario_comparison(scenario_results)
    exclusions = _exclusions_summary(meta['exclusions'], histories)
    exclusions['conflicts'] = meta['conflicts'][:MAX_EXCLUSION_ITEMS]

    result = {
        'analysis': ANALYSIS_NAME,
        'analysis_version': ANALYSIS_VERSION,
        'model_id': MODEL_ID,
        'model_spec': MODEL_SPEC,
        'intended_use': DISCLAIMER,
        'as_of': inp.as_of,
        'input_digest': inp.input_digest,
        'horizon': {'start': months[0], 'months': months, 'count': len(months)},
        'remaining_target': inp.remaining_target,
        'base_scenario_id': base_result['scenario_id'],
        'site_forecasts': base_result['site_forecasts'],
        'total_forecast': base_result['total_forecast'],
        'target_probability': base_result['target_probability'],
        'consistency': base_result['consistency'],
        'model_diagnostics': {
            'project_rate_per_open_day': round(fit.mu0, 6) if fit.mu0 is not None else None,
            'training_rows': fit.training_rows,
            'weighted_exposure': round(fit.total_exposure, 4),
            'weighted_enrolled': round(fit.total_enrolled, 4),
            'segment_rates': {key: round(value, 6) for key, value in sorted(fit.segment_means.items())},
            'site_rates': {key: round(value, 6) for key, value in sorted(fit.site_means.items())},
            'site_own_exposure': {key: round(value, 4) for key, value in sorted(fit.site_exposure.items())},
            'site_shrinkage_weight': {key: round(value, 4) for key, value in sorted(fit.site_weights.items())},
            'dispersion': fit.dispersion,
            'recency_half_life_months': MODEL_SPEC['recency_half_life_months'],
        },
        'exclusions': exclusions,
        'scenarios': scenario_results,
        'scenario_comparison': comparison,
        'backtest': backtest(inp),
        'scope_note': DISCLAIMER,
    }

    if database:
        connection = _connect(database)
        try:
            revision_key = {'model_id': MODEL_ID, 'as_of': inp.as_of}
            run_id = fingerprint(revision_key)[:24]
            previous = _load_previous(connection, run_id, MODEL_ID, inp.as_of)
            unchanged = previous is not None and previous['input_digest'] == inp.input_digest
            result['run_id'] = run_id
            result['revision_context'] = _input_changes(previous, inp.snapshot())
            result['revision_context']['forecast_delta'] = _forecast_delta(previous, result)
            result['revision_context']['interpretation'] = (
                '输入与已保留版本一致，重跑结果可直接对照上一版本。'
                if unchanged else
                'model_id 未变，前后差异来自输入更正（如开放天数）而非模型版本变化。'
                if previous else '该 as_of 首次分析，无上一版本可比较。')
            if unchanged:
                # Keep the stored snapshot exactly as it was; nothing to write.
                result['revision_context']['stored'] = False
                result['revision_context']['replayed'] = True
            else:
                _persist(connection, run_id, MODEL_ID, inp.as_of, inp.input_digest,
                         inp.snapshot(), result)
                result['revision_context']['stored'] = True
                result['revision_context']['replayed'] = False
        finally:
            connection.close()
    else:
        revision_key = {'model_id': MODEL_ID, 'as_of': inp.as_of}
        result['run_id'] = fingerprint(revision_key)[:24]
        result['revision_context'] = _input_changes(None, inp.snapshot())
        result['revision_context']['forecast_delta'] = None
        result['revision_context']['interpretation'] = '未提供数据库，未保留分析版本。'
    return result


def run(input_path: str | Path, database: str | Path | None = None,
        output_path: str | Path | None = None) -> dict:
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    result = analyze(raw, database)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                                     encoding='utf-8')
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='招募可行性分析（仅用于中心资源排期，不用于临床入组资格判断）')
    parser.add_argument('--input', required=True, help='分析输入 JSON')
    parser.add_argument('--database', default='/tmp/trial_site_federator.sqlite3',
                        help='SQLite 路径，用于保留分析版本与前后差异')
    parser.add_argument('--output', required=True, help='结果 JSON 输出路径')
    args = parser.parse_args(argv)
    try:
        result = run(args.input, args.database, args.output)
    except DomainError as exc:
        print(json.dumps({'error': str(exc), 'kind': 'domain-error'}, ensure_ascii=False), file=sys.stderr)
        return 2
    summary = {
        'run_id': result['run_id'],
        'model_id': result['model_id'],
        'as_of': result['as_of'],
        'total_expected': result['total_forecast']['expected'],
        'total_status': result['total_forecast']['status'],
        'target_probability': result['target_probability'],
        'scenarios': [scenario['scenario_id'] for scenario in result['scenarios']],
        'output': str(args.output),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
