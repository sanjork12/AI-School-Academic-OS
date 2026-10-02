# P6A.1d offline candidate replay qualification

This experiment uses only the ten saved candidates from
`run-3ce33e8d738f42df96182e5ca5409dd9`. No provider, regeneration, retry,
publication, or production-code change is involved. v1.2 remains the active
engineering baseline; neither v1.1 nor v1.2 is rewritten.

## Evidence and method

All ten original candidates put equations into four scalar fields. The original
saved validation rejects every candidate; the unchanged ASCII scalar guard also
rejects every one of these forty strings. The current validator explicitly rejects
their old candidate version. Original audit, raw response, attempt, observation,
validation and timestamp evidence stays untouched.

P6A.1c introduced expression/value pairs. The offline transcription JSON lists
the four scalar claims explicitly for each inspected attempt, pinned to the
original audit's SHA-256. The replay helper has no equation parser, RHS extraction,
arithmetic repair, or fallback. It copies the complete original calculation text
into `expression` and inserts only the manually transcribed value. It refuses a
source-hash or inspected-text mismatch. Mathematical recomputation occurs only
in verification/evidence reporting, never to construct or correct a fixture.

Inputs, radicand, numeric answer, display answer, question and scaffold text are
copied unchanged from the historical candidate. No field is silently dropped.
The historical candidate ID and model metadata remain provenance; they do not
describe a new provider call. Each fixture records every changed application
binding: schema version, current brief identity/hash and current input/scope
binding. This explicit test rebinding is necessary because the brief changed; it
does not claim that the historical model produced a v2-bound response.

The original response JSON is checked against the recorded candidate content.
The complete intermediate text, including additional equality steps, is retained
in expression/provenance. Fixture and original hashes, field mappings and full
validation reports are available per attempt in the output directory.

## Observed replay result

Attempts 01–10 each produced REPLAY_ACCEPTED: 10 accepted, 0 rejected,
0 inconclusive. All ten pass schema, binding, scope, boundary, encoding,
input mathematics, solution verification and composition checks.

Attempts 01, 06 and 07 retain mean 3, variance 2 and display 1.41.
Attempts 02, 03, 04, 05 and 10 retain mean 5/2, variance 5/4 and display 1.12.
Attempt 08 retains mean 13/2, variance 33/4 and display 2.87.
Attempt 09 retains mean 9/2, variance 21/4 and display 2.29.
The preserved numeric decimals all satisfy the existing 1e-40 tolerance.
The report records recomputed first/second terms, mean, variance, SD, absolute
numeric error and the existing verifier's individual check results.

Fourteen isolated controls cover four forbidden scalar strings, wrong first
term, variance, numeric answer, display, input binding and radicand; a valid
equivalent rational; and three expression variants. The ten negative controls
are rejected; the four positive controls pass. A separate test injects an
unready composition gate to verify the composition failure diagnostic.

## Diagnostic interpretation

The acceptance-only diagnostic adapter preserves original validator codes and
maps their safe fields to input_binding_invalid, numeric_answer_invalid,
display_answer_invalid and exact_radicand_invalid. It changes no production
behavior. Encoding and mathematical-value errors retain their existing codes;
composition_invalid remains distinct.

An encoding error leaves math_valid, solution_valid and composition_valid
NOT_EVALUATED. For a wrong intermediate, math_valid can be PASSED because this
flag denotes input feasibility; solution_valid is FAILED with
mathematical_value_invalid, and composition_valid is NOT_EVALUATED. Therefore a
math_valid boolean alone must never be described as a correct candidate solution.

`30/4 = 999` paired with the correct scalar `15/2` passes the current candidate
gate: expression semantics are deliberately not verified. This is an observed
limitation, not an endorsed explanation. Expressions cannot override numeric
values, and accepted replay content is neither academically approved nor
renderer-ready.

## Integrity and reproduction

The experiment records hashes and last-write timestamps of all existing project
source, tests, documentation, output and database files before replay. Final
acceptance rechecks them, along with database table digests, review/governance
counts, current trusted reads of both protected snapshots, and v1.1/v1.2 baseline
verification. It does not reset timestamps, rewrite old records or republish.

Run from the project root:

```
python -B -X utf8 -m unittest tests_p0.test_offline_candidate_replay -v
python -B -X utf8 -m unittest tests_p0.test_candidate_contract tests_p0.test_ai_authoring tests_p0.test_ai_qualification tests_p0.test_content_validation tests_p0.test_profiled_validation -v
python -B -X utf8 -m unittest discover -v
```

The acceptance helper is `tests_p0.offline_candidate_replay`; its already-created
output is intentionally exclusive and it refuses overwrites. Reproduce behavior
through the tests, which do not overwrite acceptance evidence. Final test counts
and the unchanged historical missing-PPTX error are in
`output/p6a1d_offline_replay/acceptance.json`.

## What this establishes

For these ten saved responses, preserving their stated mathematics while
explicitly representing it under v2 removes the representation rejection.
Incorrect scalar/input/final-answer controls still fail. This supports the
contract-mismatch explanation for this run; it is not a measured live v2 model
acceptance rate. Repeated datasets in the run also limit diversity evidence.

Replay does not prove future model compliance, correct instructional expression
semantics, pedagogy, originality, production authentication or render readiness.
The next milestone may be an explicitly authorized P6A.2 live qualification
against the unchanged v2 brief with a separate budget and immutable new run.
This task does not start it. Expression-semantic review remains a separate
requirement before any production renderer integration.
