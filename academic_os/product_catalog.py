"""Navigation/presentation selection only. All displayed academic text is read from snapshots."""
from dataclasses import dataclass

PROTECTED_SNAPSHOTS=(
    '04765fa526fc03ee889f8e0691a23e07de4dcbd5486a779317a928c0809a7070',
    '4c48326cc3b4e3315118d8dc675764a1cff2d8e0c7d37a2f741bc26d928fe826',
)


@dataclass(frozen=True)
class TopicSelection:
    title:str
    concept:str
    competency:str
    task_condition:str
    # A bounded quotation selector, not fallback content. Must match a verified
    # syllabus locator; absent text is never invented or silently substituted.
    curriculum_excerpt:str


TOPICS={'standard-deviation':TopicSelection(
    'Standard deviation',
    'CON-STAT-SD','CAN-STAT-SD-CALC','TC-SUMMARY-STATISTICS',
    'Be able to calculate standard deviation, including from summary statistics.')}

# Published product aliases: identity-based, never generated from display text,
# snapshot IDs, versions or time. An additional identity needs an explicit alias.
PRODUCT_REFS={
    'concept:CON-STAT-SD':'concept-standard-deviation',
    'competency:CAN-STAT-SD-CALC':'capability-standard-deviation-calculate',
    'task_condition:TC-SUMMARY-STATISTICS':'task-form-summary-statistics',
}


def product_ref(key):
    if key not in PRODUCT_REFS:raise ValueError('No product reference registered for '+key)
    if len(set(PRODUCT_REFS.values()))!=len(PRODUCT_REFS):raise ValueError('Product reference collision')
    return PRODUCT_REFS[key]
