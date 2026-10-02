# P5B — Reuse-first profiled content authoring

P5B adds `profiled-authored-teaching-content/1`. It reads the current live P5A,
P4A and P4B service chains, compares their upstream provenance, validates the
profile against current learning/base pedagogy, and reruns P4B content validation
before making any reuse or authoring decision. Saved JSON flags are not credentials.

## Implementation

- `academic_os/profiled_content_models.py`: separate question/content objects,
  solutions, reused references with version hashes, role decisions and candidate
  package status. No upstream schema changes.
- `academic_os/profiled_content.py`: generic compatibility, reuse allocation,
  remaining-item analysis, unresolved handling and P5B integrity verification.
- `academic_os/profiled_sd_provider.py`: explicit Standard deviation numerical
  cases and original prompts. It imports the existing P4A mathematical engine;
  it is not generic AI inference and never reads test Gold fixtures.
- `academic_os/profiled_content_service.py`: fresh read-only service boundary and
  immutable/idempotent export.
- `academic_os/cli.py`: additive command before the writable Store branch.

Compatibility uses LR coverage/assessment, semantic role, content type, task form,
base lineage, full boundary content and current P4B validation. Display titles do
not drive identity or selection. Evidence boundaries are compared by stable ref
and complete value, not serialization order. Distinct density instances within a
profile consume distinct content objects; sharing the same verified object across
profiles remains allowed.

## Current result

Focused Review: 9 substantive roles, 9 reuse decisions, no new or unresolved
content. Standard Lesson: 14 substantive roles plus orientation framing, with
7 reuse and 7 author-new decisions. Its independent-practice set reuses both
original practice blocks and adds one new question; it is one role-level
`author_new` decision with explicit reused and new item references.

Reused blocks are not cloned. Their reference, content digest, question/formula/
solution dependency hashes, source package digest and current P4B digest are
retained. New identities are provider/content identities, not profile names or
role-instance IDs. Both packages preserve the same academic scope fingerprint,
LR/coverage refs and evidence/content boundaries.

Seven new objects are provided: early conceptual retrieval, raw-data mini worked
example, second full worked example, two guided practices, independent-practice
extension and two-part exit check. The exit question declares separate conceptual
and calculation LR targets; closure references existing LRs. Orientation creates
no authored academic object.

The raw mini example is explicitly an instructional demonstration of the general
calculation capability, with no supported assessed task-form reference. Guided
and independent are support modes, not difficulty or learner classifications.
Questions/scaffolds and teacher solutions/expected meanings are separate objects.
No student natural-language grading is implemented.

## Mathematical verification

All six new numerical examples use existing `summary_stats`, `raw_stats`,
`verify_solution`, exact rational arithmetic and display rounding. The raw adapter
forms summary inputs and checks deviations/squared deviations against the original
observations; it does not implement another SD engine. The stored result is never
trusted: package verification recomputes answers and compares deterministic
content/lineage to the bounded provider. The concept item's checks are response
separation/integrity checks, not mathematical or NLP grading.

Synthetic tests corrupt each of the six numeric answers and each displayed
rounding, plus means, variances, exact representations, raw deviations, prompts,
source hashes and self-declared verification data. Non-finite and infeasible
inputs fail verification.

## Unresolved and readiness

An unavailable/unsupported provider, incompatible alignment or failed new-content
verification produces `unresolved` with a reason and retained safe partial reuse.
An unresolved package can be a valid safety result while remaining incomplete.
Minimum and target counts are separate. For example, two reused practice items
meet SL-12's minimum, but an unavailable extension leaves its target unmet and
its role unresolved. No missing item is fabricated.

The real deterministic packages meet both counts and are ready for P5C input.
They remain `candidate_pending_p5c`, with `ready_for_rendering=false`. P5B integrity
and mathematical checks do not replace P5C's future profiled content validation,
academic approval, publication or a presentation renderer.

## Reproduce

```powershell
python -m academic_os --db var/p0_q2.sqlite3 author-profiled-content standard-deviation --output-dir output/p5b_profiled_authoring
python -m unittest tests_p0.test_profiled_content tests_p0.test_lesson_profiles tests_p0.test_authored_teaching tests_p0.test_content_validation -v
python -m tests_p0.profiled_content_acceptance
```

Protected Q2/Q3 snapshots are the defaults. Repeatable `--snapshot` overrides are
available. Without an output directory the command prints both packages. Existing
different exports are refused rather than overwritten.

`output/p5b_profiled_authoring` contains both packages, integrity verification,
provenance, role-by-role decisions, baseline/final test logs and acceptance evidence.
Initial development outputs/logs are retained separately from the final exports.
No trusted database, source, decision, snapshot, existing Gold Standard or frozen
P2–P5A/P4C artifact is changed. No model/API calls or PPT generation occur.

Baseline: 145 existing relevant tests passed. Final targeted regression includes
45 new P5B tests and those same 145 tests. The entire repository suite was not
rerun; see `final-tests.txt` and `acceptance.json` for this run's actual results.

P5C should resolve reused objects through current validated source services,
check all binding hashes and profiled role/item coverage, validate support and
question/solution visibility, then decide downstream eligibility. It must not
interpret `content_complete` alone as permission to render or publish.
