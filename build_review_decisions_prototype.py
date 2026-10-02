from pathlib import Path

from review_decision_log import append_review_decisions

from canonical_schema import (
    CanonicalReviewDecision,
    OfficialToCanonicalMapping,
)


OUTPUT_FILE = Path(
    "output/topic2_human_review_decisions.json"
)


decisions = [

    # ============================================================
    # Decision 1
    # Consolidate Foundation/Higher inequality-region skills
    # ============================================================

    CanonicalReviewDecision(
        decision_id=(
            "REV-4MA1-T2-INEQ-REGION-001"
        ),

        proposal_type="consolidation",

        source_ids=[
            "CAN-ALG-INEQ-REGION-IDENTIFY",
            "CAN-ALG-INEQ-HARDER-REGIONS",
        ],

        decision="approve",

        approved_canonical_id=(
            "CAN-ALG-INEQ-REGION-INTERPRET"
        ),

        approved_subject_domain="Algebra",

        approved_skill_name=(
            "Identify regions defined by "
            "linear inequalities"
        ),

        approved_description=(
            "Identify and interpret regions on "
            "Cartesian graphs defined by linear "
            "inequalities."
        ),

        approved_official_mappings=[

            OfficialToCanonicalMapping(
                official_source_id=(
                    "EDX-4MA1-F-2.8-E"
                ),
                canonical_id=(
                    "CAN-ALG-INEQ-REGION-INTERPRET"
                ),
                relationship="equivalent",
                confidence=1.0,
                mapping_method="human",
                review_status="approved",
            ),

            OfficialToCanonicalMapping(
                official_source_id=(
                    "EDX-4MA1-H-2.8-B"
                ),
                canonical_id=(
                    "CAN-ALG-INEQ-REGION-INTERPRET"
                ),
                relationship="equivalent",
                confidence=1.0,
                mapping_method="human",
                review_status="approved",
            ),

        ],

        reviewer_notes=(
            "Foundation simple regions and Higher "
            "harder regions represent the same "
            "underlying mathematical competency. "
            "The difference belongs in scope "
            "metadata rather than canonical skill "
            "identity."
        ),

        reviewed_by="human",
    ),


    # ============================================================
    # Decision 2
    # Approve inequality-symbol skill
    # ============================================================

    CanonicalReviewDecision(
        decision_id=(
            "REV-4MA1-T2-INEQ-SYMBOLS-001"
        ),

        proposal_type="mapping",

        source_ids=[
            "EDX-4MA1-F-2.8-A",
        ],

        decision="approve",

        approved_canonical_id=(
            "CAN-ALG-INEQ-SYMBOLS"
        ),

        approved_subject_domain="Algebra",

        approved_skill_name=(
            "Understand and use inequality symbols"
        ),

        approved_description=(
            "Understand and use the symbols "
            ">, <, \u2265 and \u2264."
        ),

        approved_official_mappings=[

            OfficialToCanonicalMapping(
                official_source_id=(
                    "EDX-4MA1-F-2.8-A"
                ),
                canonical_id=(
                    "CAN-ALG-INEQ-SYMBOLS"
                ),
                relationship="equivalent",
                confidence=1.0,
                mapping_method="human",
                review_status="approved",
            ),

        ],

        reviewer_notes=(
            "Approved as a distinct canonical "
            "skill for understanding and using "
            "inequality notation."
        ),

        reviewed_by="human",
    ),

]


# --------------------------------
# Merge candidates into the complete audit history
# --------------------------------

output = append_review_decisions(OUTPUT_FILE, decisions)


# --------------------------------
# Report
# --------------------------------

print("=" * 72)
print("HUMAN REVIEW DECISIONS")
print("=" * 72)


for decision in decisions:

    print()

    print(
        f"Decision ID: "
        f"{decision.decision_id}"
    )

    print(
        f"Type:        "
        f"{decision.proposal_type}"
    )

    print(
        f"Decision:    "
        f"{decision.decision}"
    )

    print("Sources:")

    for source_id in decision.source_ids:
        print(
            f"  - {source_id}"
        )

    print(
        f"Approved ID: "
        f"{decision.approved_canonical_id}"
    )

    print(
        f"Skill:       "
        f"{decision.approved_skill_name}"
    )

    print("Approved official mappings:")

    for mapping in (
        decision.approved_official_mappings
    ):
        print(
            f"  - "
            f"{mapping.official_source_id}"
            f" -> "
            f"{mapping.canonical_id}"
        )

    print(
        f"Reviewed by: "
        f"{decision.reviewed_by}"
    )


print()
print("=" * 72)

print(
    f"Review decisions total: "
    f"{output['decision_count']}"
)

print(
    f"Output: {OUTPUT_FILE}"
)

print("=" * 72)