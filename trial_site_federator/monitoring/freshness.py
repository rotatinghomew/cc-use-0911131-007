from __future__ import annotations
from typing import Any, Mapping
from trial_site_federator.runtime import GenericRuleProcessor, ProcessingContext, normalize_text

STAGE = 'freshness_monitor'
RULES = [
    {
        'key': 'freshness_monitor_cancer_01',
        'source': 'case_id',
        'target': 'derived.freshness_monitor.cancer_01',
        'op': 'integer',
        'param': 10,
        'required': True,
        'metric': 'freshness_monitor_00',
    },
    {
        'key': 'freshness_monitor_phase_02',
        'source': 'subject_id',
        'target': 'derived.freshness_monitor.phase_02',
        'op': 'boolean',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_sponsor_03',
        'source': 'category',
        'target': 'derived.freshness_monitor.sponsor_03',
        'op': 'list',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_freshness_04',
        'source': 'region',
        'target': 'derived.freshness_monitor.freshness_04',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_duplicate_05',
        'source': 'event_date',
        'target': 'derived.freshness_monitor.duplicate_05',
        'op': 'token',
        'param': 'trial_site_federator:freshness_monitor:duplicate',
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_catalog_06',
        'source': 'status',
        'target': 'derived.freshness_monitor.catalog_06',
        'op': 'bucket',
        'param': 100,
        'required': False,
        'metric': 'freshness_monitor_05',
    },
    {
        'key': 'freshness_monitor_trial_07',
        'source': 'count',
        'target': 'derived.freshness_monitor.trial_07',
        'op': 'ratio',
        'param': 1000,
        'required': False,
        'metric': 'freshness_monitor_06',
    },
    {
        'key': 'freshness_monitor_protocol_08',
        'source': 'total',
        'target': 'derived.freshness_monitor.protocol_08',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_site_09',
        'source': 'attributes',
        'target': 'derived.freshness_monitor.site_09',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_amendment_10',
        'source': 'tags',
        'target': 'derived.freshness_monitor.amendment_10',
        'op': 'window',
        'param': 14,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_eligibility_11',
        'source': 'source_system',
        'target': 'derived.freshness_monitor.eligibility_11',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_recruitment_12',
        'source': 'revision',
        'target': 'derived.freshness_monitor.recruitment_12',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_cancer_13',
        'source': 'case_id',
        'target': 'derived.freshness_monitor.cancer_13',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_phase_14',
        'source': 'subject_id',
        'target': 'derived.freshness_monitor.phase_14',
        'op': 'number',
        'param': 100,
        'required': False,
        'metric': 'freshness_monitor_13',
    },
    {
        'key': 'freshness_monitor_sponsor_15',
        'source': 'category',
        'target': 'derived.freshness_monitor.sponsor_15',
        'op': 'integer',
        'param': 1000,
        'required': False,
        'metric': 'freshness_monitor_14',
    },
    {
        'key': 'freshness_monitor_freshness_16',
        'source': 'region',
        'target': 'derived.freshness_monitor.freshness_16',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_duplicate_17',
        'source': 'event_date',
        'target': 'derived.freshness_monitor.duplicate_17',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_catalog_18',
        'source': 'status',
        'target': 'derived.freshness_monitor.catalog_18',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_trial_19',
        'source': 'count',
        'target': 'derived.freshness_monitor.trial_19',
        'op': 'token',
        'param': 'trial_site_federator:freshness_monitor:trial',
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_protocol_20',
        'source': 'total',
        'target': 'derived.freshness_monitor.protocol_20',
        'op': 'bucket',
        'param': 1000000,
        'required': False,
        'metric': 'freshness_monitor_19',
    },
    {
        'key': 'freshness_monitor_site_21',
        'source': 'attributes',
        'target': 'derived.freshness_monitor.site_21',
        'op': 'ratio',
        'param': 10,
        'required': False,
        'metric': 'freshness_monitor_20',
    },
    {
        'key': 'freshness_monitor_amendment_22',
        'source': 'tags',
        'target': 'derived.freshness_monitor.amendment_22',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_eligibility_23',
        'source': 'source_system',
        'target': 'derived.freshness_monitor.eligibility_23',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_recruitment_24',
        'source': 'revision',
        'target': 'derived.freshness_monitor.recruitment_24',
        'op': 'window',
        'param': 90,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_cancer_25',
        'source': 'case_id',
        'target': 'derived.freshness_monitor.cancer_25',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_phase_26',
        'source': 'subject_id',
        'target': 'derived.freshness_monitor.phase_26',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_sponsor_27',
        'source': 'category',
        'target': 'derived.freshness_monitor.sponsor_27',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_freshness_28',
        'source': 'region',
        'target': 'derived.freshness_monitor.freshness_28',
        'op': 'number',
        'param': 1000000,
        'required': False,
        'metric': 'freshness_monitor_27',
    },
    {
        'key': 'freshness_monitor_duplicate_29',
        'source': 'event_date',
        'target': 'derived.freshness_monitor.duplicate_29',
        'op': 'integer',
        'param': 10,
        'required': False,
        'metric': 'freshness_monitor_28',
    },
    {
        'key': 'freshness_monitor_catalog_30',
        'source': 'status',
        'target': 'derived.freshness_monitor.catalog_30',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_trial_31',
        'source': 'count',
        'target': 'derived.freshness_monitor.trial_31',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_protocol_32',
        'source': 'total',
        'target': 'derived.freshness_monitor.protocol_32',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_site_33',
        'source': 'attributes',
        'target': 'derived.freshness_monitor.site_33',
        'op': 'token',
        'param': 'trial_site_federator:freshness_monitor:site',
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_amendment_34',
        'source': 'tags',
        'target': 'derived.freshness_monitor.amendment_34',
        'op': 'bucket',
        'param': 100,
        'required': False,
        'metric': 'freshness_monitor_33',
    },
    {
        'key': 'freshness_monitor_eligibility_35',
        'source': 'source_system',
        'target': 'derived.freshness_monitor.eligibility_35',
        'op': 'ratio',
        'param': 1000,
        'required': False,
        'metric': 'freshness_monitor_34',
    },
    {
        'key': 'freshness_monitor_recruitment_36',
        'source': 'revision',
        'target': 'derived.freshness_monitor.recruitment_36',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_cancer_37',
        'source': 'case_id',
        'target': 'derived.freshness_monitor.cancer_37',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'freshness_monitor_phase_38',
        'source': 'subject_id',
        'target': 'derived.freshness_monitor.phase_38',
        'op': 'window',
        'param': 14,
        'required': False,
        'metric': '',
    },
]

