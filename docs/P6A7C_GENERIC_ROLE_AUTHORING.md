# P6A.7C — generic symbolic role authoring

The validated P6UI.5D specification supplies approved REPRESENTATION and
CONCEPT_CHECK role families. This milestone implements bounded authoring for
those families, preserving the authenticated source/learning/pedagogy/pack/review
chain. It does not generate a complete lesson, slides or an exam bank.

## Relationship to numerical authoring

Inspection of SL-10, SL-11, the numerical core, candidate models, provenance,
composition and offline qualification is saved before implementation. The new
module reuses governance mechanisms: deterministic binding, closed schemas,
independent validation, teacher/student separation, validation before composition,
content hashes and replay. It does not import numerical candidate/2, statistical
inputs, expression evaluation, operand lineage, SD formula hints, scaffold text,
SL identities or Standard Lesson routing. Historical numerical files stay intact.

## Inputs, mapping and brief

`academic_os.generic_role_authoring.brief.build_brief(spec, family, pedagogy_service)`
requires a currently valid authenticated pedagogical specification. The current
mapping is deliberately limited to EDX-4MA1-F-2.8-A / Foundation and the exact
reviewed CAN-ALG-INEQ-SYMBOLS meaning. It never interprets the corrupted PDF glyphs.

`bounded-symbol-role-mapping/1` creates identities of the form
`generic-<family>-<SHA256>`. The digest includes source, tier, full pedagogy hash,
candidate contract and mapping version; each identity distinguishes all of them.
No SL mapping is introduced. This is an application-owned mapping policy released
with the engineering baseline, not a new human academic approval.

`generic-role-authoring-brief/1` contains the exact validated specification and
explicit projections of source wording, canonical meaning, intention, approved
criteria/activities/checks, inherited warnings, allowed modes, prohibitions and
all input hashes. The candidate output schema is in binding.contract_version;
validation and semantic policy versions are explicit. The independent brief
validator checks each projection without calling the brief builder.

The actual approved ACT-1/SC-1/CHK-1 supports symbol interpretation for
REPRESENTATION. ACT-2/SC-2/CHK-2 supports symbol selection for CONCEPT_CHECK.
Briefs contain only their respective approved relationships. A mathematically
correct item bound to the other criterion is rejected.

## Separate candidate contracts

`representation-role-candidate/1` has one fixed instruction, one approved symbol,
SYMBOL_INTERPRETATION response mode and a teacher-side expected meaning. It is a
small representation/interpretation task, not explanation prose.

`concept-check-role-candidate/1` has one fixed instruction, a stated semantic
relation, two to four choices from the four-symbol vocabulary, SYMBOL_SELECTION
response mode and a teacher-side expected symbol. It is lesson-role content only.
It has no exam metadata, numeric inputs, difficulty claims or assessment-bank API.

Both bind role identity, source/tier, pedagogy hash, learning hash, pack identity/
hash, proposal/review hashes, brief hash and exact intention/criterion/activity/
check. Extra fields are forbidden. Closed instruction and symbol/meaning enums
exclude solving, number-line methods, regions, compound/quadratic inequalities,
algebraic manipulation and arbitrary prose. This first vocabulary does not cover
every future conceptual role or free-response task.

## Independent mathematical validation

`generic-symbolic-role-validation/1` enforces a deterministic semantic bijection:
greater-than, less-than, greater-than-or-equal-to and less-than-or-equal-to. It
checks the relation, not merely whether a symbol appears. Strict and inclusive
relations cannot substitute for each other. Concept checks require unique choices
and exactly one matching expected symbol. A correct response, exact alignment and
an observable response mode are all necessary.

The semantic table is application-owned deterministic interpretation of the exact
reviewed canonical meaning; it never rewrites or repairs official source wording.
Every validation rechecks current upstream evidence and authenticated review.
No constructor is invoked by candidate validation. Pydantic schema defaults are
canonicalized for semantic hashing; input content is never repaired.

## Provenance and composition

Brief fields distinguish GOVERNED_SOURCE_CONTEXT from
APPROVED_PEDAGOGICAL_CONSTRAINT. Each content field, including the entire choices
collection, carries its declared origin. Future model candidates use
MODEL_AUTHORED_CONTENT; all six present fixtures use OFFLINE_FIXTURE_CONTENT.
Validation carries DETERMINISTIC_VALIDATION. A claimed HUMAN_REVIEWED or source
origin for authored content is forbidden. Pedagogy approval is not content approval.

`compose(candidate, brief, pedagogy_service, validation=optional_report)` always
validates again. If an earlier report is supplied it must match exactly, so even
a valid changed candidate cannot reuse an old result. Output is
`authored-generic-role-content/1`, with composition version
`bounded-symbol-role-composition/1`. It preserves the candidate, input bindings,
candidate hash, validation hash and lineage. Student-visible data excludes expected
answers; teacher validation is a separate sidecar. A deterministic token-to-label
mapping supplies readable meanings. No slide rendering or lesson attachment occurs.

`validate_composition` independently checks lineage, exact content projection and
student/teacher separation without calling compose. Repeated validation and
composition produce identical semantic hashes; no runtime timestamps are embedded.

## Eligibility and remaining boundary

The existing P6UI.5D authoring gate now recognizes these contracts, validators,
provenance enforcement, composition and generic role mappings. Role-level status
is ELIGIBLE_WITH_WARNINGS: eligible for bounded authoring under this contract,
not qualified live output, rendering readiness or pedagogical approval.

The full lesson remains BLOCKED because scope_framing is also a governed required
role and has no authored-role contract here. Optional non-assessing summary does
not become mandatory. Eligibility checks every required role, so implementing two
families cannot silently enable a full lesson.

Six positive fixtures and at least twenty-five negative fixtures cover semantic,
binding, provenance and scope failures. Additional tests cover stale validation,
composition tampering, altered source/canonical projections, authority absence,
and two offline replays. No model/provider call is made. Existing SD/P6A suites
and immutable source/artifact hashes establish historical compatibility.

Live qualification remains a separate authorized task: fixed governed briefs,
controlled provider calls, raw-response evidence, independent validation and
human evaluation. Full lesson assembly additionally requires the other mandatory
role contracts. Authenticated upstream replay still needs the original Windows
DPAPI credential context; this milestone neither modifies nor reprovisions it.
