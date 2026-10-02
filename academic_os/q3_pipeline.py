"""P1C candidate orchestration. Source structure and semantics are independent."""
from .q3_parsing import build_source_plan, SOURCE_DIR, PARTS
from .canonical_proposals import semantic_plan
from .models import normalise
from .core import validate_graph


def plan_q3(graph,decisions,source_dir=None):
    sources=build_source_plan(graph,source_dir or SOURCE_DIR)
    extended=dict(graph)
    for raw in sources['items']:
        k,v,r=normalise(raw);extended[k]=dict(version=v,record=r)
    validate_graph(extended)
    semantics=semantic_plan(extended,decisions,['parsed_part:PARSED-Q3-2023-'+p for p in PARTS])
    return dict(items=sources['items']+semantics['items'],expected_heads={**sources['expected_heads'],**semantics['expected_heads']})
