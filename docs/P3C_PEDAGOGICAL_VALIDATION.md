# P3C — Pedagogical Contract Validator and Coverage Readiness

`pedagogical-validation/1` checks the current candidate contract without producing
teaching content, academic approval or quality scores. The expected current result
is structural coverage valid, LR 3/3 and CR 2/2 planned, reference integrity valid,
ten boundaries preserved and required slot structure valid. All four instructional
slots remain unpopulated. Content authoring may begin; completed teaching content
readiness is false.

## Service boundary and trust

`PedagogicalValidationService(database).read_topic(topic_key, snapshot_ids)` calls
the current Pedagogical and Learning services. The existing chain validates source
bytes and trusted snapshots before P2A/P2B/P3A/P3B construction. Both reads must
have identical upstream provenance. P3C never reads raw database objects, reparses
PDFs, or trusts a saved JSON file as permanent authority. Every call refreshes the
chain; withdrawal errors propagate. The result has `.view` and separate `.provenance`.

`validate_pedagogical_contract(candidate, learning)` is the pure diagnostic entry
for already validated upstream data and isolated synthetic mutations. It does not
authenticate JSON. It returns structured findings rather than stopping at the first
broken reference. A malformed/unavailable upstream Learning Specification is rejected.
No upstream schema, source, Gold Standard, decision or saved upstream output changes.

## Coverage semantics and the missing-block case

The matrix reports every upstream LR and CR by stable ref. Each row includes all
referencing block refs, its required primary role, and `covered`/`uncovered`.
Coverage is a structural design obligation, never a claim that learning is taught
sufficiently or that students have mastered it.

The task-form LR currently has three references: its dedicated application block,
worked connection and practice. Removing the application block does **not** remove
the latter two references. To implement P3C's required-role rule and negative case A
without changing P3B, the validator retains those two references in the report but
marks the LR `uncovered` when its required `supported_task_form` role is absent.
The same policy uses LR/CR types for conceptual meaning, method, worked connection
and practice/check. No title or label matching is used.

This is stronger than simple nonzero-edge counting. It expresses that worked/practice
references cannot replace a separately required instructional function. Slot and
authoring readiness also fail when that role is missing.

## Reference and slot checks

Checks cover unique block/content identities, collisions with Product or upstream
refs, correct LR/CR/evidence/boundary/content kinds, declared versus actual coverage
maps, instructional Product/evidence alignment, and learning-check assessment refs.
Duplicate display titles are allowed. Unknown or wrong-kind refs produce ERROR.

Each required function must have a required constraint. Method, task application,
worked connection and practice/check must link the corresponding slot type. Slots
must support their owning block's LRs and contain a nonempty specification instruction.
A learning-check slot must declare its assessment targets.

The frozen P3B model compares boundary tuple order directly. P3C normalizes unordered
collections in a validation copy before invoking that model; it neither modifies the
caller input nor repairs the saved upstream artifact. Findings and matrix order are
deterministic, including reversed input collections.

## Boundaries and limitations

The embedded source-learning projection is compared against current upstream meaning
and compact evidence. All ten outer evidence boundaries must match exactly. Structured
formula-memorisation flags and unsupported Product/task refs are checked explicitly.

Deterministic lexical rules detect explicit overclaims about formula memorisation,
required calculator methods, difficulty, common mistakes, prerequisites, academically
mandatory teaching sequence, frequency, typical marks, exam prediction and additional
task forms. They scan pedagogical purposes/titles/constraints and generator constraints,
not the inherited negative boundary statements. Contrast clauses are separated so a
negative introductory clause does not suppress an affirmative overclaim after “but”.

Instructional support without required memorisation, a flexible calculator demonstration,
recommended guided-to-independent practice, and bounded reviewed-example mark observations
are allowed. These rules are **bounded text checks**, not an NLP proof of every possible
paraphrase, language or disguised claim. The report contains a warning explaining that
limit. P3C does not certify arbitrary authored text or pedagogical quality; future authored
content still needs its own content-level validation/review.

## Readiness dimensions

`ready_for_content_authoring` requires no blocking ERROR: structural requirements,
references, boundaries, schema and required slots must be valid. Warnings about missing
content do not prevent authoring.

The frozen `candidate_slot` schema has a purpose/instruction but no authored-content
field or completed-content validation receipt. Therefore purposes such as “Provide a
valid calculation method” never count as populated methods. All four current slots,
including task inputs, are unpopulated. Changing a status to `populated` or adding an
unsupported content field cannot bypass the frozen schema.

`content_readiness.ready` and `ready_as_completed_teaching_content` remain false in
this version. A future populated authoring contract and content-level checks are needed;
P3C does not silently extend the frozen P3B schema. No final pedagogical quality score,
lesson validation, question generation or scoring is implemented.

## Run

From `D:\AI-School-Academic-OS`:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 validate-pedagogy standard-deviation
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 validate-pedagogy standard-deviation --json
python -X utf8 -m unittest tests_p0.test_pedagogical_validation -v
python -X utf8 -m unittest discover -v *> output/p3c_pedagogical_validation/full-suite.txt
python -X utf8 -m tests_p0.pedagogical_validation_acceptance
```

The protected Q2/Q3 snapshots are defaults; `--snapshot` can be repeated. `--output`
retains the existing no-overwrite guard. CLI exit 0 means safe for content authoring,
not completed teaching content; exit 2 indicates a diagnostic authoring block, and
upstream read errors retain the existing error exit behavior.

Artifacts under `output/p3c_pedagogical_validation/` include normal report JSON,
separate provenance, acceptance report, before-state and test logs. Normal reports
use Product/Learning/Pedagogical refs, not canonical IDs. Provenance retains the
validation → block → LR → Product → canonical → snapshot chain.

Negative tests mutate in-memory copies only. Acceptance records database hashes,
table digests, counts, frozen upstream/Gold Standard hashes, snapshot usability,
determinism and full-suite results. The existing missing
`AI_Academic_Operating_System_Brainstorm_CN.pptx` protected-file error is retained,
with no skipped/weakened test or changed pinned hash. No APIs, model calls, .env,
web search or new approval/governance system is involved.
