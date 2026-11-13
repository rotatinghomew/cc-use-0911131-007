from __future__ import annotations
from typing import Any, Mapping, Sequence
from trial_site_federator.runtime import DomainError, GenericRuleProcessor, ProcessingContext, normalize_text

STAGE = 'record_linkage'
RULES = [
    {
        'key': 'record_linkage_recruitment_01',
        'source': 'case_id',
        'target': 'derived.record_linkage.recruitment_01',
        'op': 'lower',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'record_linkage_cancer_02',
        'source': 'subject_id',
        'target': 'derived.record_linkage.cancer_02',
        'op': 'upper',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'record_linkage_phase_03',
        'source': 'category',
        'target': 'derived.record_linkage.phase_03',
        'op': 'number',
        'param': 1000,
        'required': True,
        'metric': 'record_linkage_02',
    },
    {
        'key': 'record_linkage_sponsor_04',
        'source': 'region',
        'target': 'derived.record_linkage.sponsor_04',
        'op': 'integer',
        'param': 1000000,
        'required': False,
        'metric': 'record_linkage_03',
    },
    {
        'key': 'record_linkage_freshness_05',
        'source': 'event_date',
        'target': 'derived.record_linkage.freshness_05',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_duplicate_06',
        'source': 'status',
        'target': 'derived.record_linkage.duplicate_06',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_catalog_07',
        'source': 'count',
        'target': 'derived.record_linkage.catalog_07',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_trial_08',
        'source': 'total',
        'target': 'derived.record_linkage.trial_08',
        'op': 'token',
        'param': 'trial_site_federator:record_linkage:trial',
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_protocol_09',
        'source': 'attributes',
        'target': 'derived.record_linkage.protocol_09',
        'op': 'bucket',
        'param': 10,
        'required': False,
        'metric': 'record_linkage_08',
    },
    {
        'key': 'record_linkage_site_10',
        'source': 'tags',
        'target': 'derived.record_linkage.site_10',
        'op': 'ratio',
        'param': 100,
        'required': False,
        'metric': 'record_linkage_09',
    },
    {
        'key': 'record_linkage_amendment_11',
        'source': 'source_system',
        'target': 'derived.record_linkage.amendment_11',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_eligibility_12',
        'source': 'revision',
        'target': 'derived.record_linkage.eligibility_12',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_recruitment_13',
        'source': 'case_id',
        'target': 'derived.record_linkage.recruitment_13',
        'op': 'window',
        'param': 7,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_cancer_14',
        'source': 'subject_id',
        'target': 'derived.record_linkage.cancer_14',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_phase_15',
        'source': 'category',
        'target': 'derived.record_linkage.phase_15',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_sponsor_16',
        'source': 'region',
        'target': 'derived.record_linkage.sponsor_16',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_freshness_17',
        'source': 'event_date',
        'target': 'derived.record_linkage.freshness_17',
        'op': 'number',
        'param': 10,
        'required': False,
        'metric': 'record_linkage_16',
    },
    {
        'key': 'record_linkage_duplicate_18',
        'source': 'status',
        'target': 'derived.record_linkage.duplicate_18',
        'op': 'integer',
        'param': 100,
        'required': False,
        'metric': 'record_linkage_17',
    },
    {
        'key': 'record_linkage_catalog_19',
        'source': 'count',
        'target': 'derived.record_linkage.catalog_19',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_trial_20',
        'source': 'total',
        'target': 'derived.record_linkage.trial_20',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_protocol_21',
        'source': 'attributes',
        'target': 'derived.record_linkage.protocol_21',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_site_22',
        'source': 'tags',
        'target': 'derived.record_linkage.site_22',
        'op': 'token',
        'param': 'trial_site_federator:record_linkage:site',
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_amendment_23',
        'source': 'source_system',
        'target': 'derived.record_linkage.amendment_23',
        'op': 'bucket',
        'param': 1000,
        'required': False,
        'metric': 'record_linkage_22',
    },
    {
        'key': 'record_linkage_eligibility_24',
        'source': 'revision',
        'target': 'derived.record_linkage.eligibility_24',
        'op': 'ratio',
        'param': 1000000,
        'required': False,
        'metric': 'record_linkage_23',
    },
    {
        'key': 'record_linkage_recruitment_25',
        'source': 'case_id',
        'target': 'derived.record_linkage.recruitment_25',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_cancer_26',
        'source': 'subject_id',
        'target': 'derived.record_linkage.cancer_26',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_phase_27',
        'source': 'category',
        'target': 'derived.record_linkage.phase_27',
        'op': 'window',
        'param': 30,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_sponsor_28',
        'source': 'region',
        'target': 'derived.record_linkage.sponsor_28',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_freshness_29',
        'source': 'event_date',
        'target': 'derived.record_linkage.freshness_29',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_duplicate_30',
        'source': 'status',
        'target': 'derived.record_linkage.duplicate_30',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_catalog_31',
        'source': 'count',
        'target': 'derived.record_linkage.catalog_31',
        'op': 'number',
        'param': 1000,
        'required': False,
        'metric': 'record_linkage_30',
    },
    {
        'key': 'record_linkage_trial_32',
        'source': 'total',
        'target': 'derived.record_linkage.trial_32',
        'op': 'integer',
        'param': 1000000,
        'required': False,
        'metric': 'record_linkage_31',
    },
    {
        'key': 'record_linkage_protocol_33',
        'source': 'attributes',
        'target': 'derived.record_linkage.protocol_33',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_site_34',
        'source': 'tags',
        'target': 'derived.record_linkage.site_34',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_amendment_35',
        'source': 'source_system',
        'target': 'derived.record_linkage.amendment_35',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_eligibility_36',
        'source': 'revision',
        'target': 'derived.record_linkage.eligibility_36',
        'op': 'token',
        'param': 'trial_site_federator:record_linkage:eligibility',
        'required': False,
        'metric': '',
    },
    {
        'key': 'record_linkage_recruitment_37',
        'source': 'case_id',
        'target': 'derived.record_linkage.recruitment_37',
        'op': 'bucket',
        'param': 10,
        'required': False,
        'metric': 'record_linkage_36',
    },
    {
        'key': 'record_linkage_cancer_38',
        'source': 'subject_id',
        'target': 'derived.record_linkage.cancer_38',
        'op': 'ratio',
        'param': 100,
        'required': False,
        'metric': 'record_linkage_37',
    },
]

