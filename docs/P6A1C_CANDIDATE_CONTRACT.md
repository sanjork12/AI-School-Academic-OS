# P6A.1c numeric representation contract

Candidate `ai-author-candidate/2` and brief `authoring-brief/2` replace the
experimental v1 representation. `first_term`, `second_term`, `mean`, and
`variance` now each contain `expression` and `value`, for example
`{"expression":"30/4", "value":"15/2"}`. There is no duplicate working list.

Expressions are bounded, boundary-screened, untrusted explanatory text. Equations
and alternative notation are allowed. Their mathematical meaning is not verified.
They are never parsed, evaluated, repaired, or passed to the production renderer.
Correct scalar values cannot certify an expression's explanation. The original
candidate audit retains both fields; the experimental package uses application
generated method steps and remains non-renderable and academically unapproved.

Values retain the existing ASCII integer/decimal/simple-rational grammar and
128-character bound. Proposed inputs remain new problem parameters. Solution
inputs must match them exactly. The existing Fraction/Decimal engine recomputes
all intermediates, radicand, numeric SD (finite decimal, tolerance 1e-40), and
two-decimal ROUND_HALF_UP display. No fixed number of digits is imposed.

The public validation booleans remain compatible. Read
`verification_summary.stage_status` to distinguish PASSED, FAILED and
NOT_EVALUATED. Encoding failures leave mathematics, solution and composition
unevaluated. `primary_failure` and `failures` provide safe error codes and field
names without rejected input values or exception strings. Qualification attempts
use null for unevaluated checks, so aggregate denominators remain meaningful.

Old candidate versions and old string intermediates are explicitly rejected as
`candidate_contract_version_unsupported`. No historical artifact is migrated.
The offline Gold contains manually specified fixtures for attempts 01/02,
incorrect values, equation-valued rejection and the old shape. The ten original
live candidates remain rejected and byte-for-byte unchanged.

## Engineering baseline v1.2

The operator explicitly authorized a new engineering baseline because changing
contract code necessarily changes files pinned by v1.1. v1 and v1.1 artifacts and
recorded hashes remain immutable. Historical verification reports
`historical_artifact_integrity`; it does not claim that current code conforms to
old source hashes. The explicit active descriptor selects v1.2, whose complete
inventory enforces current code conformance. Original v1.1 source bytes are not
reconstructed. Baselines are local engineering configuration, never academic
trust authority or production authentication. Source integrity, current review
state, revocation and snapshot validation continue through the live service.

## Offline verification

Run from the project root:

```
python -B -X utf8 -m unittest tests_p0.test_candidate_contract -v
python -B -X utf8 -m tests_p0.candidate_contract_acceptance
python -B -X utf8 -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --dry-run
```

The acceptance replay loads current trusted inputs, validates the historical
candidates without modifying them, and executes only synthetic fixture authors.
It refuses to overwrite an existing replay. Tests use temporary output directories.
There are no live calls, retries, repair paths or publication operations.

The supplied acceptance-artifact path ended at `output`; this implementation uses
`output/p6a1c_candidate_contract/`. Final test counts and protected-file comparison
are recorded in `acceptance.json` there.
