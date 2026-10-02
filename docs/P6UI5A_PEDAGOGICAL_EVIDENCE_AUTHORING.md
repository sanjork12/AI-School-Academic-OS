# P6UI.5A — governed pedagogy evidence authoring

P6UI.5 found four missing requirements: success criteria (REVIEW_REQUIRED),
activity scope and check alignment (MISSING), and pedagogical adapter
(AUTHORING_REQUIRED). Its lesson gate additionally requires an executable role
contract and role-specific content validators. Inspection was saved before
implementation in `output/p6ui5a_pedagogical_evidence/inspection.json`.

## Bounded contracts

`academic_os.pedagogy_evidence.PedagogicalEvidenceService` provides the service
workflow. Policy `bounded-symbol-evidence-authoring/1` supports only
EDX-4MA1-F-2.8-A. Unsupported targets fail closed. This is intentionally a small
first authoring vocabulary, not a universal education adapter.

The `pedagogical-evidence-authoring-brief/1` embeds the independently validated
Learning Specification, its content hash, selected target/document hash/tier,
exact source wording, distinct historical canonical semantics, learning intention,
all warnings, authoring constraints, prohibitions and review requirements. These
nested typed upstream fields are authoritative; there is no second editable
copy of canonical wording masquerading as source wording. The source's unclear
glyphs remain unchanged. Brief serialization and hash are deterministic.

`pedagogical-evidence-proposal/1` remains PROPOSED. Every proposed component has
explicit PROPOSED provenance, origin, brief hash, source and intention references.
Origins distinguish synthetic, human-authored and future model proposals; none
confers approval. Source and canonical evidence remains separately typed in the
brief. Upstream warnings are inherited intact; validation cannot remove them.

Success criteria specify observable INTERPRET_SYMBOL or SELECT_SYMBOL action,
reviewed-symbol-only scope, presentation condition, completion rule, intention
and evidence basis. Vague understanding claims and arbitrary curriculum prose
are not accepted. These are proposed observable criteria, not new official
curriculum claims or a claim of complete learning coverage.

Activities constrain REPRESENTATION or CONCEPT_CHECK, referenced criteria and
response mode. Checks bind intention → criterion → activity → observable evidence
form, disallowing completion without a response. No lesson text, student question,
answer, worked example, timing or forced sequence field exists.

`pedagogical-adapter/1` preserves exact canonical ID/action, references all proposed
criteria/activities/checks, and recommends a small family set. ORIENTATION derives
its category reference from SL-01; REPRESENTATION from SL-03; CONCEPT_CHECK from
SL-13; SUMMARY refers only to the non-assessing portion identified by P6UI.5 for
SL-15. These are repository category references, not evidence that SD content or
an SD role is suitable for Topic 2. Method, calculation, numerical practice and
worked-example families are unsupported in this bounded version. No SL role is
activated and no 15-role lesson is imposed. The positive fixture proposes two
families. Suitability still needs human judgment.

## Validation and review workflow

1. Build a brief with `build_pedagogical_authoring_brief(learning_spec)`.
2. Author a Proposal externally using the typed schema; validate using
   `validate_pedagogical_proposal(proposal, brief)`.
3. `present_for_review(proposal)` stores immutable proposal bytes and returns the
   full proposal, hash, components and upstream warnings for a reviewer.
4. A trusted human-review caller produces `pedagogical-evidence-review/1` with
   exact proposal hash, ordered decisions for all four components, reviewer ID,
   rationale, policy, purpose and domain. Each decision is APPROVE, REJECT, REVISE
   or DEFER. Adapter review includes its role-family constraints.
5. `record_pedagogical_review(proposal, decision, reviewer_signature=...)` verifies
   an HMAC-SHA256 signature using deployment-provisioned reviewer credentials.
   There are no default human keys, and proposal data cannot provision keys.
   The trusted review caller signs canonical `serial(review)` bytes with its
   reviewer key (at least 32 bytes). Do not expose keys or this signing operation
   to a model or unauthenticated API. Configure the same keys on service restart
   for replay; key removal revokes validation of its historical receipts.
6. `build_approved_pedagogical_evidence_pack(proposal, receipt)` requires all four
   explicit approvals, authenticated exact-hash review and a matching immutable
   stored receipt. No request-supplied boolean or validation report is trusted.
7. `validate_pedagogical_evidence_pack`, `persist_evidence_pack`, and
   `read_evidence_pack` revalidate source bindings, content, review and identity.

The review semantic hash excludes timestamp/signature metadata. Evidence identity
binds proposal hash plus semantic review hash. Receipt timestamp remains immutable
in its service-owned store. HMAC proves a configured review channel, not human
identity or pedagogical truth. Deployment must authenticate human reviewers and
protect both keys and receipt-store write access; this milestone supplies a
service boundary, not an authentication UI. Local administrators remain trusted.

Synthetic tests use a separate temporary store and SYNTHETIC_TEST_ONLY domain.
Synthetic proposals cannot receive HUMAN_REVIEW approval. No real reviewer key,
real approval or production approved pack is created by this milestone. Model
and provider calls are zero; network is denied during tests/acceptance.

## Integration and remaining work

`consume_approved_evidence` independently validates the approved pack and current
Learning Specification, and supplies the four typed requirement payloads next to
the unchanged P6UI.5 eligibility result. This is a consumption adapter for future
construction, not a new eligibility policy. P6UI.5 policy and construction are
unchanged; real eligibility remains REVIEW_REQUIRED and lesson authoring BLOCKED.
No actual pedagogical specification or lesson is constructed. A future constructor
and role-specific validators must consume these inputs under a separately reviewed
policy before eligibility can advance. Approval here means only permission for
governed pedagogical construction, never curriculum/canonical truth, publication,
public lesson approval or a trusted snapshot.

Future models may propose criteria, activity constraints, check alignment, bounded
adapters and role families within this schema. They may not change source text,
claim human/canonical approval, sign reviews, publish, write trusted state or skip
validation. Live qualification/P6A.7 still needs an authorized provider run, a real
bounded proposal, independently validated evidence, authenticated human review,
and executable construction/content validators. No such run is performed here.

Standard Deviation P3A–P6 is unchanged. The comparison artifact records conceptual
contract correspondences only; there is no migration. The pre-existing ingestion
test drift consists of two explicit UTF-8 file reads, retained and tested as part
of v1.13. All v1.12 historical artifacts and its manifest remain byte-identical.
