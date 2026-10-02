import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from canonical_schema import (
    AICanonicalMappingProposal,
)


# --------------------------------
# Configuration
# --------------------------------

FOUNDATION_FILE = Path(
    "output/topic2_foundation_parsed.json"
)

HIGHER_FILE = Path(
    "output/topic2_higher_parsed.json"
)

CANONICAL_FILE = Path(
    "output/topic2_canonical_prototype.json"
)

OUTPUT_FILE = Path(
    "output/topic2_ai_mapping_proposals.json"
)


# --------------------------------
# Structured output wrapper
# --------------------------------

class ProposalBatch(BaseModel):
    proposals: list[
        AICanonicalMappingProposal
    ]


# --------------------------------
# Load environment + client
# --------------------------------

load_dotenv()

client = OpenAI()


# --------------------------------
# Helper functions
# --------------------------------

def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def find_objective(
    curriculum_data,
    source_id
):
    for subtopic in curriculum_data["subtopics"]:

        for objective in subtopic["objectives"]:

            if objective.get("source_id") == source_id:

              return {
                  "source_id": source_id,
                  "subtopic_code": subtopic["code"],
                  "subtopic_name": subtopic["name"],
                  "official_text": objective[
                     "official_text"
              ],
}

    raise ValueError(
        f"Official objective not found: "
        f"{source_id}"
    )


# --------------------------------
# Load curriculum
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


# --------------------------------
# Test objectives
# --------------------------------

test_ids = [
    "EDX-4MA1-F-2.8-A",
    "EDX-4MA1-F-2.8-B",
    "EDX-4MA1-F-2.8-C",
    "EDX-4MA1-F-2.8-D",
    "EDX-4MA1-F-2.8-E",
    "EDX-4MA1-H-2.8-A",
    "EDX-4MA1-H-2.8-B",
]


test_objectives = []

for source_id in test_ids:

    if "-F-" in source_id:
        curriculum = foundation_data
    else:
        curriculum = higher_data

    test_objectives.append(
        find_objective(
            curriculum,
            source_id
        )
    )


# --------------------------------
# Existing canonical objectives
# --------------------------------

existing_canonical = (
    canonical_data[
        "canonical_objectives"
    ]
)


# --------------------------------
# Prompt
# --------------------------------

prompt = f"""
You are mapping official mathematics curriculum
objectives into a canonical curriculum graph.

IMPORTANT RULES:

1. The official curriculum text is immutable.
   Never rewrite or correct it.

2. For each official objective, decide whether
   it should:

   - map_existing:
     map to an existing canonical objective

   OR

   - create_new:
     propose a new canonical objective.

3. Do NOT force an objective into an existing
   canonical objective merely because the topic
   is similar.

4. Relationship describes the OFFICIAL objective
   relative to the CANONICAL objective:

   equivalent:
   approximately the same skill and scope.

   narrower:
   the official objective covers a restricted
   subset of the canonical skill.

   broader:
   the official objective covers more than the
   canonical skill.

   partial:
   the two overlap but neither cleanly contains
   the other.

5. If action is map_existing:

   proposed_canonical_id MUST exactly match one
   of the existing canonical IDs.

   proposed_skill_name must be null.

   proposed_subject_domain must be null.

   proposed_description must be null.

6. If action is create_new:

   create a stable canonical ID beginning with:

   CAN-ALG-

   Also provide:
   proposed_subject_domain
   proposed_skill_name
   proposed_description

   For the current Edexcel 4MA1 Topic 2,
   proposed_subject_domain is Algebra.

7. Do not merge distinct mathematical skills
   simply to reduce the number of canonical
   objectives.

8. Pay attention to tier-specific scope and
   restrictions.

   Difficulty, tier, or scope differences alone
   must not create a new canonical competency.

9. Confidence must be between 0 and 1.

10. All proposals are pending human review.

11. Reasoning should be concise and explain the
    curriculum-mapping decision. Do not invent
    syllabus requirements that are not present
    in the supplied data.
12. OBJECTIVE BOUNDARY RULE:

    Each official_source_id must be mapped using
    ONLY the skill explicitly stated in that
    objective's official_text.

    Do not import requirements from neighboring
    objectives in the same subtopic.

    Do not combine multiple official objectives
    into one proposal merely because they belong
    to the same subtopic.

    The subtopic name and notes are context only.
    They must never expand the scope of the
    official objective.

13. EVIDENCE RULE:

    Every claim in the reasoning about what an
    official objective requires must be directly
    supported by that objective's official_text.

    If the official_text only asks students to
    understand or use notation, do not infer that
    it also requires solving, graphing, proving,
    or applying that notation unless explicitly
    stated.

14. GRANULARITY RULE:

    Preserve meaningful differences between
    notation, solving, representation, graphing,
    interpretation, and application skills.

    Do not collapse these into a broader skill
    unless the official objective itself combines
    them.



EXISTING CANONICAL OBJECTIVES:

{json.dumps(
    existing_canonical,
    ensure_ascii=False,
    indent=2
)}


OFFICIAL OBJECTIVES TO MAP:

{json.dumps(
    test_objectives,
    ensure_ascii=False,
    indent=2
)}
"""