class FreshnessProcessor(GenericRuleProcessor):
    stage = STAGE
    rules = RULES

    def process(self, ctx: ProcessingContext) -> ProcessingContext:
        ctx.emit(self.stage, 'processor_started', rule_count=len(self.rules))
        result = super().process(ctx)
        self.enforce_business_invariants(result)
        result.emit(self.stage, 'processor_finished', flags=len(result.flags), evidence=len(result.evidence))
        return result

    def enforce_business_invariants(self, ctx: ProcessingContext) -> None:
        branch = ctx.payload.setdefault('business', {})
        branch['freshness_monitor'] = {'complete': True, 'revision': ctx.revision, 'evidence_count': len(ctx.evidence)}
        if len(ctx.flags) > 12:
            ctx.flag(f'escalate:{self.stage}')
        if not ctx.case_id:
            ctx.flag('missing:case_id')

def build_processor() -> GenericRuleProcessor:
    return FreshnessProcessor()


# --- Observation freshness -----------------------------------------------------------
#
# A month can only be used for training once (a) the record was known by the
# analysis cut-off, (b) the month itself has closed before the cut-off, and
# (c) the feed reports it complete.  The current, unfinished month is never a
# training label: its running total is right-censored and would bias every later
# estimate downward.  A zero-exposure month is a different case: it is real data
# about a pause, but it cannot estimate a per-open-day rate, so it is excluded
# from rate fitting while remaining usable as an observed pause.

def month_key(value: object) -> str:
    return normalize_text(value, 'month', 20)


def freshness_of(record: Mapping[str, Any], as_of: str) -> dict:
    month = month_key(record.get('month'))
    known_at = normalize_text(record.get('known_at'), 'known_at', 40)
    as_of_text = normalize_text(as_of, 'as_of', 40)
    open_days = record.get('open_days')
    try:
        open_days_value = float(open_days)
    except (TypeError, ValueError):
        open_days_value = None
    if not month:
        status, reason = 'stale', 'missing-month'
    elif month > as_of_text[:7]:
        status, reason = 'future', 'month-after-cutoff'
    elif month == as_of_text[:7]:
        # The current month is right-censored whether or not a running total was
        # already reported; that is why this check precedes the cut-off check.
        status, reason = 'open', 'current-month-incomplete'
    elif not known_at:
        status, reason = 'stale', 'missing-known-at'
    elif known_at > as_of_text:
        status, reason = 'stale', 'reported-after-cutoff'
    elif open_days_value is None:
        status, reason = 'stale', 'missing-open-days'
    else:
        status, reason = 'usable', 'closed-and-known'
    return {
        'status': status,
        'reason': reason,
        'month': month,
        'known_at': known_at or None,
        'open_days': open_days_value,
        'training_eligible': status == 'usable',
        'censored': status == 'open',
    }


def usable_for_training(record: Mapping[str, Any], as_of: str) -> bool:
    """True only for a closed, known, complete month with a reported exposure."""
    report = freshness_of(record, as_of)
    if not report['training_eligible']:
        return False
    if record.get('complete') is not True:
        return False
    if report['open_days'] is None or report['open_days'] <= 0:
        return False
    return True


def exposure_known(record: Mapping[str, Any]) -> bool:
    try:
        return float(record.get('open_days')) > 0
    except (TypeError, ValueError):
        return False
