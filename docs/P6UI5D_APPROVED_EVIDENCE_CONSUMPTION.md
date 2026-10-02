# P6UI.5D — approved evidence consumption

P6UI.5C recorded the user's real decision and validated the approved evidence
pack. Eligibility remained REVIEW_REQUIRED because P6UI.5 only evaluated the
Learning Specification, whose original four pedagogy evidence fields were absent.
The P6UI.5A adapter exposed payloads without implementing an eligible constructor.

## Governed consumer and eligibility

The existing `GovernedPedagogyService` now accepts an explicitly configured
`evidence_service` and optional `approved_pack` on its eligibility and construction
methods. The default no-pack path retains the previous policy and serialized
qualification results. The same service still makes the eligibility decision.

`approved-pedagogical-evidence-consumer/1` authenticates the pack using the existing
HUMAN_REVIEW authority and immutable stored receipts, revalidates the proposal,
requires four APPROVE decisions, and checks exact pack/proposal/review/brief/
Learning Specification/source/tier bindings. SYNTHETIC_TEST_ONLY authority is not
accepted. No caller-supplied validation boolean can replace receipt authentication.

The consumer copies all four approved components without semantic changes and
records exact-copy mapping provenance. Its independent validator compares every
component and binding directly; it does not call the consumer constructor.

The versioned `approved-evidence-pedagogical-readiness/1` policy extends the existing
four mandatory requirements. It marks each AVAILABLE only after authenticated
consumption; none is removed or made optional. Standalone eligibility validation
rechecks authenticated input and pure policy, without invoking the consumer or
pedagogical constructor. Existing canonical/source prerequisites are still enforced.

## Construction and provenance

`governed-pedagogical-specification/1` is retained with an additive optional typed
`approved_evidence` field. This is needed because the original `activity_constraints`
field represents requirement statuses, not the actual criteria, checks and adapter.
The field stores the exact pack and checked projection, with all bindings. No new
required field is imposed on the previous schema's readers in this repository.
External strict consumers would need to accept this additive field.

The approved path records construction version
`governed-approved-pedagogical-construction/1`. Construction requires a current,
matching eligible decision and revalidates the resulting specification independently.
Input provenance distinguishes LEARNING_SPEC_DERIVED, APPROVED_PEDAGOGICAL_EVIDENCE,
DETERMINISTIC_POLICY and HUMAN_REVIEWED. Original model proposal provenance remains
PROPOSED/MODEL_PROPOSED inside the immutable evidence; its review receipt supplies
the separate approval. Nothing is relabeled as official source content.

Scope and goals come exactly from the Learning Specification; activity requirement
statuses and planning roles come from deterministic policy and approved evidence.
No teaching sequence, prerequisites, misconceptions, assessment bank, lesson text,
questions or explanations are fabricated. Spec governance remains qualification
evidence only, unpublished and not approved as a public lesson.

Every upstream warning remains, including historical missing-evidence warnings.
Those warnings describe the original Learning Specification and are not rewritten
when external approved evidence supplies a later requirement. The existing
NO_GENERIC_CALCULATION_MAPPING warning also remains. Twelve inherited warnings
therefore remain within thirteen specification warnings.

## Roles and independent authoring gate

The existing framing and optional non-assessing summary constraints remain.
The approved REPRESENTATION and CONCEPT_CHECK families become required planning
constraints with explicit approved-evidence provenance. Their concrete legacy role
lists are empty, authoring remains disabled, no SL role is selected, and no fixed
sequence is imposed. Broader concept/retrieval, numerical and assessment roles
remain unsupported for explicit evidence/mapping reasons.

The separate `approved-pedagogy-lesson-authoring-gate/1` reports the following
independently: spec validity, approved evidence binding, determined role families,
concrete mapping, content authoring contract, role validators and content provenance
constraints. `role-content-validation-requirements/1` defines outstanding
REPRESENTATION and CONCEPT_CHECK validation obligations; it does not claim an
implemented validator. Representation needs exact symbol scope, source/canonical
separation, observable representation and content provenance. Checks need
intention/criterion coverage, observable evidence, bounded assessment claims and
content provenance. Concrete role mapping, content DTOs and enforcement are still
missing. Lesson authoring therefore remains BLOCKED even for a valid constructed
pedagogical specification.

`persist_pedagogical_spec` stores deterministic semantic bytes by hash;
`read_constructed_spec` revalidates them and the live review authority on replay.
No runtime timestamps enter specification identity. The unchanged upstream pack
contains its already-recorded receipt metadata; identity is deterministic for the
same pack, learning input, consumer and construction versions.

## Trust and compatibility

Acceptance uses the real P6UI.5C pack read-only. It decrypts the existing credential
with Windows current-user DPAPI; it never provisions a replacement, resigns a
review or modifies a decision. The original Windows profile and credential must
remain available for authenticated replay. Network is denied during testing.
All historical outputs, review files, signatures, live proposals, credential bytes
and academic runtime state are compared with the initial inventory. Standard
Deviation runtime hashes and regression suites establish compatibility; no SD
migration occurs. No model/provider calls, trusted snapshot, canonical promotion,
database mutation, lesson content or publication occurs.

The remaining path to P6A.7 is a separately governed implementation of concrete
role mapping, content authoring contracts, role validators and content provenance
enforcement, followed by controlled qualification. This milestone does not bypass
those requirements.
