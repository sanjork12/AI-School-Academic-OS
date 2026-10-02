import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from canonical_schema import (
    CanonicalConsolidationProposal,
)


INPUT_FILE = Path(
    "output/topic2_ai_mapping_proposals.json"
)

OUTPUT_FILE = Path(
    "output/topic2_ai_consolidation_proposals.json"
)


class ConsolidationBatch(BaseModel):
    proposals: list[
        CanonicalConsolidationProposal
    ]


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


load_dotenv()
client = OpenAI()

data = load_json(INPUT_FILE)

mapping_proposals = data.get(
    "proposals",
    []
)


# --------------------------------
# Only candidate new canonical nodes
# --------------------------------

candidate_nodes = []

for proposal in mapping_proposals:

    if proposal["action"] != "create_new":
        continue

    candidate_nodes.append(
        {
            "official_source_id":
                proposal["official_source_id"],

            "candidate_canonical_id":
                proposal["proposed_canonical_id"],

            "skill_name":
                proposal["proposed_skill_name"],

            "description":
                proposal["proposed_description"],

            "relationship":
                proposal["relationship"],

            "reasoning":
                proposal["reasoning"],
        }
    )


if len(candidate_nodes) < 2:
    raise ValueError(
        "Need at least two candidate canonical "
        "nodes for consolidation."
    )


prompt = f"""
You are reviewing candidate canonical curriculum
nodes proposed from official mathematics
curriculum objectives.

Your task is NOT to map official objectives.

Your task is to determine whether candidate
canonical nodes represent:

1. the same underlying mathematical skill and
   should be merged,

or

2. genuinely different mathematical skills and
   should remain separate.


IMPORTANT RULES:

1. Difficulty difference alone does NOT justify
   separate canonical skills.

   Examples such as:
   simple / harder,
   Foundation / Higher,
   basic / advanced

   may represent different scope or difficulty
   of the same underlying skill.

2. Different mathematical operations or cognitive
   actions MAY justify separate skills.

   Examples:

   understanding notation
   is different from
   solving an inequality.

   solving an inequality
   is different from
   graphing an inequality.

   graphing an inequality
   may be different from
   interpreting a feasible region.

3. Do not merge nodes merely because they share
   words such as "inequality", "quadratic",
   "linear", or "graph".

4. Prefer a stable canonical skill that can be
   reused across:

   - Foundation and Higher tiers
   - different exam boards
   - future curriculum versions

5. Canonical nodes should represent mathematical
   competency, not exam-board wording.

6. If multiple candidate nodes are the same
   underlying skill:

   action = "merge"

   source_canonical_ids must contain every
   candidate ID being merged.

   recommended_canonical_id should be a clean,
   stable CAN-ALG-... ID.

7. If candidate nodes represent genuinely
   different skills:

   action = "keep_separate"

   Do NOT place unrelated nodes into one proposal.

8. A keep_separate proposal should describe the
   specific candidate node or closely related
   candidate set being retained as distinct.

9. Every candidate canonical ID supplied below
   must appear in at least one consolidation
   proposal.

10. Do not invent syllabus requirements.

11. All proposals must have:

    review_status = "pending"

12. Reasoning should explain WHY the skills are
    the same or different.

13. Scope and difficulty should normally be
    represented later as metadata rather than
    creating duplicate canonical skills, unless
    the mathematical competency itself changes.

14. DECISION CONSISTENCY RULE:

    If two candidate nodes represent the same
    underlying mathematical competency and differ
    only by scope, difficulty, tier, complexity,
    or exam-board wording, you MUST recommend:

    action = "merge"

    Do not use "keep_separate" merely because one
    candidate is described as simple, harder,
    basic, advanced, Foundation, or Higher.

15. KEEP-SEPARATE RULE:

    Use "keep_separate" only when the mathematical
    competency itself is meaningfully different.

    Examples of meaningful differences include:

    - understanding notation vs solving
    - solving vs graphing
    - constructing a graph vs interpreting a region
    - linear inequality solving vs quadratic
      inequality solving when the mathematical
      procedure changes substantively

16. REASONING CONSISTENCY RULE:

    The selected action must agree with the
    reasoning.

    If the reasoning says that two candidates are
    the same underlying skill and that their
    difference should be represented as scope or
    difficulty metadata, the action must be
    "merge", not "keep_separate".


CANDIDATE CANONICAL NODES:

{json.dumps(
    candidate_nodes,
    ensure_ascii=False,
    indent=2
)}
"""


print()
print("Calling AI Canonical Consolidator...")
print()


response = client.responses.parse(
    model="gpt-5.6-luna",
    input=prompt,
    text_format=ConsolidationBatch,
)


result = response.output_parsed


if result is None:
    raise RuntimeError(
        "No structured output returned."
    )


# --------------------------------
# Safety validation
# --------------------------------

candidate_ids = {
    item["candidate_canonical_id"]
    for item in candidate_nodes
}

covered_ids = set()
coverage_count = {}

for proposal in result.proposals:

    if proposal.review_status != "pending":
        raise ValueError(
            "AI consolidation proposal "
            "must remain pending."
        )

    if not proposal.source_canonical_ids:
        raise ValueError(
            "Consolidation proposal has "
            "no source canonical IDs."
        )

    for source_id in proposal.source_canonical_ids:

        if source_id not in candidate_ids:
            raise ValueError(
                f"Unknown candidate canonical ID: "
                f"{source_id}"
            )

        covered_ids.add(source_id)
        coverage_count[source_id] = (
            coverage_count.get(source_id, 0) + 1
        )

    if not (
        proposal.recommended_canonical_id
        .startswith("CAN-ALG-")
    ):
        raise ValueError(
            "Recommended canonical ID must "
            "start with CAN-ALG-"
        )


missing_ids = (
    candidate_ids - covered_ids
)

if missing_ids:
    raise ValueError(
        "Some candidate nodes were not reviewed: "
        f"{sorted(missing_ids)}"
    )

duplicate_coverage = {
    source_id: count
    for source_id, count in coverage_count.items()
    if count > 1
}

if duplicate_coverage:
    raise ValueError(
        "Candidate nodes appeared in multiple "
        "consolidation proposals: "
        f"{duplicate_coverage}"
    )


# --------------------------------
# Save
# --------------------------------

output = {
    "model": "gpt-5.6-luna",
    "candidate_count": len(
        candidate_nodes
    ),
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

print("=" * 72)
print("AI CANONICAL CONSOLIDATION PROPOSALS")
print("=" * 72)


for proposal in result.proposals:

    print()

    print(
        "Sources:"
    )

    for source_id in (
        proposal.source_canonical_ids
    ):
        print(
            f"  - {source_id}"
        )

    print(
        f"Action:       "
        f"{proposal.action}"
    )

    print(
        f"Recommended:  "
        f"{proposal.recommended_canonical_id}"
    )

    print(
        f"Skill:        "
        f"{proposal.skill_name}"
    )

    print(
        f"Confidence:   "
        f"{proposal.confidence}"
    )

    print(
        f"Review:       "
        f"{proposal.review_status}"
    )

    print(
        f"Reasoning:    "
        f"{proposal.reasoning}"
    )


print()
print("=" * 72)

print(
    f"Candidate nodes reviewed: "
    f"{len(candidate_nodes)}"
)

print(
    f"Consolidation proposals:  "
    f"{len(result.proposals)}"
)

print(
    f"Output: {OUTPUT_FILE}"
)

print("=" * 72)