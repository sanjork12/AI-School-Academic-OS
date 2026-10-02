import json
from pathlib import Path


FOUNDATION_FILE = Path(
    "output/topic2_foundation_parsed.json"
)

HIGHER_FILE = Path(
    "output/topic2_higher_parsed.json"
)

CANONICAL_FILE = Path(
    "output/topic2_canonical_prototype.json"
)

SCOPE_FILE = Path(
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


foundation = load_json(FOUNDATION_FILE)
higher = load_json(HIGHER_FILE)
canonical = load_json(CANONICAL_FILE)
scope_data = load_json(SCOPE_FILE)


errors = []
warnings = []


# --------------------------------
# Collect official objectives
# --------------------------------

official_objectives = {}

for curriculum in [foundation, higher]:

    expected_tier = curriculum["tier_source"]

    for subtopic in curriculum["subtopics"]:
        for objective in subtopic["objectives"]:

            source_id = objective["source_id"]

            if source_id in official_objectives:
                errors.append(
                    f"Duplicate official source ID: "
                    f"{source_id}"
                )

            official_objectives[source_id] = {
                "tier_source": expected_tier,
                "official_text":
                    objective["official_text"],
            }


# --------------------------------
# Collect canonical IDs
# --------------------------------

canonical_ids = set()

for objective in canonical[
    "canonical_objectives"
]:

    canonical_id = objective["canonical_id"]

    if canonical_id in canonical_ids:
        errors.append(
            f"Duplicate canonical ID: "
            f"{canonical_id}"
        )

    canonical_ids.add(canonical_id)


# --------------------------------
# Validate scope metadata
# --------------------------------

scope_records = scope_data.get(
    "metadata",
    []
)

seen_pairs = set()


for record in scope_records:

    official_id = record[
        "official_source_id"
    ]

    canonical_id = record[
        "canonical_id"
    ]

    tier_source = record[
        "tier_source"
    ]

    applicability = record[
        "tier_applicability"
    ]


    # Official objective must exist

    if official_id not in official_objectives:
        errors.append(
            f"Unknown official source ID: "
            f"{official_id}"
        )
        continue


    # Canonical node must exist

    if canonical_id not in canonical_ids:
        errors.append(
            f"Unknown canonical ID: "
            f"{canonical_id}"
        )


    # Tier source must match official source

    expected_tier = (
        official_objectives[
            official_id
        ]["tier_source"]
    )

    if tier_source != expected_tier:
        errors.append(
            f"Tier source mismatch for "
            f"{official_id}: "
            f"expected {expected_tier}, "
            f"got {tier_source}"
        )


    # Applicability must not be empty

    if not applicability:
        errors.append(
            f"Empty tier applicability: "
            f"{official_id}"
        )


    # Applicability must not contain duplicates

    if len(applicability) != len(
        set(applicability)
    ):
        errors.append(
            f"Duplicate tier applicability: "
            f"{official_id}"
        )


    # Source tier should normally be applicable

    if tier_source not in applicability:
        warnings.append(
            f"Source tier not included in "
            f"applicability for {official_id}"
        )


    # Prevent duplicate official→canonical
    # scope records

    pair = (
        official_id,
        canonical_id
    )

    if pair in seen_pairs:
        errors.append(
            f"Duplicate scope record: "
            f"{official_id} -> "
            f"{canonical_id}"
        )

    seen_pairs.add(pair)


# --------------------------------
# Cross-check against approved
# official→canonical mappings
# --------------------------------

approved_mapping_pairs = set()

for mapping in canonical["mappings"]:

    if mapping["review_status"] != "approved":
        continue

    approved_mapping_pairs.add(
        (
            mapping["official_source_id"],
            mapping["canonical_id"],
        )
    )


for record in scope_records:

    pair = (
        record["official_source_id"],
        record["canonical_id"],
    )

    if pair not in approved_mapping_pairs:
        warnings.append(
            "Scope metadata has no approved "
            "official-to-canonical mapping: "
            f"{pair[0]} -> {pair[1]}"
        )


# --------------------------------
# Report
# --------------------------------

print("=" * 72)
print("SCOPE METADATA VALIDATION REPORT")
print("=" * 72)

print()
print(
    f"Official objectives:      "
    f"{len(official_objectives)}"
)

print(
    f"Canonical objectives:     "
    f"{len(canonical_ids)}"
)

print(
    f"Scope metadata records:   "
    f"{len(scope_records)}"
)

print(
    f"Approved mapping pairs:   "
    f"{len(approved_mapping_pairs)}"
)


print()

if errors:
    print("STRUCTURE VALIDATION FAILED")
else:
    print("STRUCTURE VALIDATION PASSED")


if warnings:
    print("REVIEW REQUIRED")
else:
    print("NO REVIEW WARNINGS")


if errors:
    print()
    print("ERRORS")
    print("-" * 72)

    for error in errors:
        print(
            f"[ERROR] {error}"
        )


if warnings:
    print()
    print("WARNINGS")
    print("-" * 72)

    for warning in warnings:
        print(
            f"[WARNING] {warning}"
        )


print()
print(
    f"Errors: {len(errors)}"
)

print(
    f"Warnings: {len(warnings)}"
)

print("=" * 72)


if errors:
    raise SystemExit(1)