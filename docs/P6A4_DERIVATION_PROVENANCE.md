# P6A.4 bounded derivation / operand provenance

P6A.4 checks explicit mathematical source identities and operation structure for
SL-10's four existing intermediate expression fields. Candidate payload remains
`ai-author-candidate/2`; P6A.3 parser/evaluator `sl10-expression/1` is unchanged.

## Policy and entry points

Verifier: `sl10-derivation-provenance/1`.
New acceptance/generation policy: `sl10-provenance-required/1`.
New brief: `authoring-brief/3`, identity
`standard-deviation-standard-lesson-SL-10/3`.

Both authoring and qualification CLIs select the new policy in application code.
No provider can select it, downgrade it, or inject policy fields into content.
The Python APIs `compile_brief`, `run_once`, `validate_candidate`, `compose`, and
qualification `execute` now default to `sl10-provenance-required/1`. Omitting
`policy` cannot select legacy acceptance. Compatibility workflows must explicitly
pass `policy=LEGACY_POLICY`. They remain labelled legacy and never claim provenance.
This closure hardening corrects the initial P6A.4b implicit legacy default; the
original acceptance and v1.5 manifest remain immutable pre-closure evidence.
The active v1.5 closure manifest records the exact amendment and original hash.
Closure also corrects the validation result's brief reference to the selected
brief: v3 for strict policy and v2 for explicit legacy policy. Earlier strict
validation records had a stale v2 label despite correctly enforcing v3 binding;
those stored records remain unchanged as historical evidence.
The selected policy participates in brief identity/hash binding and is recorded
in validation, run manifests, attempts, reports, and preflight output.

Historical P6A.2 brief bytes and their interpretation are unchanged. Old exports
in `output/p6a_ai_authoring` remain historical v1 schema evidence; runtime models
define the unchanged v2 candidate shape. No candidate operand-metadata fields
or calculation-node IDs were added.

## Exact rules

- `first_term`: `sum_x2 / n`
- `second_term`: `(sum_x / n)^2`
- `mean`: `sum_x / n`
- `variance`: `first term - second term`, or exactly the expanded tree
  `sum_x2 / n - (sum_x / n)^2`

Matching uses the existing canonical AST, not expression text or evaluated-value
equivalence. Existing aliases (`Σx`, `Σx²`, `÷`, `²`) and redundant parentheses
are accepted only insofar as the frozen parser produces the same tree. No
commutative/algebraic simplification is performed. The policy intentionally
rejects even numerically equivalent alternative derivations outside these trees.

The application-owned dependency map resolves `n`, `sum_x`, and `sum_x2` to the
candidate's proposed input fields; derived `first_term`, `second_term`, and
`radicand` resolve through `context_for()`'s independent Fraction calculations.
Candidate intermediate claims never supply binding values. The map describes
fixed dependencies; it is not a general graph framework or a second math engine.

Self-references such as `first term` in its own destination, `second term` in its
own destination, and `radicand` in variance fail. Constant or mixed literal/source
operands fail the new policy, even when values coincide with the intended source.
In particular, a denominator `radicand` cannot replace `n` when both equal 4.

## Independent trust dimensions

`math_valid`, `solution_valid`, and `expression_semantics_valid` retain their
existing behavior. `derivation_provenance_valid` is independent: correct source
structure may pass while a wrong claimed scalar fails semantics/solution, and
correct numeric working may pass semantics while provenance fails.

The provenance stage follows successful numeric encoding/input recomputation.
It is evaluated even if the expression-semantic check fails, and does not prevent
independent solution checks. Overall provenance-required acceptance and
composition require all existing gates AND a provenance pass. Compose revalidates
using the caller's application-selected policy.

Results contain a nullable boolean plus explicit status:

- `PASSED`: true; expected identities and tree established.
- `FAILED`: false; evaluated current-policy violation.
- `INSUFFICIENT_EVIDENCE`: null; historical numeric operands lack source identity.
- `NOT_EVALUATED`: null; historical absence, legacy policy, or an earlier gate
  prevented evaluation. It is never automatically converted into a violation.

Each evaluated field records expression, canonical AST, expected role and allowed
dependency trees, expected value, symbolic source paths/values/dependencies,
status, stable reason, verifier/policy version, and semantic-check context.
Qualification reports count all four statuses separately and verify attempt/audit
consistency. A required-policy acceptance without provenance PASS is rejected by
report reconstruction. Historical reports can be rebuilt into a separate output
directory without changing the source run.

## Historical and synthetic evidence

`tests_p0.provenance_replay.historical_replay()` verifies historical artifact
hashes through the existing P6A.3 replay, requires exact equality with the saved
P6A.3 report, and classifies the original ten candidates without transcription.
Their historical acceptance stays true and all forty semantic checks stay true;
all forty provenance outcomes are INSUFFICIENT_EVIDENCE. No source identities
are inferred or backfilled. Repeated replay is deterministic.

Separate synthetic controls cover all roles, both allowed variance trees,
existing aliases, wrong sources with equal zero values, swapped operands with
equal values, n/radicand collisions, literals, mixed operands, self-reference,
missing square, malformed syntax and unsupported syntax. They are labelled
synthetic and never represented as regenerated historical evidence.

## Limits and trust boundary

This proves the represented derivation references the intended proposed problem
parameters. It does not prove the model's internal reasoning or that parameters
describe an externally observed dataset. There are no raw observations in the
SL-10 candidate payload. There is no candidate square-root expression field;
radicand/numeric SD/display checks remain the existing deterministic checks.

No pedagogical explanation judgment, arbitrary symbolic proof, academic approval,
publication permission, renderer readiness, or global model qualification follows.
Student-facing literal substitution is a later rendering concern. This milestone
is offline; future live symbolic-generation qualification is a separate task.

## Engineering verification

Dedicated tests: `tests_p0.test_derivation_provenance`.
Historical/synthetic replay: `python -B -m tests_p0.provenance_replay` (exclusive
new output only). Verification output lives under
`output/p6a4_derivation_provenance`; old runs/manifests are never overwritten.

v1.5 may be created only after dedicated/focused tests and deterministic replay
pass, with exact tested-source hashes and an explicit changed-file allowlist.
Final full-suite/conformance checks occur after selecting the new baseline,
because current-conformance tests intentionally reject implementation edits
against the frozen v1.4 hashes. The known missing
`AI_Academic_Operating_System_Brainstorm_CN.pptx` error remains reported as an
unrelated full-suite error; no fixture or assertion is fabricated or suppressed.
