import json
from pathlib import Path

from canonical_schema import (
    CanonicalLearningObjective,
    OfficialToCanonicalMapping,
)


# --------------------------------
# Input files
# --------------------------------

FOUNDATION_FILE = Path(
    "output/topic2_foundation_parsed.json"
)

HIGHER_FILE = Path(
    "output/topic2_higher_parsed.json"
)

OUTPUT_FILE = Path(
    "output/topic2_canonical_prototype.json"
)


# --------------------------------
# Load official curriculum
# --------------------------------

foundation_data = json.loads(
    FOUNDATION_FILE.read_text(
        encoding="utf-8"
    )
)

higher_data = json.loads(
    HIGHER_FILE.read_text(
        encoding="utf-8"
    )
)


# --------------------------------
# Helper: find official objective
# --------------------------------

def find_objective(
    curriculum_data,
    subtopic_code,
    objective_code
):
    for subtopic in curriculum_data["subtopics"]:

        if subtopic["code"] != subtopic_code:
            continue

        for objective in subtopic["objectives"]:

            if objective["code"] == objective_code:
                return objective

    raise ValueError(
        f"Objective not found: "
        f"{subtopic_code}-{objective_code}"
    )


# --------------------------------
# Retrieve official objectives
# --------------------------------

foundation_26a = find_objective(
    foundation_data,
    "2.6",
    "A"
)

higher_26a = find_objective(
    higher_data,
    "2.6",
    "A"
)

higher_26b = find_objective(
    higher_data,
    "2.6",
    "B"
)

foundation_27a = find_objective(
    foundation_data,
    "2.7",
    "A"
)

higher_27a = find_objective(
    higher_data,
    "2.7",
    "A"
)

higher_27b = find_objective(
    higher_data,
    "2.7",
    "B"
)

higher_27c = find_objective(
    higher_data,
    "2.7",
    "C"
)

higher_27d = find_objective(
    higher_data,
    "2.7",
    "D"
)

foundation_24a = find_objective(
    foundation_data,
    "2.4",
    "A"
)

foundation_24b = find_objective(
    foundation_data,
    "2.4",
    "B"
)

foundation_28e = find_objective(
    foundation_data,
    "2.8",
    "E"
)

higher_28b = find_objective(
    higher_data,
    "2.8",
    "B"
)



# --------------------------------
# Ground-truth safety check
# --------------------------------

if (
    foundation_26a["official_text"]
    != higher_26a["official_text"]
):
    raise ValueError(
        "Foundation 2.6A and Higher 2.6A "
        "do not have identical official text. "
        "Manual review required."
    )


# --------------------------------
# Canonical objectives
# --------------------------------

canonical_objectives = [
    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-SIMLINEAR-SOLVE"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Solve simultaneous linear equations"
        ),
        description=(
            "Solve two simultaneous linear equations "
            "in two unknowns exactly."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-SIMLINEAR-GRAPH"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Interpret simultaneous linear equations "
            "graphically"
        ),
        description=(
            "Interpret simultaneous linear equations "
            "as lines and their common solution as "
            "the point of intersection."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-QUAD-FACTOR"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Solve quadratic equations by factorisation"
        ),
        description=(
            "Solve quadratic equations by factorisation."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-QUAD-FORMULA-SQUARE"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Solve quadratic equations using the "
            "quadratic formula or completing the square"
        ),
        description=(
            "Solve quadratic equations using the "
            "quadratic formula or by completing the square."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-QUAD-CONTEXT"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Form and solve quadratic equations "
            "from contextual data"
        ),
        description=(
            "Form and solve quadratic equations "
            "from data given in a context."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-SIM-LINEAR-QUAD"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Solve simultaneous linear and "
            "quadratic equations"
        ),
        description=(
            "Solve simultaneous equations in two "
            "unknowns where one equation is linear "
            "and the other is quadratic."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-LINEAR-EQUATION-SOLVE"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Solve linear equations in one unknown"
        ),
        description=(
            "Solve linear equations in one unknown, "
            "including equations where the unknown "
            "appears on either or both sides."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-LINEAR-EQUATION-FORM"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Form linear equations from given data"
        ),
        description=(
            "Set up simple linear equations from "
            "given data."
        ),
        status="approved",
    ),

    CanonicalLearningObjective(
        canonical_id=(
            "CAN-ALG-INEQ-REGION-INTERPRET"
        ),
        subject_domain="Algebra",
        skill_name=(
            "Identify regions defined by "
            "linear inequalities"
        ),
        description=(
            "Identify and interpret regions on "
            "Cartesian graphs defined by linear "
            "inequalities."
        ),
        status="approved",
    ),
]


# --------------------------------
# Official → Canonical mappings
# --------------------------------

mappings = [
    OfficialToCanonicalMapping(
        official_source_id=(
            foundation_26a["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-SIMLINEAR-SOLVE"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            higher_26a["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-SIMLINEAR-SOLVE"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            higher_26b["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-SIMLINEAR-GRAPH"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            foundation_27a["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-QUAD-FACTOR"
        ),
        relationship="narrower",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            higher_27a["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-QUAD-FACTOR"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            higher_27b["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-QUAD-FORMULA-SQUARE"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            higher_27c["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-QUAD-CONTEXT"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            higher_27d["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-SIM-LINEAR-QUAD"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            foundation_24a["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-LINEAR-EQUATION-SOLVE"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            foundation_24b["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-LINEAR-EQUATION-FORM"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),

    OfficialToCanonicalMapping(
        official_source_id=(
            foundation_28e["source_id"]
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
            higher_28b["source_id"]
        ),
        canonical_id=(
            "CAN-ALG-INEQ-REGION-INTERPRET"
        ),
        relationship="equivalent",
        confidence=1.0,
        mapping_method="human",
        review_status="approved",
    ),
]


# --------------------------------
# Build output
# --------------------------------

output = {
    "prototype": "Topic 2.6",
    "canonical_objectives": [
        item.model_dump()
        for item in canonical_objectives
    ],
    "mappings": [
        item.model_dump()
        for item in mappings
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


# --------------------------------
# Summary
# --------------------------------

print()
print("=" * 60)
print("CANONICAL CURRICULUM PROTOTYPE")
print("=" * 60)

print(
    f"Canonical objectives: "
    f"{len(canonical_objectives)}"
)

print(
    f"Official mappings:    "
    f"{len(mappings)}"
)

print()

for mapping in mappings:
    print(
        f"{mapping.official_source_id}"
        f"  --[{mapping.relationship}]-->  "
        f"{mapping.canonical_id}"
    )

print()
print(f"Output: {OUTPUT_FILE}")
print("=" * 60)