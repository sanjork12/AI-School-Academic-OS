import argparse
import json
import sys
from pathlib import Path


FOUNDATION_FILE = Path(
    "output/topic2_foundation_parsed.json"
)

HIGHER_FILE = Path(
    "output/topic2_higher_parsed.json"
)

DEFAULT_CANONICAL_FILE = Path(
    "output/topic2_canonical_prototype.json"
)


# --------------------------------
# Command-line arguments
# --------------------------------

parser = argparse.ArgumentParser(
    description=(
        "Validate a canonical curriculum graph."
    )
)

parser.add_argument(
    "--canonical",
    type=Path,
    default=DEFAULT_CANONICAL_FILE,
    help=(
        "Canonical graph JSON file to validate. "
        "Defaults to "
        "output/topic2_canonical_prototype.json"
    ),
)

args = parser.parse_args()

CANONICAL_FILE = args.canonical


# --------------------------------
# Helpers
# --------------------------------

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


# --------------------------------
# Load files
# --------------------------------

foundation_data = load_json(
    FOUNDATION_FILE
)

higher_data = load_json(
    HIGHER_FILE
)

canonical_data = load_json(
    CANONICAL_FILE
)


errors = []
warnings = []


# --------------------------------
# Collect official objectives
# --------------------------------

official_ids = set()

for curriculum in [
    foundation_data,
    higher_data,
]:

    for subtopic in curriculum["subtopics"]:

        for objective in subtopic["objectives"]:

            source_id = objective.get(
                "source_id"
            )

            if not source_id:
                errors.append(
                    "Official objective missing "
                    "source_id: "
                    f"{subtopic['code']}-"
                    f"{objective['code']}"
                )
                continue

            if source_id in official_ids:
                errors.append(
                    "Duplicate official source_id: "
                    f"{source_id}"
                )

            official_ids.add(
                source_id
            )


# --------------------------------
# Validate canonical objectives
# --------------------------------

canonical_objectives = (
    canonical_data.get(
        "canonical_objectives",
        []
    )
)

canonical_ids = set()

for objective in canonical_objectives:

    canonical_id = objective.get(
        "canonical_id"
    )

    if not canonical_id:
        errors.append(
            "Canonical objective missing "
            "canonical_id."
        )
        continue

    if canonical_id in canonical_ids:
        errors.append(
            "Duplicate canonical_id: "
            f"{canonical_id}"
        )

    canonical_ids.add(
        canonical_id
    )

    if not objective.get(
        "skill_name"
    ):
        errors.append(
            f"{canonical_id}: "
            f"missing skill_name."
        )

    if not objective.get(
        "subject_domain"
    ):
        errors.append(
            f"{canonical_id}: "
            f"missing subject_domain."
        )


# --------------------------------
# Validate mappings
# --------------------------------

mappings = canonical_data.get(
    "mappings",
    []
)

mapping_pairs = set()
mapped_official_ids = set()


valid_relationships = {
    "equivalent",
    "broader",
    "narrower",
    "partial",
}

valid_methods = {
    "human",
    "ai",
    "rule",
}

valid_review_statuses = {
    "pending",
    "approved",
    "rejected",
}


