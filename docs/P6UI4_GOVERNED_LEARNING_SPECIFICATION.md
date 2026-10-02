# P6UI.4 — Governed Learning Specification

This milestone qualifies bounded, reviewable learning-intention evidence from an
authenticated AcademicCapabilityPackage. It does not publish academic truth or
generate pedagogy, lessons, questions, exams or presentations. Provider calls are
zero. The P3A Standard Deviation pipeline is unchanged.

## Inspection before implementation

`output/p6ui4_learning_specification/inspection.json` was saved before construction
code existed. It records inspected source hashes and the actual Standard Deviation
read result: one concept, three learning requirements and two reviewed examples.
The inspection separates generic learning contracts from topic catalog entries,
product aliases, concept/competency/task IDs, curriculum excerpt and snapshot IDs.

`LearningSpecificationService` obtains current teacher and assessment views and
checks their upstream provenance agrees. `learning_core` derives concept,
capability and evidenced task-form requirements. It does not invent prerequisites,
teaching sequences, formula memorisation, misconceptions or assessment statistics.
`product_reader` validates current usable snapshots on an ephemeral database copy.
The existing teacher product requires a reviewed assessment example. A capability
learning requirement itself can have an empty evidence-example list; only a
task-form requirement requires matching assessment examples.

## Eligibility policy and trust boundary

Model: `learning-spec-eligibility/1`.
Policy: `bounded-reviewed-learning-intentions/1`, with a deterministic policy digest.
Statuses: ELIGIBLE, ELIGIBLE_WITH_WARNINGS, REVIEW_REQUIRED, BLOCKED, UNSUPPORTED.
Each result carries reasons, missing requirements, warnings, evidence references,
package hash, target ID, exact objective results and scope membership.

The policy authorizes **BOUNDED_REVIEWABLE_LEARNING_INTENTIONS_ONLY**. It is not a
replacement for P3A's trusted production service, and it does not turn the existing
capability package's conservative downstream flags on. Those historical package
bytes and eligibility flags remain unchanged. This new policy asks a narrower
question: can an explicitly reviewed equivalent skill meaning be restated as a
learning intention for review?

Required evidence for every selected objective:

- Current valid capability package, source document, selected target, parsed,
  validation and tree bindings. Source IDs and tier must match exactly.
- Exactly one unambiguous canonical binding with an `equivalent` relationship.
- A concrete recorded human approval decision for that exact source ID and
  canonical ID, not just a legacy `approved` label.
- Exact agreement between the decision's approved description and the canonical
  wording, with the mapping present in the approved official mappings.

The pinned historical review record qualifies the historical canonical meaning
only. It does not human-approve the uploaded document, verify every extracted
glyph, approve the new specification or supply a trusted snapshot. These all stay
explicitly false in `governance_state`. The engineering policy grants no new
academic review decision; no journal or trusted database is written.

Trusted snapshots, assessment examples and concept/task graphs remain required
for the corresponding stronger claims or production publication. They are not
artificial prerequisites for this limited skill restatement. In particular, this
contract emits no conceptual-knowledge claim, task-form claim, scored criterion or
assessment-generation claim without those sources. This bounded qualification
does not make a target eligible for pedagogy.

## Exact scope and partial coverage

The service evaluates topic, subtopic and single-objective selections already
supported by `selected-curriculum-target/2`. Every selected objective is present in
`objective_results`. It reports independently ready IDs and unresolved IDs;
`excluded_source_ids` remains empty because no automatic filtering is permitted.
If any selected objective is unresolved, the complete scope is REVIEW_REQUIRED
and construction is refused. An empty selected scope is BLOCKED. Invalid/stale
evidence is BLOCKED; unsupported profiles are UNSUPPORTED.

A caller must explicitly obtain a smaller selected-target identity and capability
package to construct an independently complete objective. Foundation Topic 2 has
25 objectives: two have qualifying recorded reviews, 23 do not. Higher has 16:
one qualifies and 15 do not. These counts differ from the 6/7 historical mapping
counts because mapping presence does not establish a recorded approval receipt.

The first bounded objective is `EDX-4MA1-F-2.8-A`, bound to
`CAN-ALG-INEQ-SYMBOLS` and `REV-4MA1-T2-INEQ-SYMBOLS-001`.
Foundation `EDX-4MA1-F-2.8-E` and Higher `EDX-4MA1-H-2.8-B` have separate explicit
mappings to `CAN-ALG-INEQ-REGION-INTERPRET`. Canonical reuse never merges their tier,
source identity, learning-intention identity or package hash.

## Output model and provenance

Model: `governed-learning-specification/1`.
Construction: `governed-learning-construction/1`.

The output binds source package hash, exact selected target, policy hash and
eligibility hash. It contains original learning-objective wording and notes,
separate canonical semantics, learning intentions, broad task-capability meaning,
explicit evidence gaps, warnings, evidence hashes and governance state.

