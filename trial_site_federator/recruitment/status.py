from __future__ import annotations
from typing import Any, Mapping, Sequence
from trial_site_federator.runtime import DomainError, GenericRuleProcessor, ProcessingContext, normalize_text

STAGE = 'recruitment_status'
RULES = [
    {
        'key': 'recruitment_status_eligibility_01',
        'source': 'case_id',
        'target': 'derived.recruitment_status.eligibility_01',
        'op': 'checksum',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'recruitment_status_recruitment_02',
        'source': 'subject_id',
        'target': 'derived.recruitment_status.recruitment_02',
        'op': 'window',
        'param': 14,
        'required': True,
        'metric': '',
    },
    {
        'key': 'recruitment_status_cancer_03',
        'source': 'category',
        'target': 'derived.recruitment_status.cancer_03',
        'op': 'text',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'recruitment_status_phase_04',
        'source': 'region',
        'target': 'derived.recruitment_status.phase_04',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_sponsor_05',
        'source': 'event_date',
        'target': 'derived.recruitment_status.sponsor_05',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_freshness_06',
        'source': 'status',
        'target': 'derived.recruitment_status.freshness_06',
        'op': 'number',
        'param': 100,
        'required': False,
        'metric': 'recruitment_status_05',
    },
    {
        'key': 'recruitment_status_duplicate_07',
        'source': 'count',
        'target': 'derived.recruitment_status.duplicate_07',
        'op': 'integer',
        'param': 1000,
        'required': False,
        'metric': 'recruitment_status_06',
    },
    {
        'key': 'recruitment_status_catalog_08',
        'source': 'total',
        'target': 'derived.recruitment_status.catalog_08',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_trial_09',
        'source': 'attributes',
        'target': 'derived.recruitment_status.trial_09',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_protocol_10',
        'source': 'tags',
        'target': 'derived.recruitment_status.protocol_10',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_site_11',
        'source': 'source_system',
        'target': 'derived.recruitment_status.site_11',
        'op': 'token',
        'param': 'trial_site_federator:recruitment_status:site',
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_amendment_12',
        'source': 'revision',
        'target': 'derived.recruitment_status.amendment_12',
        'op': 'bucket',
        'param': 1000000,
        'required': False,
        'metric': 'recruitment_status_11',
    },
    {
        'key': 'recruitment_status_eligibility_13',
        'source': 'case_id',
        'target': 'derived.recruitment_status.eligibility_13',
        'op': 'ratio',
        'param': 10,
        'required': False,
        'metric': 'recruitment_status_12',
    },
    {
        'key': 'recruitment_status_recruitment_14',
        'source': 'subject_id',
        'target': 'derived.recruitment_status.recruitment_14',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_cancer_15',
        'source': 'category',
        'target': 'derived.recruitment_status.cancer_15',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_phase_16',
        'source': 'region',
        'target': 'derived.recruitment_status.phase_16',
        'op': 'window',
        'param': 90,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_sponsor_17',
        'source': 'event_date',
        'target': 'derived.recruitment_status.sponsor_17',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_freshness_18',
        'source': 'status',
        'target': 'derived.recruitment_status.freshness_18',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_duplicate_19',
        'source': 'count',
        'target': 'derived.recruitment_status.duplicate_19',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_catalog_20',
        'source': 'total',
        'target': 'derived.recruitment_status.catalog_20',
        'op': 'number',
        'param': 1000000,
        'required': False,
        'metric': 'recruitment_status_19',
    },
    {
        'key': 'recruitment_status_trial_21',
        'source': 'attributes',
        'target': 'derived.recruitment_status.trial_21',
        'op': 'integer',
        'param': 10,
        'required': False,
        'metric': 'recruitment_status_20',
    },
    {
        'key': 'recruitment_status_protocol_22',
        'source': 'tags',
        'target': 'derived.recruitment_status.protocol_22',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_site_23',
        'source': 'source_system',
        'target': 'derived.recruitment_status.site_23',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_amendment_24',
        'source': 'revision',
        'target': 'derived.recruitment_status.amendment_24',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_eligibility_25',
        'source': 'case_id',
        'target': 'derived.recruitment_status.eligibility_25',
        'op': 'token',
        'param': 'trial_site_federator:recruitment_status:eligibility',
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_recruitment_26',
        'source': 'subject_id',
        'target': 'derived.recruitment_status.recruitment_26',
        'op': 'bucket',
        'param': 100,
        'required': False,
        'metric': 'recruitment_status_25',
    },
    {
        'key': 'recruitment_status_cancer_27',
        'source': 'category',
        'target': 'derived.recruitment_status.cancer_27',
        'op': 'ratio',
        'param': 1000,
        'required': False,
        'metric': 'recruitment_status_26',
    },
    {
        'key': 'recruitment_status_phase_28',
        'source': 'region',
        'target': 'derived.recruitment_status.phase_28',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_sponsor_29',
        'source': 'event_date',
        'target': 'derived.recruitment_status.sponsor_29',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_freshness_30',
        'source': 'status',
        'target': 'derived.recruitment_status.freshness_30',
        'op': 'window',
        'param': 14,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_duplicate_31',
        'source': 'count',
        'target': 'derived.recruitment_status.duplicate_31',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_catalog_32',
        'source': 'total',
        'target': 'derived.recruitment_status.catalog_32',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_trial_33',
        'source': 'attributes',
        'target': 'derived.recruitment_status.trial_33',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_protocol_34',
        'source': 'tags',
        'target': 'derived.recruitment_status.protocol_34',
        'op': 'number',
        'param': 100,
        'required': False,
        'metric': 'recruitment_status_33',
    },
    {
        'key': 'recruitment_status_site_35',
        'source': 'source_system',
        'target': 'derived.recruitment_status.site_35',
        'op': 'integer',
        'param': 1000,
        'required': False,
        'metric': 'recruitment_status_34',
    },
    {
        'key': 'recruitment_status_amendment_36',
        'source': 'revision',
        'target': 'derived.recruitment_status.amendment_36',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_eligibility_37',
        'source': 'case_id',
        'target': 'derived.recruitment_status.eligibility_37',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'recruitment_status_recruitment_38',
        'source': 'subject_id',
        'target': 'derived.recruitment_status.recruitment_38',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
]

class StatusProcessor(GenericRuleProcessor):
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
        branch['recruitment_status'] = {'complete': True, 'revision': ctx.revision, 'evidence_count': len(ctx.evidence)}
        if len(ctx.flags) > 12:
            ctx.flag(f'escalate:{self.stage}')
        if not ctx.case_id:
            ctx.flag('missing:case_id')

def build_processor() -> GenericRuleProcessor:
    return StatusProcessor()


# --- Exposure and pause semantics -----------------------------------------------------
#
# Recruitment effort is measured in open site-days, not calendar months.  A month
# with a pause or a late opening contributes a partial exposure, and a month with
# zero open days contributes no exposure at all.  This keeps a "screening halted"
# month from being read as "site cannot recruit" while still preventing a paused
# month from being advertised as capacity in a scenario plan.

def _number(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise DomainError(f'{name} must be numeric') from None
    if number < 0:
        raise DomainError(f'{name} must be non-negative')
    return number


def exposure_days(record: Mapping[str, Any], month_length: int | None = None) -> dict:
    """Interpret a monthly count as open-day exposure.

    ``open_days`` above the month length is impossible and rejected; a month
    reported without ``open_days`` is unknown exposure, not zero exposure.
    """
    raw = record.get('open_days')
    if raw is None:
        return {'status': 'unknown', 'days': None, 'paused': False, 'reason': 'missing-open-days'}
    days = _number(raw, 'open_days')
    if month_length is not None and days > month_length:
        raise DomainError(f'open_days={days} exceeds month length {month_length}')
    paused = days == 0
    return {
        'status': 'paused' if paused else 'open',
        'days': days,
        'paused': paused,
        'reason': 'zero-exposure-pause' if paused else 'exposed',
    }


def enrolment(record: Mapping[str, Any]) -> float:
    value = _number(record.get('enrolled', 0), 'enrolled')
    if value != int(value):
        raise DomainError('enrolled must be a whole count')
    return value


def exposure_share(record: Mapping[str, Any], month_length: int) -> float:
    """Open fraction of the month in [0, 1]; unknown exposure raises."""
    report = exposure_days(record, month_length)
    if report['days'] is None:
        raise DomainError('open_days is required to compute exposure')
    return report['days'] / float(month_length)


def exposure_weight(record: Mapping[str, Any], month_length: int) -> float:
    """Exposure in full-month equivalents, the natural offset for a rate model."""
    return exposure_share(record, month_length)


def pause_months(records: Sequence[Mapping[str, Any]]) -> list[dict]:
    result = []
    for record in records:
        report = exposure_days(record)
        if report['paused']:
            result.append({'site_id': normalize_text(record.get('site_id'), 'site_id', 96),
                           'month': normalize_text(record.get('month'), 'month', 20),
                           'reason': report['reason']})
    return result


def exposure_summary(records: Sequence[Mapping[str, Any]], month_lengths: Mapping[str, int]) -> dict:
    """Aggregate exposure for a site, separating paused and unknown months."""
    total_days = 0.0
    open_months = paused_months = unknown_months = 0
    for record in records:
        month = normalize_text(record.get('month'), 'month', 20)
        report = exposure_days(record, month_lengths.get(month))
        if report['status'] == 'unknown':
            unknown_months += 1
            continue
        total_days += report['days']
        if report['paused']:
            paused_months += 1
        elif report['days'] > 0:
            open_months += 1
    return {'open_days': total_days, 'open_months': open_months,
            'paused_months': paused_months, 'unknown_months': unknown_months,
            'month_equivalents': round(total_days / 30.0, 6)}
