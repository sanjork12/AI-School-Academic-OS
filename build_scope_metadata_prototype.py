import json
from pathlib import Path

from canonical_schema import CanonicalScopeMetadata


FOUNDATION_FILE = Path(
    "output/topic2_foundation_parsed.json"
)

HIGHER_FILE = Path(
    "output/topic2_higher_parsed.json"
)

OUTPUT_FILE = Path(
    "output/topic2_scope_metadata_prototype.json"
)


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def find_objective(data, source_id):
    for subtopic in data["subtopics"]:
        for objective in subtopic["objectives"]:
            if objective["source_id"] == source_id:
                return {
                    "source_id": source_id,
                    "official_text":
                        objective["official_text"],
                    "subtopic_code":
                        subtopic["code"],
                    "subtopic_name":
                        subtopic["name"],
                }

    raise ValueError(
        f"Objective not found: {source_id}"
    )


foundation = load_json(FOUNDATION_FILE)
higher = load_json(HIGHER_FILE)


# -------------------------------------------------
# Ground-truth official objectives
# -------------------------------------------------

f_27a = find_objective(
    foundation,
    "EDX-4MA1-F-2.7-A"
)

h_27a = find_objective(
    higher,
    "EDX-4MA1-H-2.7-A"
)

f_28e = find_objective(
    foundation,
    "EDX-4MA1-F-2.8-E"
)

h_28b = find_objective(
    higher,
    "EDX-4MA1-H-2.8-B"
)

f_24a = find_objective(
    foundation,
    "EDX-4MA1-F-2.4-A"
)


# -------------------------------------------------
# Human-reviewed scope metadata
# -------------------------------------------------

metadata = [

    CanonicalScopeMetadata(
        official_source_id=f_27a["source_id"],
        canonical_id="CAN-ALG-QUAD-FACTOR",

        tier_source="Foundation",
        tier_applicability=[
            "Foundation"
        ],

        scope_description=(
            "Solve quadratic equations by "
            "factorisation within the restricted "
            "Foundation scope stated in the "
            "official objective."
        ),

        constraints=[
            "Limited to x² + bx + c = 0"
        ],

        metadata_method="human",
        review_status="approved",
    ),

    CanonicalScopeMetadata(
        official_source_id=h_27a["source_id"],
        canonical_id="CAN-ALG-QUAD-FACTOR",

        tier_source="Higher",
        tier_applicability=[
            "Higher"
        ],

        scope_description=(
            "Solve quadratic equations by "
            "factorisation."
        ),

        constraints=[],

        metadata_method="human",
        review_status="approved",
    ),

    CanonicalScopeMetadata(
        official_source_id=f_28e["source_id"],
        canonical_id=(
            "CAN-ALG-INEQ-REGION-INTERPRET"
        ),

        tier_source="Foundation",
        tier_applicability=[
            "Foundation"
        ],

        scope_description=(
            "Identify regions on rectangular "
            "Cartesian graphs defined by simple "
            "linear inequalities."
        ),

        constraints=[
            "Simple linear inequalities"
        ],

        metadata_method="human",
        review_status="approved",
    ),

    CanonicalScopeMetadata(
        official_source_id=h_28b["source_id"],
        canonical_id=(
            "CAN-ALG-INEQ-REGION-INTERPRET"
        ),

        tier_source="Higher",
        tier_applicability=[
            "Higher"
        ],

        scope_description=(
            "Identify harder examples of regions "
            "defined by linear inequalities."
        ),

        constraints=[
            "Harder examples"
        ],

        metadata_method="human",
        review_status="approved",
    ),

    CanonicalScopeMetadata(
        official_source_id=f_24a["source_id"],
        canonical_id=(
            "CAN-ALG-LINEAR-EQUATION-SOLVE"
        ),

        tier_source="Foundation",
        tier_applicability=[
            "Foundation",
            "Higher"
        ],

        scope_description=(
            "Solve linear equations in one "
            "unknown, including equations with "
            "integer or fractional coefficients "
            "and equations where the unknown "
            "appears on either or both sides."
        ),

        constraints=[
            "One unknown",
            "Integer or fractional coefficients",
            "Unknown may appear on either or both sides"
        ],

        metadata_method="human",
        review_status="approved",
    ),
]

# -------------------------------------------------
# Safety checks
# -------------------------------------------------

seen_official_ids = set()

for item in metadata:

    if item.official_source_id in seen_official_ids:
        raise ValueError(
            "Duplicate scope metadata for: "
            f"{item.official_source_id}"
        )

    seen_official_ids.add(
        item.official_source_id
    )


# -------------------------------------------------
# Save
# -------------------------------------------------

output = {
    "prototype_version": "0.1",
    "metadata_count": len(metadata),
    "metadata": [
        item.model_dump()
        for item in metadata
    ],
}


OUTPUT_FILE.write_text(
    json.dumps(
        output,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


# -------------------------------------------------
# Report
# -------------------------------------------------

print("=" * 72)
print("CANONICAL SCOPE METADATA PROTOTYPE")
print("=" * 72)

for item in metadata:

    print()
    print(
        f"Official:    "
        f"{item.official_source_id}"
    )

    print(
        f"Canonical:   "
        f"{item.canonical_id}"
    )

    print(
       f"Tier source: "
       f"{item.tier_source}"
   )

    print(
       f"Applies to:  "
       f"{item.tier_applicability}"
   )

    print(
        f"Scope:       "
        f"{item.scope_description}"
    )

    print(
        f"Constraints: "
        f"{item.constraints}"
    )

    print(
        f"Review:      "
        f"{item.review_status}"
    )


print()
print("=" * 72)

print(
    f"Scope metadata records: "
    f"{len(metadata)}"
)

print(
    f"Output: {OUTPUT_FILE}"
)

print("=" * 72)