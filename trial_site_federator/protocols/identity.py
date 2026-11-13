from __future__ import annotations
from typing import Mapping
from trial_site_federator.runtime import DomainError, GenericRuleProcessor, ProcessingContext, normalize_text

STAGE = 'protocol_identity'
RULES = [
    {
        'key': 'protocol_identity_protocol_01',
        'source': 'case_id',
        'target': 'derived.protocol_identity.protocol_01',
        'op': 'number',
        'param': 10,
        'required': True,
        'metric': 'protocol_identity_00',
    },
    {
        'key': 'protocol_identity_site_02',
        'source': 'subject_id',
        'target': 'derived.protocol_identity.site_02',
        'op': 'integer',
        'param': 100,
        'required': True,
        'metric': 'protocol_identity_01',
    },
    {
        'key': 'protocol_identity_amendment_03',
        'source': 'category',
        'target': 'derived.protocol_identity.amendment_03',
        'op': 'boolean',
        'param': 500,
        'required': True,
        'metric': '',
    },
    {
        'key': 'protocol_identity_eligibility_04',
        'source': 'region',
        'target': 'derived.protocol_identity.eligibility_04',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_recruitment_05',
        'source': 'event_date',
        'target': 'derived.protocol_identity.recruitment_05',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_cancer_06',
        'source': 'status',
        'target': 'derived.protocol_identity.cancer_06',
        'op': 'token',
        'param': 'trial_site_federator:protocol_identity:cancer',
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_phase_07',
        'source': 'count',
        'target': 'derived.protocol_identity.phase_07',
        'op': 'bucket',
        'param': 1000,
        'required': False,
        'metric': 'protocol_identity_06',
    },
    {
        'key': 'protocol_identity_sponsor_08',
        'source': 'total',
        'target': 'derived.protocol_identity.sponsor_08',
        'op': 'ratio',
        'param': 1000000,
        'required': False,
        'metric': 'protocol_identity_07',
    },
    {
        'key': 'protocol_identity_freshness_09',
        'source': 'attributes',
        'target': 'derived.protocol_identity.freshness_09',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_duplicate_10',
        'source': 'tags',
        'target': 'derived.protocol_identity.duplicate_10',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_catalog_11',
        'source': 'source_system',
        'target': 'derived.protocol_identity.catalog_11',
        'op': 'window',
        'param': 30,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_trial_12',
        'source': 'revision',
        'target': 'derived.protocol_identity.trial_12',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_protocol_13',
        'source': 'case_id',
        'target': 'derived.protocol_identity.protocol_13',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_site_14',
        'source': 'subject_id',
        'target': 'derived.protocol_identity.site_14',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_amendment_15',
        'source': 'category',
        'target': 'derived.protocol_identity.amendment_15',
        'op': 'number',
        'param': 1000,
        'required': False,
        'metric': 'protocol_identity_14',
    },
    {
        'key': 'protocol_identity_eligibility_16',
        'source': 'region',
        'target': 'derived.protocol_identity.eligibility_16',
        'op': 'integer',
        'param': 1000000,
        'required': False,
        'metric': 'protocol_identity_15',
    },
    {
        'key': 'protocol_identity_recruitment_17',
        'source': 'event_date',
        'target': 'derived.protocol_identity.recruitment_17',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_cancer_18',
        'source': 'status',
        'target': 'derived.protocol_identity.cancer_18',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_phase_19',
        'source': 'count',
        'target': 'derived.protocol_identity.phase_19',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_sponsor_20',
        'source': 'total',
        'target': 'derived.protocol_identity.sponsor_20',
        'op': 'token',
        'param': 'trial_site_federator:protocol_identity:sponsor',
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_freshness_21',
        'source': 'attributes',
        'target': 'derived.protocol_identity.freshness_21',
        'op': 'bucket',
        'param': 10,
        'required': False,
        'metric': 'protocol_identity_20',
    },
    {
        'key': 'protocol_identity_duplicate_22',
        'source': 'tags',
        'target': 'derived.protocol_identity.duplicate_22',
        'op': 'ratio',
        'param': 100,
        'required': False,
        'metric': 'protocol_identity_21',
    },
    {
        'key': 'protocol_identity_catalog_23',
        'source': 'source_system',
        'target': 'derived.protocol_identity.catalog_23',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_trial_24',
        'source': 'revision',
        'target': 'derived.protocol_identity.trial_24',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_protocol_25',
        'source': 'case_id',
        'target': 'derived.protocol_identity.protocol_25',
        'op': 'window',
        'param': 7,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_site_26',
        'source': 'subject_id',
        'target': 'derived.protocol_identity.site_26',
        'op': 'text',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_amendment_27',
        'source': 'category',
        'target': 'derived.protocol_identity.amendment_27',
        'op': 'lower',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_eligibility_28',
        'source': 'region',
        'target': 'derived.protocol_identity.eligibility_28',
        'op': 'upper',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_recruitment_29',
        'source': 'event_date',
        'target': 'derived.protocol_identity.recruitment_29',
        'op': 'number',
        'param': 10,
        'required': False,
        'metric': 'protocol_identity_28',
    },
    {
        'key': 'protocol_identity_cancer_30',
        'source': 'status',
        'target': 'derived.protocol_identity.cancer_30',
        'op': 'integer',
        'param': 100,
        'required': False,
        'metric': 'protocol_identity_29',
    },
    {
        'key': 'protocol_identity_phase_31',
        'source': 'count',
        'target': 'derived.protocol_identity.phase_31',
        'op': 'boolean',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_sponsor_32',
        'source': 'total',
        'target': 'derived.protocol_identity.sponsor_32',
        'op': 'list',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_freshness_33',
        'source': 'attributes',
        'target': 'derived.protocol_identity.freshness_33',
        'op': 'code',
        'param': 500,
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_duplicate_34',
        'source': 'tags',
        'target': 'derived.protocol_identity.duplicate_34',
        'op': 'token',
        'param': 'trial_site_federator:protocol_identity:duplicate',
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_catalog_35',
        'source': 'source_system',
        'target': 'derived.protocol_identity.catalog_35',
        'op': 'bucket',
        'param': 1000,
        'required': False,
        'metric': 'protocol_identity_34',
    },
    {
        'key': 'protocol_identity_trial_36',
        'source': 'revision',
        'target': 'derived.protocol_identity.trial_36',
        'op': 'ratio',
        'param': 1000000,
        'required': False,
        'metric': 'protocol_identity_35',
    },
    {
        'key': 'protocol_identity_protocol_37',
        'source': 'case_id',
        'target': 'derived.protocol_identity.protocol_37',
        'op': 'status',
        'param': ['new', 'active', 'closed', 'pending'],
        'required': False,
        'metric': '',
    },
    {
        'key': 'protocol_identity_site_38',
        'source': 'subject_id',
        'target': 'derived.protocol_identity.site_38',
        'op': 'checksum',
        'param': 500,
        'required': False,
        'metric': '',
    },
]