# --------------------------------
# Call model
# --------------------------------

print()
print("Calling AI Canonical Mapper...")
print()


response = client.responses.parse(
    model="gpt-5.6-luna",
    input=prompt,
    text_format=ProposalBatch,
)


result = response.output_parsed


if result is None:
    raise RuntimeError(
        "No structured output returned."
    )


# --------------------------------
# Safety checks
# --------------------------------

returned_ids = {
    proposal.official_source_id
    for proposal in result.proposals
}

expected_ids = set(test_ids)


if returned_ids != expected_ids:

    missing = (
        expected_ids - returned_ids
    )

    unexpected = (
        returned_ids - expected_ids
    )

    raise ValueError(
        "AI returned incorrect objective set. "
        f"Missing: {sorted(missing)} "
        f"Unexpected: {sorted(unexpected)}"
    )


existing_ids = {
    item["canonical_id"]
    for item in existing_canonical
}


for proposal in result.proposals:

    if proposal.review_status != "pending":
        raise ValueError(
            f"{proposal.official_source_id}: "
            f"AI proposal must remain pending."
        )

    if proposal.action == "map_existing":

        if (
            proposal.proposed_canonical_id
            not in existing_ids
        ):
            raise ValueError(
                f"{proposal.official_source_id}: "
                f"AI referenced unknown canonical ID "
                f"{proposal.proposed_canonical_id}"
            )

        if (
            proposal.proposed_subject_domain
            is not None
            or proposal.proposed_skill_name
            is not None
            or proposal.proposed_description
            is not None
        ):
            raise ValueError(
                f"{proposal.official_source_id}: "
                f"map_existing must not create "
                f"new canonical metadata."
            )

    elif proposal.action == "create_new":

        if not (
            proposal.proposed_canonical_id
            .startswith("CAN-ALG-")
        ):
            raise ValueError(
                f"{proposal.official_source_id}: "
                f"new canonical ID must start "
                f"with CAN-ALG-"
            )

        if not proposal.proposed_subject_domain:
            raise ValueError(
                f"{proposal.official_source_id}: "
                f"create_new requires subject domain."
            )

        if not proposal.proposed_skill_name:
            raise ValueError(
                f"{proposal.official_source_id}: "
                f"create_new requires skill name."
            )

        if not proposal.proposed_description:
            raise ValueError(
                f"{proposal.official_source_id}: "
                f"create_new requires description."
            )


# --------------------------------
# Save proposals
# --------------------------------

output = {
    "model": "gpt-5.6-luna",
    "proposal_count": len(
        result.proposals
    ),
    "proposals": [
        proposal.model_dump()
        for proposal in result.proposals
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
# Report
# --------------------------------

print("=" * 70)
print("AI CANONICAL MAPPING PROPOSALS")
print("=" * 70)

for proposal in result.proposals:

    print()
    print(
        proposal.official_source_id
    )

    print(
        f"  action:       "
        f"{proposal.action}"
    )

    print(
        f"  canonical:    "
        f"{proposal.proposed_canonical_id}"
    )

    print(
        f"  relationship: "
        f"{proposal.relationship}"
    )

    print(
        f"  confidence:   "
        f"{proposal.confidence}"
    )

    print(
        f"  review:       "
        f"{proposal.review_status}"
    )

    print(
        f"  reasoning:    "
        f"{proposal.reasoning}"
    )


print()
print("=" * 70)

print(
    f"Proposals created: "
    f"{len(result.proposals)}"
)

print(
    f"Output: {OUTPUT_FILE}"
)

print("=" * 70)
