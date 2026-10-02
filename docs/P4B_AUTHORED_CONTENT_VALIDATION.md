# P4B authored-content validation and renderer gate

P4B adds `authored-content-validation/1`. It validates the current P4A candidate
against current P3A/P3B and a freshly recomputed P3C report. It does not author
content, render slides, publish academic data, score teaching quality, grade
students or assert mastery.

## Reproduce

From `D:\AI-School-Academic-OS`:

```powershell
python -m academic_os.cli --db var/p0_q2.sqlite3 validate-authored-content standard-deviation
python -m academic_os.cli --db var/p0_q2.sqlite3 validate-authored-content standard-deviation --json --output output/p4b_authored_content_validation/standard_deviation.json
python -X utf8 -m unittest tests_p0.test_content_validation -v
```

The CLI returns 0 when ready for rendering, 2 for a completed validation report
with blocking findings, and 1 for a failed live read or other operational error.
Existing output files are never replaced with differing content. Repeat
`--snapshot` to select snapshots; defaults remain the protected Q2/Q3 pair.
No write Store is opened by the command.

To reproduce full acceptance evidence:

```powershell
python -X utf8 -m unittest tests_p0.test_content_validation -v *> output/p4b_authored_content_validation/focused-tests.txt
python -X utf8 -m unittest discover -v *> output/p4b_authored_content_validation/full-suite.txt
python -X utf8 -m tests_p0.content_validation_acceptance
```

Acceptance compares the saved pre-change state; it does not reset source pins,
review decisions, fixtures or hashes. The known missing legacy brainstorm PPTX
remains an error in the full suite, reported separately from P4B results.

## Modules and trust boundary

- `content_validation_models.py`: report schema, separate dimensions, findings,
  coverage evidence, slot evidence and renderer readiness.
- `content_validation.py`: pure validation of isolated inputs, reference
  registries, actual-content checks, coverage and reuse of P4A mathematics.
- `content_validation_rules.py`: explicit bounded Standard deviation language
  rules. This is a v1 topic profile, not general semantic inference.
- `content_validation_service.py`: current trusted read chain, provenance
  consistency checks, validation and operator-readable output.
- `tests_p0/test_content_validation.py`: isolated adversarial fixtures and
  read-only live integration tests.

The service reconstructs authored content through the existing P4A service,
which rechecks trusted snapshots and P3C. P4B separately reads current P3B/P3A,
checks the provenance chains agree and recomputes P3C before assessing renderer
readiness. A revoked/unusable source or snapshot blocks the read. A change
between independent reads produces an explicit retry error.

Saved JSON is an artifact, never a permanent trust authority. The pure function
does not authenticate caller-supplied JSON. Tests label such inputs as isolated
synthetic copies; production callers must use `AuthoredContentValidationService`.

All upstream contracts, P4A modules and outputs, source files, review records,
snapshots and Gold Standards remain unchanged. No model, external API, `.env`,
embedding, UI or document renderer is used.

## Actual content and coverage

Reference validation uses current upstream entities, not lists asserted inside
the candidate. It checks identity collisions, wrong-kind and unknown refs,
Teaching Block/slot ownership, LR targets, task/capability/evidence alignment,
question/block relationships and separate unambiguous solutions.

The actual four frozen slots are calculation method, summary-statistics inputs,
worked example, and learning check. The visual comparison belongs to the
conceptual Teaching Block, not to a separate visual slot. Population is derived
from valid content of the right kind with valid links and recomputed mathematics;
the saved P4A coverage/verification declarations are not evidence of completion.

Method content must contain the calculation actions in order and reference a
verified formula with the correct learning target. Summary-statistics support
must define n, sum of observations, and sum of squared observations correctly.
A worked example or numerical learning check needs a concrete question, supported
task form, learning targets, reviewed evidence alignment, a separate solution
and passing mathematics. Titles or authoring instructions alone cannot qualify.

The coverage matrix lists actual supporting authored refs for each of the three
Learning Requirements and both Coverage Requirements. Required conceptual,
method and task-input teaching functions remain required. The worked-example
and learning-check slots enforce the required application/assessment connection.
Recommendations and flexible choices do not become new hard requirements:
missing recommended visual support produces a warning; optional extra practice
or a conceptual check may be absent. Every supplied object is still checked,
including optional objects. Invalid optional content cannot bypass the gate.

## Mathematics and prose limitations

P4B invokes the unchanged P4A `verify_formula`, `verify_visual` and
`verify_solution` primitives, collecting reports even when other objects fail.
It does not create a second arithmetic engine. Stored `verified` fields are
ignored. Exact radicals, numeric values, displays, method steps, question data,
visual data/claims and formula ASTs are rechecked.

The inherited mathematical boundary is exact rational means/variances, positive
integer n, finite inputs, nonnegative implied variance and singleton consistency;
Decimal precision 50 for square roots and absolute `1e-40` numeric comparison;
`ROUND_HALF_UP` to two decimals for this package's displays. This is not an
Edexcel-wide rule or a constrained moment-problem solver. Formula equivalence
checks use deterministic datasets, not an arbitrary symbolic proof.

Frozen P4A concept explanation blocks have no structured semantic-element field.
P4B therefore uses bounded phrase/negation rules for spread/dispersion, relation
to the mean and observation units, together with current upstream LR and block
roles. Conceptual solutions already contain `key_semantic_elements`; both these
elements and the actual expected meaning are checked. Supported paraphrases can
pass without exact prose equality. This does not implement student answer grading.

Boundary rules inspect actual block text, questions, solution steps, expected
meaning, input definitions, visual briefs and formula display text. They flag
explicit memorisation mandates, required calculator methods, calibrated
difficulty, common-mistake/prerequisite claims, frequency, typical marks,
predictions, population/sample lessons and unsupported required task forms.
Direct negation is scoped locally; an unrelated negative clause cannot suppress
a later positive requirement. Unrecognised phrasing can require review; these
rules are not an arbitrary-language semantic proof or pedagogical quality model.

Origin/provenance checks reject unsupported copying metadata and explicit claims
that generated questions are Pearson/Edexcel source questions. They do not
perform full textual copyright similarity detection. Warnings retain these
limitations in the machine-readable report.

## Renderer handoff

Call `AuthoredContentValidationService(database).read_topic(topic, snapshot_ids)`.
Only `renderer_readiness.ready_for_rendering` represents this gate's result;
all blocking findings are ERRORs. WARNINGs explain nonblocking limitations.
Schema-invalid inputs fail closed, even when some mathematical subchecks pass.

`input_contracts` binds the report to SHA-256 hashes of the canonical serialized
P4A, P3B, freshly recomputed P3C and P3A inputs. Canonical serialization uses
UTF-8, sorted JSON keys, two-space indentation, unescaped Unicode and a trailing
newline, matching the existing contract serializers. The separate provenance
artifact records the live upstream trust chain.

A future renderer must obtain a current successful service result, check that
the supplied candidate matches the report's P4A hash, and only then render that
candidate. A report must not authorize a changed candidate or remain a trust
token after upstream withdrawal. This implementation returns diagnostics and
eligibility only; it creates no PPT/lesson artifact or trusted snapshot.
