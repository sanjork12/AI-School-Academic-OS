# P4A deterministic authored teaching content

P4A consumes the current trusted Standard deviation read chain and adds
`authored-teaching-content/1`. Its status is `authored_candidate`. Neither
mathematical verification nor slot population is academic approval, publication,
pedagogical approval or completed-lesson readiness.

## Run

From `D:\AI-School-Academic-OS`:

```powershell
python -m academic_os.cli --db var/p0_q2.sqlite3 validate-pedagogy standard-deviation
python -m academic_os.cli --db var/p0_q2.sqlite3 author-teaching-content standard-deviation
python -m academic_os.cli --db var/p0_q2.sqlite3 author-teaching-content standard-deviation --json --output output/p4a_authored_teaching_content/standard_deviation.json
python -m unittest tests_p0.test_authored_teaching -v
```

To reproduce the saved test evidence and read-only acceptance report:

```powershell
python -X utf8 -m unittest tests_p0.test_authored_teaching -v *> output/p4a_authored_teaching_content/focused-tests.txt
python -X utf8 -m unittest discover -v *> output/p4a_authored_teaching_content/full-suite.txt
python -X utf8 -m tests_p0.authored_teaching_acceptance
```

Acceptance checks the saved pre-change baseline; it does not reset hashes or
repair the known missing legacy PPTX. The full-suite command therefore reports
that existing error even when P4A acceptance succeeds.

The default selection is the two protected Q2/Q3 snapshots; repeat `--snapshot`
to select snapshots explicitly. Every service call rechecks current snapshot
usability through P3C and P3B. The CLI does not open a write Store. Existing
output files may be reused only when their bytes match; a different existing
artifact is preserved and the command fails. Saved candidate JSON is not a
replacement for the live trusted read chain.

## Module boundaries

- `authored_models.py`: reusable candidate contract, controlled origins, stable
  links, separate questions/solutions, and slot population accounting.
- `authored_math.py`: small closed arithmetic expression interpreter, exact
  rational population statistics, deterministic square roots/display rounding,
  and recomputation of stored mathematical claims. No `eval`.
- `authored_verification.py`: recomputes formulas, visual claims and numerical
  answers, ignoring stored verification labels. This is a mathematical checker,
  not a full pedagogical/content validator.
- `authored_sd.py`: explicit topic-specific `standard-deviation-population/v1`
  authoring provider. Text and original examples are authored choices here,
  not inferred academic knowledge. It never loads an acceptance fixture.
- `authored_service.py`: current P3C authoring gate, consistent provenance
  between reads, provider dispatch and human-readable rendering.
- `tests_p0/fixtures/authored_standard_deviation_gold.json`: independently
  transcribed expectations from the human task, used only by acceptance tests.
  It is not a fabricated reviewer decision or a trusted academic record.

No upstream contract or artifact is changed. The new package references P3B
Teaching Blocks, four instructional slots and the same three P3A Learning
Requirements. It records SHA-256 hashes of the consumed P3B and P3C serialized
contracts; the separate provenance artifact carries the live upstream chain.

The pure provider expects validated internal upstream values. External API
callers must use the service boundary, not submit a self-asserted validation
report to the provider. There is no new authentication or review workflow.

## Content and alignment

Nine blocks provide a concept explanation, visual data/brief, calculation
method, summary-statistics method/input definitions, one worked example, two
practice questions, and conceptual/numerical learning checks. Every authored
object has an origin, constraint level, Teaching Block links and existing LR
links. Numerical questions additionally record reviewed evidence alignment,
capability and task form. They are original questions, not Pearson question
reproductions. Solutions are separate teacher-facing objects.

The conceptual check links to the conceptual Teaching Block. It does not
expand the frozen learning-check slot, whose existing scope is calculation
and summary-statistics application. Numerical practice and the calculation
check populate that slot. All four slots are
`content_supplied_pending_validation`; P3B remains unchanged with candidate
slots. No new Learning Requirements, prerequisites or canonical competencies
are created.

The two formulas are `instructional_formula`, with
`formula_memorisation_required=false`. All ten upstream evidence boundaries
are preserved. Population/sample comparison, prescribed calculator steps,
exam predictions, calibrated difficulty, frequency, typical marks, common
mistakes and additional required task forms are outside this authored slice.

## Mathematical verification boundary

Means and variances use exact `Fraction` arithmetic. Square roots use Decimal
precision 50. Stored decimal SDs must be finite and within absolute `1e-40`
of recomputation. Display values use exactly two decimal places and explicit
`ROUND_HALF_UP`, independent of locale. This is this package's display choice,
not a universal Edexcel requirement. Exact radical structure, decimal value,
display value and method steps are separate fields and checked independently.

Summary inputs require a positive integer n, finite rational sums, nonnegative
exact implied population variance, and zero variance for n=1. There is no
negative-variance tolerance because subtraction is rational/exact. These
checks do not establish feasibility under additional domain restrictions
(integer observations, nonnegative observations, bounded values, measurements,
etc.). No full constrained moment-problem solver is implemented.

Both formula ASTs are checked against an independent deviation-based variance
calculation on six deterministic datasets, including decimals, negatives,
singleton and constant data. These tests are arithmetic consistency checks,
not a symbolic proof for arbitrary future formulas. Only the closed supported
operations are executable.

Visual A/B claims recompute to means 10/10, variances 2/32 and SD(A)<SD(B).
Numerical questions recompute to:

- worked n=5, sum=50, squares=550: mean 10, variance 10, sqrt(10), display 3.16;
- practice n=10, sum=70, squares=530: mean 7, variance 4, sqrt(4), display 2.00;
- practice n=8, sum=96, squares=1200: mean 12, variance 6, sqrt(6), display 2.45;
- check n=20, sum=300, squares=4700: mean 15, variance 10, sqrt(10), display 3.16.

The conceptual answer stores expected meaning and semantic elements; it does
not implement student scoring or require exact answer-string matching.

## Future integration

An API should call `AuthoredTeachingService.read_topic(topic_key, snapshot_ids)`
and expose the typed view separately from audit provenance. A future content
validator should consume the authored package plus current P3B/P3C, recheck
their hashes/usability, call `verify_package_math`, validate semantic coverage
and content quality, and then decide renderer readiness. Never trust a saved
`verified` flag. Arbitrary prose semantics are not verified by P4A's math checks.

`ready_for_downstream_content_validation` means the generated candidate can be
submitted to that future validator. `ready_as_completed_teaching_content`
remains false. No lesson/PPT/DOCX renderer, model call or approval is added.

Read-only acceptance evidence is in `output/p4a_authored_teaching_content`:
baseline/focused/full test logs, before-state hashes, authored JSON, separate
provenance and acceptance report. The existing missing brainstorm PPTX remains
a reported legacy test error; neither its pinned hash nor its test is reset.