class RecordLinkageProcessor(GenericRuleProcessor):
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
        branch['record_linkage'] = {'complete': True, 'revision': ctx.revision, 'evidence_count': len(ctx.evidence)}
        if len(ctx.flags) > 12:
            ctx.flag(f'escalate:{self.stage}')
        if not ctx.case_id:
            ctx.flag('missing:case_id')

def build_processor() -> GenericRuleProcessor:
    return RecordLinkageProcessor()


# --- Observation linkage ------------------------------------------------------------
#
# Monthly site counts arrive from multiple feeds.  Two feeds can describe the same
# site-month; a later revision supersedes an earlier one.  The catalog rule is:
# the highest revision wins, ties are broken by the later ``known_at``, and a tie
# that still disagrees is a conflict rather than a silent pick.  Feasibility
# consumes this so a corrected month is not double counted.

def observation_key(record: Mapping[str, Any]) -> tuple[str, str]:
    site_id = normalize_text(record.get('site_id'), 'site_id', 96)
    month = normalize_text(record.get('month'), 'month', 20)
    if not site_id:
        raise DomainError('site_id is required')
    if not month:
        raise DomainError('month is required')
    return site_id, month


def _revision_rank(record: Mapping[str, Any]) -> tuple:
    revision = record.get('revision')
    try:
        revision_value = float(revision) if revision is not None else 0.0
    except (TypeError, ValueError):
        revision_value = 0.0
    return (revision_value, normalize_text(record.get('known_at'), 'known_at', 40))


def link_observations(records: Sequence[Mapping[str, Any]]) -> dict:
    """Deduplicate site-month observations, newest revision per key.

    Returns ``rows`` (key -> winning record) plus ``conflicts`` and
    ``superseded`` so the analysis can explain what it discarded.  The winning
    record is copied, never mutated.
    """
    rows: dict[tuple[str, str], dict] = {}
    superseded: list[dict] = []
    conflicts: list[dict] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise DomainError('observations must be objects')
        key = observation_key(record)
        candidate = dict(record)
        current = rows.get(key)
        if current is None:
            rows[key] = candidate
            continue
        current_rank = _revision_rank(current)
        candidate_rank = _revision_rank(candidate)
        if candidate_rank > current_rank:
            rows[key] = candidate
            superseded.append({'site_id': key[0], 'month': key[1], 'revision': current.get('revision')})
        elif candidate_rank == current_rank:
            comparable = ('enrolled', 'open_days', 'complete', 'protocol_id')
            if any(candidate.get(name) != current.get(name) for name in comparable):
                conflicts.append({'site_id': key[0], 'month': key[1],
                                  'revision': candidate.get('revision')})
            else:
                superseded.append({'site_id': key[0], 'month': key[1],
                                   'revision': current.get('revision')})
        else:
            superseded.append({'site_id': key[0], 'month': key[1], 'revision': candidate.get('revision')})
    return {'rows': rows, 'superseded': superseded, 'conflicts': conflicts}


def known_by(record: Mapping[str, Any], as_of: str) -> bool:
    """True when the record was reported on or before ``as_of``."""
    known_at = normalize_text(record.get('known_at'), 'known_at', 40)
    return bool(known_at) and known_at <= as_of