for mapping in mappings:

    official_id = mapping.get(
        "official_source_id"
    )

    canonical_id = mapping.get(
        "canonical_id"
    )

    relationship = mapping.get(
        "relationship"
    )

    confidence = mapping.get(
        "confidence"
    )

    method = mapping.get(
        "mapping_method"
    )

    review_status = mapping.get(
        "review_status"
    )


    # --------------------------------
    # Referential integrity
    # --------------------------------

    if official_id not in official_ids:
        errors.append(
            "Mapping references unknown "
            "official_source_id: "
            f"{official_id}"
        )

    if canonical_id not in canonical_ids:
        errors.append(
            "Mapping references unknown "
            "canonical_id: "
            f"{canonical_id}"
        )


    # --------------------------------
    # Duplicate mapping
    # --------------------------------

    pair = (
        official_id,
        canonical_id,
    )

    if pair in mapping_pairs:
        errors.append(
            "Duplicate mapping: "
            f"{official_id} -> "
            f"{canonical_id}"
        )

    mapping_pairs.add(
        pair
    )


    # --------------------------------
    # Relationship
    # --------------------------------

    if relationship not in valid_relationships:
        errors.append(
            f"{official_id}: "
            f"invalid relationship "
            f"'{relationship}'"
        )


    # --------------------------------
    # Confidence
    # --------------------------------

    if not isinstance(
        confidence,
        (int, float)
    ):
        errors.append(
            f"{official_id}: "
            f"confidence must be numeric."
        )

    elif not 0.0 <= confidence <= 1.0:
        errors.append(
            f"{official_id}: "
            f"confidence must be between "
            f"0 and 1."
        )


    # --------------------------------
    # Mapping method
    # --------------------------------

    if method not in valid_methods:
        errors.append(
            f"{official_id}: "
            f"invalid mapping_method "
            f"'{method}'"
        )


    # --------------------------------
    # Review status
    # --------------------------------

    if (
        review_status
        not in valid_review_statuses
    ):
        errors.append(
            f"{official_id}: "
            f"invalid review_status "
            f"'{review_status}'"
        )


    # --------------------------------
    # Approved AI mapping sanity check
    # --------------------------------

    if (
        method == "ai"
        and review_status == "approved"
    ):
        warnings.append(
            f"{official_id}: "
            f"AI mapping is approved. "
            f"Confirm human review."
        )


    if official_id in official_ids:
        mapped_official_ids.add(
            official_id
        )


# --------------------------------
# Coverage
# --------------------------------

unmapped_ids = (
    official_ids
    - mapped_official_ids
)

if unmapped_ids:
    warnings.append(
        f"{len(unmapped_ids)} official "
        f"objective(s) are not yet mapped."
    )


# --------------------------------
# Report
# --------------------------------

print()
print("=" * 72)
print(
    "CANONICAL GRAPH VALIDATION REPORT"
)
print("=" * 72)

print(
    f"Canonical file:            "
    f"{CANONICAL_FILE}"
)

print()

print(
    f"Official objectives total:   "
    f"{len(official_ids)}"
)

print(
    f"Canonical objectives total:  "
    f"{len(canonical_ids)}"
)

print(
    f"Mappings total:              "
    f"{len(mappings)}"
)

print(
    f"Mapped official objectives:  "
    f"{len(mapped_official_ids)}"
)

print(
    f"Unmapped official objectives:"
    f"  {len(unmapped_ids)}"
)

print()


if errors:
    print(
        "STRUCTURE VALIDATION FAILED"
    )
else:
    print(
        "STRUCTURE VALIDATION PASSED"
    )


if warnings:
    print(
        "REVIEW REQUIRED"
    )
else:
    print(
        "NO REVIEW WARNINGS"
    )


# --------------------------------
# Errors
# --------------------------------

if errors:

    print()
    print("ERRORS")
    print("-" * 72)

    for error in errors:
        print(
            f"[ERROR] {error}"
        )


# --------------------------------
# Warnings
# --------------------------------

if warnings:

    print()
    print("WARNINGS")
    print("-" * 72)

    for warning in warnings:
        print(
            f"[WARNING] {warning}"
        )


# --------------------------------
# Show unmapped IDs
# --------------------------------

if unmapped_ids:

    print()
    print(
        "UNMAPPED OFFICIAL OBJECTIVES"
    )
    print("-" * 72)

    for source_id in sorted(
        unmapped_ids
    ):
        print(
            source_id
        )


print()
print(
    f"Errors: {len(errors)}"
)

print(
    f"Warnings: {len(warnings)}"
)

print("=" * 72)


# --------------------------------
# Non-zero exit code if invalid
# --------------------------------

if errors:
    sys.exit(1)