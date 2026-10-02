"""Source-only bundle definitions; reuse P1B version/decision-head tickets."""
from .review_bundles import BundleSpec, guard, source_view
from .core import manifest
from .sources import integrity

NOTICE = 'Source verification does not approve academic interpretation.'
SOURCE_BUNDLES = {
    'SOURCE-BUNDLE-MS-Q2': BundleSpec('SOURCE-BUNDLE-MS-Q2', 'Q2 mark scheme',
        ('source:MS', 'locator:MS-Q2-a', 'locator:MS-Q2-b', 'locator:MS-Q2-c'), participation='source verification only'),
    'SOURCE-BUNDLE-QP-Q2': BundleSpec('SOURCE-BUNDLE-QP-Q2', 'Q2 question paper',
        ('source:QP', 'locator:QP-Q2', 'locator:QP-Q2-a', 'locator:QP-Q2-b', 'locator:QP-Q2-c'), participation='source verification only'),
    'SOURCE-BUNDLE-SPEC-2.3': BundleSpec('SOURCE-BUNDLE-SPEC-2.3', 'Specification section 2.3',
        ('source:SPEC', 'locator:SPEC-2.3'), participation='source verification only'),
}


def source_versions(graph, spec):
    versions = manifest(graph, spec.roots)
    if any(graph[k]['record']['kind'] not in ('source', 'locator') for k in versions):
        raise ValueError('Source bundle dependency closure contains academic objects; review its definition')
    return versions


def source_bundle_view(graph, decisions, spec):
    versions = source_versions(graph, spec)
    groups = source_view(graph, decisions, versions)
    if len(groups) != 1:
        raise ValueError('Source bundle requires exactly one source')
    group = groups[0]
    objects = [group['source'], *group['locators']]
    errors = integrity(graph, versions)
    group.update(bundle_id=spec.bundle_id, integrity_errors=errors,
        source_verified=not errors and all(o['state'] == 'verify' for o in objects),
        stale_objects=[o['key'] for o in objects if o['state'] == 'stale'],
        decision_scope={a: list(versions) for a in ('verify', 'reject')},
        review_ticket=guard(graph, decisions, spec, versions), notice=NOTICE)
    return group


# Preserve the historical Q2-only catalog for existing integrations.
ALL_SOURCE_BUNDLES=dict(SOURCE_BUNDLES)
for _kind in ('QP','MS'):
    _parts=('whole','b','c','a','b-i','b-ii','c-i','c-ii') if _kind=='QP' else ('a','b-i','b-ii','c-i','c-ii')
    _id='SOURCE-BUNDLE-'+_kind+'-Q3-2023'
    ALL_SOURCE_BUNDLES[_id]=BundleSpec(_id,'June 2023 Q3 '+_kind,
        ('source:'+_kind+'-2023',)+tuple('locator:'+_kind+'-2023-Q3-'+p for p in _parts),
        participation='source verification only')