class IdentityProcessor(GenericRuleProcessor):
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
        branch['protocol_identity'] = {'complete': True, 'revision': ctx.revision, 'evidence_count': len(ctx.evidence)}
        if len(ctx.flags) > 12:
            ctx.flag(f'escalate:{self.stage}')
        if not ctx.case_id:
            ctx.flag('missing:case_id')

def build_processor() -> GenericRuleProcessor:
    return IdentityProcessor()


# --- Protocol lineage comparability -------------------------------------------------
#
# Recruitment counts from an earlier protocol revision may only be pooled with a
# later revision when the change between them is not expected to move the size or
# the mix of the eligible population.  The catalog keeps the protocol pedigree, so
# the rule lives here rather than in the analysis module: every consumer applies
# the same interpretation of ``change_type`` and the same handling of unknown
# parents.

_COMPARABLE_CHANGE_TYPES = frozenset({
    'root',
    'clarification',
    'administrative',
    'formatting',
    'site-addition',
    'contact-update',
    'language',
    'editorial',
})

_BREAKING_CHANGE_TYPES = frozenset({
    'eligibility-change',
    'population-change',
    'endpoint-change',
    'treatment-change',
    'dose-change',
    'randomisation-change',
    'amendment',
})


def normalize_change_type(value: object) -> str:
    return normalize_text(value, 'change_type', 80).strip().casefold().replace('_', '-') or 'unknown'