Each semantic element has classifications, evidence references, source IDs and a
transformation rule. Supported classifications are SOURCE_DERIVED,
CANONICAL_DERIVED, DETERMINISTIC_TRANSFORMATION, MODEL_PROPOSED, HUMAN_REVIEWED and
TRUSTED_SNAPSHOT. Current outputs use SOURCE_DERIVED for exact parsed wording,
CANONICAL_DERIVED + HUMAN_REVIEWED for the recorded canonical meaning, and
DETERMINISTIC_TRANSFORMATION for the bounded learning-intention transformation.
HUMAN_REVIEWED never labels the whole specification. No current element claims
MODEL_PROPOSED or TRUSTED_SNAPSHOT provenance.

The only learning-intention transformation is:

`Student should be able to: ` + exact recorded approved canonical description.

This follows the existing P3A capability-prefix pattern without inventing a method,
activity, success threshold or teaching sequence. Source wording is never replaced
by the canonical wording. Knowledge and action remain separate: conceptual
knowledge is unavailable, while the broad approved action meaning is bound to its
canonical skill. Concrete task forms remain an empty list with an explicit missing
evidence state.

## Unavailable fields, warnings and future authoring

Success criteria are REVIEW_REQUIRED: there is no approved rubric, performance
threshold or sufficiently specific criterion. Prerequisites, misconceptions,
concept meanings, concept/skill/task relations and reviewed assessment examples
are MISSING. Each field has an explicit reason, empty claims, provenance and a
nonblocking flag for this limited construction scope. Empty claims mean unavailable
evidence, not a claim that students need no prerequisites or have no misconceptions.

All capability warnings propagate exactly, including human-review and glyph
warnings. Additional warnings describe the bounded construction and unavailable
fields. A warning does not automatically invalidate a skill restatement; source or
binding integrity errors always block. No warning is silently marked resolved.

The missing fields are not automatically MODEL_AUTHORING_REQUIRED because human
curation could supply them. If controlled AI authoring is introduced later, it must
produce separately labelled MODEL_PROPOSED candidates with explicit source IDs,
scope, evidence and unresolved assertions. Success criteria need approved observable
performance rules; prerequisite edges and misconception claims need their own
evidence. Candidates cannot be relabelled SOURCE_DERIVED or HUMAN_REVIEWED before
the appropriate review. No model calls or candidate authoring occur here.

## Assessment distinction and next pedagogy boundary

Existing P3A provides reviewed examples through `teacher-topic/2` and
`assessment-intelligence/1`; its production composition remains unchanged. The new
bounded contract does not require Standard Deviation assets or fabricate substitute
examples. Examples are optional for a plain reviewed skill intention, but required
when making supported task-form or assessment-specific claims.

Before a pedagogical adapter can consume this evidence, the project must define
and review its required success criteria, concepts/task relations, activity scope
and any assessment-alignment evidence. It also needs an explicit contract adapter
and the applicable target-specific trust checks. Missing prerequisites and
misconceptions must stay visible unless evidence is supplied; this milestone does
not imply every optional field must be populated before all future pedagogy.
No teaching sequence, difficulty, question template or learning activity is emitted.

## Services, validation, determinism and storage

`GovernedLearningService(capability_service)` provides:

- `evaluate_learning_spec_eligibility(package, expected_package_hash=None)`
- `build_learning_spec(package, eligibility_result)`
- `validate_learning_spec(spec)`
- `persist(spec)` and `read_learning_spec(id)`

Core rules live under `academic_os/governed_learning`. No new frontend or HTTP
workflow is needed for this milestone. Callers use the existing capability service
and the new independent core service.

Construction recomputes eligibility and rejects stale policy/results. Independent
validation never calls the constructor: it checks source/target/package identity,
exact scope, original text, canonical description and reviews, deterministic
intention rule, provenance classification, evidence references, missing-field
claims, warnings and governance state. Stored reads revalidate current sources and
all recorded artifact hashes. Invalid evidence cannot be published by this service.

Canonical sorted UTF-8 JSON determines semantic SHA-256. Timestamp is kept only in
a separate immutable receipt. Default runtime storage is
`var/p6ui/runs/governed-learning/<semantic-sha256>/`, already gitignored. Each record
contains construction input, eligibility, specification, validation and receipt.
Repeated persistence reuses existing records; interrupted partial writes are not
automatically repaired. Read validation requires the referenced ingestion evidence.
Local hashes detect drift, not an adversary rewriting all code and evidence together.

Selected acceptance evidence is additive under
`output/p6ui4_learning_specification/`. Historical P6UI.3B files and v1.10 remain
unchanged. The stored comparison identifies common learning concepts, legacy
teacher/assessment fields, new per-element provenance and missing evidence.

Tests: `python -X utf8 -B -m unittest tests_p0.test_governed_learning`.
Acceptance reuses completed P6UI.3A runs; no new curriculum parse is performed.

The demonstrated curriculum remains the exact known 2017 4MA1 Topic 2 profile.
The model structure is reusable, but arbitrary curricula are not qualified. Each
specification has one tier and exact selected scope. Qualified historical decisions
are not current trusted snapshot receipts; production publication remains separate.
