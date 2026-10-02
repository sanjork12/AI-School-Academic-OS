import json
from pathlib import Path


# Rebuild from the bootstrap baseline and full human decision history.
# Never use the previous promoted snapshot as input.
CANONICAL_FILE = Path(
    "output/topic2_canonical_prototype.json"
)

REVIEW_FILE = Path(
    "output/topic2_human_review_decisions.json"
)

OUTPUT_FILE = Path(
    "output/topic2_canonical_promoted.json"
)


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


canonical = load_json(CANONICAL_FILE)
review_data = load_json(REVIEW_FILE)


canonical_objectives = canonical[
    "canonical_objectives"
]

mappings = canonical[
    "mappings"
]


# --------------------------------
# Existing canonical nodes
# --------------------------------

existing_canonical_ids = {
    item["canonical_id"]
    for item in canonical_objectives
}


# --------------------------------
# Existing mapping pairs
# --------------------------------

existing_mapping_pairs = {
    (
        item["official_source_id"],
        item["canonical_id"],
    )
    for item in mappings
}


added_nodes = 0
skipped_nodes = 0

added_mappings = 0
skipped_mappings = 0


# --------------------------------
# Process review decisions
# --------------------------------

for decision in review_data["decisions"]:

    if decision["decision"] != "approve":
        continue

    decision_id = decision[
        "decision_id"
    ]

    canonical_id = decision.get(
        "approved_canonical_id"
    )

    if not canonical_id:
        raise ValueError(
            f"Approved decision "
            f"{decision_id} "
            f"has no approved_canonical_id."
        )


    # --------------------------------
    # Promote canonical node
    # --------------------------------

    if canonical_id in existing_canonical_ids:

        print(
            f"SKIP existing canonical node: "
            f"{canonical_id}"
        )

        skipped_nodes += 1

    else:

        if not decision.get("approved_subject_domain"):
            raise ValueError(
                f"Decision {decision_id} "
                f"requires approved_subject_domain "
                f"for a new canonical node."
            )

        skill_name = decision.get(
            "approved_skill_name"
        )

        if not skill_name:
            raise ValueError(
                f"Decision {decision_id} "
                f"requires approved_skill_name "
                f"for a new canonical node."
            )

        canonical_objectives.append(
            {
                "canonical_id":
                    canonical_id,

                "subject_domain":
                    decision["approved_subject_domain"],

                "skill_name":
                    skill_name,

                "description":
                    decision.get(
                        "approved_description"
                    ),

                "status":
                    "approved",
            }
        )

        existing_canonical_ids.add(
            canonical_id
        )

        added_nodes += 1

        print(
            f"ADD canonical node: "
            f"{canonical_id}"
        )


    # --------------------------------
    # Promote official mappings
    # --------------------------------

    approved_mappings = decision.get(
        "approved_official_mappings",
        []
    )

    for mapping in approved_mappings:

        official_id = mapping[
            "official_source_id"
        ]

        mapping_canonical_id = mapping[
            "canonical_id"
        ]

        pair = (
            official_id,
            mapping_canonical_id,
        )


        # Mapping must point to the
        # canonical node approved by
        # this review decision.

        if mapping_canonical_id != canonical_id:
            raise ValueError(
                f"Decision {decision_id}: "
                f"mapping canonical ID "
                f"{mapping_canonical_id} "
                f"does not match approved "
                f"canonical ID {canonical_id}."
            )


        # Human review decision must
        # produce approved mappings.

        if mapping["review_status"] != "approved":
            raise ValueError(
                f"Decision {decision_id}: "
                f"mapping {official_id} "
                f"is not approved."
            )


        if pair in existing_mapping_pairs:

            print(
                f"SKIP existing mapping: "
                f"{official_id} -> "
                f"{mapping_canonical_id}"
            )

            skipped_mappings += 1

        else:

            mappings.append(mapping)

            existing_mapping_pairs.add(
                pair
            )

            added_mappings += 1

            print(
                f"ADD mapping: "
                f"{official_id} -> "
                f"{mapping_canonical_id}"
            )


# --------------------------------
# Final duplicate safety checks
# --------------------------------

all_canonical_ids = [
    item["canonical_id"]
    for item in canonical_objectives
]

if len(all_canonical_ids) != len(
    set(all_canonical_ids)
):
    raise ValueError(
        "Duplicate canonical IDs detected "
        "after promotion."
    )


all_mapping_pairs = [
    (
        item["official_source_id"],
        item["canonical_id"],
    )
    for item in mappings
]

if len(all_mapping_pairs) != len(
    set(all_mapping_pairs)
):
    raise ValueError(
        "Duplicate mapping pairs detected "
        "after promotion."
    )


# --------------------------------
# Save promoted graph
# --------------------------------

output = {
    **canonical,

    "canonical_objectives":
        canonical_objectives,

    "mappings":
        mappings,

    "promotion_summary": {

        "review_decisions":
            len(review_data["decisions"]),

        "canonical_nodes_added":
            added_nodes,

        "canonical_nodes_skipped":
            skipped_nodes,

        "mappings_added":
            added_mappings,

        "mappings_skipped":
            skipped_mappings,
    },
}


OUTPUT_FILE.write_text(
    json.dumps(
        output,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


# --------------------------------
# Report
# --------------------------------

print()
print("=" * 72)
print("REVIEW DECISION PROMOTION REPORT")
print("=" * 72)

print(
    f"Review decisions:       "
    f"{len(review_data['decisions'])}"
)

print(
    f"Canonical nodes added:  "
    f"{added_nodes}"
)

print(
    f"Canonical nodes skipped:"
    f" {skipped_nodes}"
)

print(
    f"Mappings added:         "
    f"{added_mappings}"
)

print(
    f"Mappings skipped:       "
    f"{skipped_mappings}"
)

print(
    f"Canonical objectives:   "
    f"{len(canonical_objectives)}"
)

print(
    f"Official mappings:      "
    f"{len(mappings)}"
)

print(
    f"Output: {OUTPUT_FILE}"
)

print("=" * 72)
