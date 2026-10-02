# P6UI.5 — Governed pedagogical qualification

This core bridge evaluates a current governed Learning Specification, records
pedagogical prerequisites and a non-executable role contract, and gates future
lesson authoring. It generates no explanations, examples, questions, answers,
student-facing text, slide text or pedagogical content. Provider calls are zero.

## Inspection and existing architecture

`output/p6ui5_pedagogical_specification/inspection.json` was saved before new core
implementation. It records inspected file hashes, actual P3B/P3C/profile reads and
all fifteen Standard Lesson roles. Generic concepts include source references,
planned coverage, candidate slots, constraints, warning propagation and separate
structural/content readiness.

The existing P3B maps every capability to a calculation-method slot. That is safe
only within its demonstrated scope, not a universal interpretation of “understand”,
“identify” or “interpret”. P3C checks role/slot coverage and rejects unsupported
boundary claims; its candidate slots do not prove teaching content is complete.
Its absence of explicit success-criteria fields is not evidence that a new topic
can support valid learning checks without criteria.

P3B block order is not a mandatory sequence. P5's Gold profiles add SD-specific
role order, density and suggested timing; the adapter explicitly requires
`standard-deviation` and its three existing learning-requirement types. P4/P5
consume block lineage, learning/assessment references, role kinds, supported task
forms, support modes and validated scope. P6 numerical authoring additionally uses
SD-specific template, mathematical/provenance rules and an application-owned
formula hint. None are automatically reused for Topic 2.

## Input and versions

Input: `governed-learning-specification/1`, authenticated through the existing
`GovernedLearningService.validate_learning_spec`. Detached JSON flags do not grant
eligibility. Exact package, source, target, tier, canonical decision and policy
bindings remain checked upstream.

New models are `pedagogical-spec-eligibility/1`,
`governed-pedagogical-specification/1`,
`governed-pedagogical-role-contract/1`, `lesson-authoring-eligibility/1` and
`pedagogical-qualification/1`. Policy is `governed-pedagogical-readiness/1`, with a
deterministic digest. The separate authoring gate is `governed-lesson-authoring-gate/1`.

## Eligibility and success criteria

Statuses are ELIGIBLE, ELIGIBLE_WITH_WARNINGS, REVIEW_REQUIRED, BLOCKED and
UNSUPPORTED. Each result contains reasons, missing requirements, warnings,
evidence hashes, learning-spec hash, policy version, source identity, input
requirements and role evidence.

For `EDX-4MA1-F-2.8-A`, source/tier bindings, learning intentions and reviewed
canonical action meaning are available. Pedagogical eligibility is REVIEW_REQUIRED
because all four required inputs remain absent:

- SUCCESS_CRITERIA_REQUIRED: reviewed observable performance criteria; the broad
  capability wording does not establish a rubric, threshold or valid check.
- ACTIVITY_SCOPE_REQUIRED: supported task/activity scope and its learning alignment.
- CHECK_ALIGNMENT_REQUIRED: an evidence-backed relationship between checks,
  intended learning and the success criteria.
- PEDAGOGICAL_AUTHORING_REQUIRED: a bounded reviewed policy/adapter that defines
  how to structure those supported activities and checks.

The current governed-learning/1 contract explicitly records these gaps. Its
independent validator rejects inserting claims to make them appear available.
Therefore this policy has no eligible production construction path for current
inputs. A stronger governed evidence contract and adapter require a new policy;
there is no permissive fallback or test-only approval path.

Concept knowledge, prerequisite evidence, misconceptions and reviewed assessment
examples are not universally mandatory. They remain OPTIONAL_UNAVAILABLE until a
chosen role/activity actually depends on them. For example, concept explanation
requires conceptual meaning; worked-assessment roles require reviewed assessment
structure; a prerequisite-dependent activity requires that prerequisite evidence.
Existing SD assessment assets are never required for an unrelated topic.

Canonical action wording is retained verbatim and classified as reviewed capability
meaning, not a procedural calculation method, concrete performance task or task
graph. “Know”, “do”, concrete task performance and assessment remain distinct.

## Pedagogical model and construction result

The governed pedagogical schema binds the complete source learning contract and
hash, eligibility, policy, exact scope, instructional-goal references, role
contract, potential phase references, activity constraints, warnings and governance.
Phase fields hold contract references, not authored explanations or activities.

`build_pedagogical_spec` re-evaluates eligibility and rejects absent/stale evidence.
No actual pedagogical specification is constructed for the primary target, and no
`pedagogical-specification.json` is saved. The schema and validator define a closed
boundary; they are not evidence that a generic pedagogical constructor is ready.
Validation rejects forged specimens, including invented phases and copied SD roles.

Instead an immutable `pedagogical-qualification/1` record stores the real source,
eligibility, role contract and explicit authoring decision. Valid qualification
evidence does not mean valid or eligible pedagogy.

## Role policy

Role requirements are planning constraints, not a lesson plan or content brief.
Every role has an evidence reason, source/learning references and
`enabled_for_authoring=false`. No duration, mandatory sequence or profile is chosen.

