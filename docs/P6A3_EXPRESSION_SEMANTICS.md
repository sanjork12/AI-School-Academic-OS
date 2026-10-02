# P6A.3 controlled expression semantic verification

The AI remains a candidate author. The application parses an explicit SL-10
grammar and independently evaluates expressions from bounded proposed inputs.
Four intermediate expression results must match both the candidate's scalar
claim and the independently recomputed expected value. A correct scalar alone
no longer grants expression validity. Candidate/schema and P6A.2 prompt remain
v2; the validation report is `ai-candidate-validation/2`, expression verifier
`sl10-expression/1`, active engineering revision v1.4.

## Exact supported grammar

Case-sensitive tokens: ASCII integer/decimal constants (optional leading minus),
`Σx`, `Σx²`, `sum_x`, `sum_x2`, `n`, literal phrases `first term`, `second term`,
`radicand`, `sqrt`, parentheses, `/`, `÷`, `-`, `²`, and `^2`.
ASCII spaces, tabs and line breaks separate tokens. The internal space in each
phrase token is one literal space. No other syntax is inferred or normalized.

```
expression := division ("-" division)*
division   := squared (("/" | "÷") squared)*
squared    := atom [("²" | "^" "2")]
atom       := decimal | "-" decimal | variable
            | "(" expression ")" | "sqrt(" expression ")"
decimal    := ASCII_DIGITS ["." ASCII_DIGITS]
variable   := Σx | Σx² | sum_x | sum_x2 | n
            | first term | second term | radicand
```

Square-root evaluation is restricted to an outermost root with an exact rational
argument. Root composition such as `sqrt(2)/2` or `sqrt(2)^2` is unsupported;
there is no algebraic simplifier. Rational literals such as `15/2` use division.
Operators are left associative; square binds before division, then subtraction.
`Σx²` is the sum-of-squares variable; `(Σx)²` squares the sum.

Unsupported: equations/equality chains, addition, multiplication, other powers,
scientific notation, arbitrary names, natural language, LaTeX, attribute access,
indexing, imports, comprehensions and arbitrary function calls. No eval, exec,
Python AST interpreter or SymPy is used.

Aliases normalize to canonical AST variables; both square spellings and both
division spellings produce the same operators. Decimal constants canonicalize
to Fraction strings. This is structural normalization, not general algebraic
equivalence or candidate repair. Original expression text remains in reports.

## Exactness, bounds and trust

Rational evaluation stays exact with Fraction. Outermost sqrt uses the existing
50-digit Decimal root and absolute tolerance 1e-40. Numeric_answer, display_answer,
exact_radicand and the original arithmetic verifier are unchanged.

Limits: 256 expression characters, 128 tokens/nodes, 16 parenthesis/function
nesting levels, 128 characters per scalar, 2048 numerator/denominator bits after
each arithmetic operation. Evaluation depth is bounded at 128. Proposed n is a
strict integer in 1..1,000,000, and sums use the existing scalar grammar. There
are no floats, unbounded powers, or environment-dependent symbol lookups.

`first term`, `second term` and `radicand` are computed from proposed inputs,
never copied from candidate claims. A constant expression with the correct value
is mathematically consistent under this policy; the verifier does not prove a
pedagogically appropriate derivation or assess instructional quality.

The candidate gate adds `expression_semantics_valid` separately from existing
math_valid and solution_valid. Existing math_valid retains its input feasibility/
recomputation meaning; it is not silently redefined. Encoding failure leaves the
expression stage NOT_EVALUATED. Expression failure does not erase independently
successful solution checks, but blocks composition and overall acceptance.
Qualification attempts expose a nullable expression dimension for old records
and aggregate expression counts. Preflight does not claim ungenerated expressions
are verified. No approval, publication or renderer readiness is granted.

## Reasons

`unsupported_expression`, `unsupported_root_composition`, `parser_failure`,
`expression_limit`, `arithmetic_limit`, `division_by_zero`, `negative_radicand`,
`scalar_encoding_invalid`, `scalar_value_invalid`, `input_invalid`,
`expression_arithmetic_invalid`, `expression_value_mismatch`, and
`expression_expected_value_mismatch`. Candidate diagnostics identify the failing
intermediate's expression field. Reports retain canonical AST and evaluated value.

## Offline P6A.2 replay

Source: `run-46ccbed1b3874c04a226469477e4ea29`.
The replay verifies stored artifact hashes and brief binding, checks raw/parsed
content equality, then uses only saved candidate inputs and expressions. It does
not load current teacher JSON, reconstruct approvals, read the trusted database
as replay input, or invoke a provider. Saved proposal parameters are bounded
numeric operands, not academic truth.

Two independently constructed replay reports are identical. All ten candidates
are expression-valid; all forty intermediate checks pass. No expression is
unsupported or malformed. Original P6A.2 acceptance is a separate retained field,
not retroactively amended. The report cannot grant current academic trust from
saved JSON.

Historical P6A.1d transcriptions retain full equation strings and now fail the
new expression gate. Their old reports/fixtures remain immutable. Tests which
previously demonstrated unverified expression acceptance now assert rejection;
the old evidence is not rewritten to manufacture current success.

P6A.2's prompt and provider content schema are preserved, including their broader
explanatory-expression wording. This milestone makes no new generation calls.
A future explicitly authorized prompt revision may describe the narrower grammar;
the verifier will currently reject unsupported wording rather than repair it.

## Verification and artifacts

```
python -B -X utf8 -m unittest tests_p0.test_expression_semantics -v
python -B -X utf8 -m unittest discover -v
```

`tests_p0.expression_replay` creates an exclusive replay-report.json and refuses
overwriting it. Repeat the integration test to reproduce without changing output.
Results, hashes and counts are in `output/p6a3_expression_verification/acceptance.json`.
v1.4 records the source changes and preserves prior baselines and P6A.2/P6A.1d
evidence. Trusted database, review/governance decisions, protected snapshots and
academic materials are unchanged. No model/provider calls or rendering are added.