def protocol_index(protocols) -> dict[str, dict]:
    """Build a validated protocol pedigree, rejecting conflicting duplicates."""
    index: dict[str, dict] = {}
    for item in protocols or []:
        if not isinstance(item, Mapping):
            raise DomainError('protocol entries must be objects')
        protocol_id = normalize_text(item.get('protocol_id'), 'protocol_id', 96)
        if not protocol_id:
            raise DomainError('protocol_id is required')
        parent = normalize_text(item.get('parent'), 'parent', 96) or None
        if parent == protocol_id:
            raise DomainError(f'protocol {protocol_id} is its own parent')
        entry = {
            'protocol_id': protocol_id,
            'parent': parent,
            'change_type': normalize_change_type(item.get('change_type')),
            'known_at': normalize_text(item.get('known_at'), 'known_at', 40) or None,
        }
        existing = index.get(protocol_id)
        if existing is not None and existing != entry:
            raise DomainError(f'protocol {protocol_id} declared twice with conflicting pedigree')
        index[protocol_id] = entry
    return index


def lineage_chain(index: Mapping[str, dict], protocol_id: str) -> list[dict]:
    """Return the pedigree from ``protocol_id`` up to its root.

    A dangling parent is returned as a sentinel entry so callers can report
    ``unknown-lineage`` instead of silently treating the chain as complete.
    Cycles are rejected because they make comparability undecidable.
    """
    chain: list[dict] = []
    seen: set[str] = set()
    current: str | None = protocol_id
    while current is not None:
        if current in seen:
            raise DomainError(f'protocol lineage cycle at {current}')
        seen.add(current)
        entry = index.get(current)
        if entry is None:
            chain.append({'protocol_id': current, 'parent': None, 'change_type': 'unknown',
                          'known_at': None, 'missing': True})
            return chain
        chain.append(dict(entry))
        current = entry.get('parent')
    return chain


def changed_parents(index: Mapping[str, dict], protocol_id: str) -> list[str]:
    chain = lineage_chain(index, protocol_id)
    return [entry['protocol_id'] for entry in chain[1:] if not entry.get('missing')]


def comparability(index: Mapping[str, dict], historical: str, current: str) -> dict:
    """Can recruitment observed under ``historical`` inform ``current``?

    Returns a decision record with a machine readable ``status`` of
    ``comparable``, ``not-comparable`` or ``unknown`` and a human readable
    ``reason``.  Anything that cannot be decided from the catalog is ``unknown``;
    it is never treated as comparable, because doing so would let unverified
    revisions leak into the forecast.
    """
    historical = normalize_text(historical, 'protocol_id', 96)
    current = normalize_text(current, 'protocol_id', 96)
    if not historical or not current:
        return {'status': 'unknown', 'reason': 'protocol-id-missing', 'path': []}
    if historical == current:
        # Even a self-comparison is undecidable when the protocol is not in the
        # catalog: the analysis deliberately does not invent a lineage for it.
        if current not in index:
            return {'status': 'unknown', 'reason': f'unregistered-protocol:{current}', 'path': [current]}
        return {'status': 'comparable', 'reason': 'same-protocol', 'path': [current]}
    chain = lineage_chain(index, current)
    path = [entry['protocol_id'] for entry in chain]
    missing = [entry['protocol_id'] for entry in chain if entry.get('missing')]
    if missing:
        return {'status': 'unknown', 'reason': f'unknown-lineage:{missing[0]}', 'path': path}
    if historical not in path:
        return {'status': 'not-comparable', 'reason': 'unrelated-lineage', 'path': path}
    if chain[0]['protocol_id'] == historical:
        return {'status': 'comparable', 'reason': 'same-protocol', 'path': path[:1]}
    # Walk from current back to the historical revision; every change in between
    # is a candidate break, and the newest one decides the answer.
    breaking: list[str] = []
    for entry in chain[:-1]:
        kind = entry.get('change_type', 'unknown')
        if kind in _BREAKING_CHANGE_TYPES:
            breaking.append(f"{entry['protocol_id']}:{kind}")
        elif kind not in _COMPARABLE_CHANGE_TYPES:
            return {'status': 'unknown', 'reason': f'unknown-change-type:{entry["protocol_id"]}:{kind}',
                    'path': path}
    if breaking:
        return {'status': 'not-comparable', 'reason': f'breaking-change:{breaking[0]}', 'path': path}
    return {'status': 'comparable', 'reason': 'non-breaking-revisions-only', 'path': path}


def comparable_set(index: Mapping[str, dict], current: str) -> dict[str, dict]:
    """Map every protocol in the pedigree to its comparability decision."""
    return {protocol_id: comparability(index, protocol_id, current) for protocol_id in index}


def change_type_catalog(index: Mapping[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in index.values():
        counts[entry['change_type']] = counts.get(entry['change_type'], 0) + 1
    return counts