`scope_framing` is required solely to retain exact learning-scope identity in a
future plan. This is this milestone's deterministic traceability policy; it does
not claim that every topic needs a Standard Lesson orientation slide.
`non_assessing_summary` is optional; an exit check is not inferred from it.

Concept explanation/retrieval, method/formula instruction, data-backed demonstration,
numerical practice and assessment/check families remain unsupported pending their
specific evidence. All SL-01–SL-15 compatibility entries remain UNSUPPORTED; a
family association is never an executable binding to an SD role.

The inspected legacy roles are classified as follows:

- SL-01: framing/orientation; zero content-item target in the standard profile.
- SL-02, SL-03: concept explanation/visual representation.
- SL-04, SL-13: concept-dependent retrieval/checks with assessment alignment.
- SL-05: calculation-method instruction.
- SL-06: calculation-dependent mini worked example.
- SL-07: summary-statistics task/method, specifically SD.
- SL-08, SL-09: worked assessment connections.
- SL-10, SL-11: guided numerical practice; SL-11's P6 policy is SD-specific.
- SL-12: independent numerical practice.
- SL-14: calculation/application check.
- SL-15: assessment-dependent exit check plus summary.

Presence in the legacy standard profile is not universal requiredness. Optionality
and sequencing are profile decisions: the focused-review profile omits several
standard-role expansions. The new policy introduces no automatic 15-role plan.

## Provenance, warnings and governance

Each input requirement, action binding and role element has classifications,
evidence references, learning-intention IDs, source IDs and a rule identifier.
LEARNING_SPEC_DERIVED marks learning evidence; CANONICAL_DERIVED/HUMAN_REVIEWED
apply only to the historical reviewed canonical action; DETERMINISTIC_POLICY marks
the new planning constraints. MODEL_PROPOSED and TRUSTED_REFERENCE are supported
labels but are not claimed by these outputs. No pedagogical rule is represented as
a new human-approved academic judgment.

All source warnings propagate unchanged, including unresolved glyph/review warnings.
The no-generic-calculation-mapping warning is added. Missing input states are
explicit: MISSING, OPTIONAL_UNAVAILABLE, REVIEW_REQUIRED or AUTHORING_REQUIRED.
The latter permits future controlled human or AI work but does not trigger it.
Governance remains QUALIFICATION_EVIDENCE_ONLY, approved=false, published=false.

## Separate lesson-authoring gate

The primary target's `lesson-authoring-eligibility/1` is BLOCKED. A valid
pedagogical specification, executable required role contracts, role-specific
validators and resolution of required pedagogical gaps are missing. Traceable
framing constraints alone are insufficient. This result cannot dispatch a model,
route to SD authoring or create a P6 brief. Any supplied fabricated pedagogical
specification is independently validated and rejected.

## Services, validation and storage

`GovernedPedagogyService(learning_service)` exposes:

- `evaluate_pedagogical_spec_eligibility(learning_spec, expected_learning_hash=None)`
- `build_pedagogical_spec(learning_spec, eligibility)`
- `validate_pedagogical_spec(spec)`
- `evaluate_lesson_authoring_eligibility(spec=None, learning_spec=...)`
- `qualify`, `validate_qualification`, `persist_qualification`, `read_qualification`
- `read_pedagogical_spec(id)`, which returns NOT_CONSTRUCTED for current records.

Independent validation checks current learning provenance and hash, tier/scope,
policy, exact role partition and provenance, missing inputs, warning propagation,
authoring gates and governance. It does not call the qualification constructor.
Forged role requirements are diagnosed even when overall pedagogy is ineligible.

Canonical sorted UTF-8 JSON defines the qualification's semantic hash. Time appears
only in its separate receipt. Runtime defaults to
`var/p6ui/runs/governed-pedagogy/`, already ignored. Reads verify all artifact hashes,
cross-artifact equality and current sources. Repeated writes reuse the original
record; interrupted partial writes are not automatically repaired. Hashes detect
local drift, not an adversary rewriting all code and evidence together.

Selected evidence is additive under `output/p6ui5_pedagogical_specification/`.
No API or frontend change is needed. Tests use existing P6UI.4 evidence, not a new
parse or model response. Run `python -X utf8 -B -m unittest tests_p0.test_governed_pedagogy`.

## Remaining P6A.7 gap and limitations

P6A.7 needs governed observable success criteria, bounded tasks/activities and
checks, a reviewed pedagogical adapter, source-bound role contracts, controlled
content provenance rules and independent role validators. Future candidates must
be explicitly labelled and reviewed; they cannot become trusted content by flags.
Optional enrichments become required only when a proposed activity uses them.

Only the existing known 4MA1 Topic 2 evidence has been demonstrated. No eligible
pedagogical construction or authoring path is claimed, and no pedagogical phases,
examples or practice items have been generated. Existing P3B/P3C/P4/P5/P6 behavior
and all historical review decisions remain unchanged.
