# P6A.6b — Controlled input infrastructure

This milestone implements offline request binding. It does not run P6A.6c,
qualify a model, approve academic content, or grant renderer readiness.

## Ownership and versions

The application selects an immutable `ControlledCase` containing a distinct
`controlled_case_id` and the existing `Inputs` triple. Catalog A–H stores only
the approved source triples; existing authored mathematics recomputes results.
The mode is `sl10-controlled-input/1`. The provenance policy remains
`sl10-provenance-required/1`; Candidate Contract and provider response schema
remain `ai-author-candidate/2` and the existing content-only schema.

`authoring-brief/4` extends brief/3 with `controlled_mode`, `controlled_case`,
and `controlled_case_sha256`. It replaces the free numerical-choice instruction
with explicit fixed values and removes the original-numerical-problem wording.
Sorted, indented UTF-8 JSON with a trailing newline is hashed using SHA-256.
Case hashes bind the identifier and original source representation. Brief hashes
bind that complete case context and all instructions. Brief/2 and brief/3 keep
their historical serialization and interpretation.

## Validation and acceptance

Before provider construction, case validation reparses even model instances,
requires a strict integer `1 <= n <= 1000000`, ASCII scalar sum strings of at
most 128 characters, nonzero rational denominators, feasible nonnegative
variance, and zero variance for a singleton. Unknown mode, legacy policy with
controlled mode, missing case/hash, or hash disagreement fails closed.

The compiler, service, validator, composer and runner receive the same
application-owned context. The service and runner snapshot caller dictionaries
into frozen nested models. A candidate cannot supply the expected case.

The independent `controlled_input_binding_valid` result is nullable, with
`PASSED`, `FAILED`, or `NOT_EVALUATED` status and a reason code. Input mismatches
do not prevent independent internal mathematics and provenance checks; a
correct answer to the old 5/15/55 problem can therefore be reported as internally
correct but rejected for ignoring the required case.

Integer n must match exactly. Sum strings are parsed by the existing exact
rational parser and compared without float tolerance. Thus `0.5` and `1/2`
are equal. Returned strings are preserved verbatim. The existing structural
equality between proposed inputs and solution inputs remains stricter: both
candidate copies must use identical strings. Composition revalidates the entire
candidate with the same case and requires a positive controlled binding gate.

## Qualification and deterministic replay

Each run has one immutable controlled case, one brief and one brief hash.
`execute` accepts `controlled_mode`, `controlled_case`, and
`controlled_case_sha256`. Controlled mode is orthogonal to `live_normal` or
`offline_synthetic`; it cannot be mixed with adversarial stress identities.
The existing adversarial `case_id` stays null for controlled attempts.

The run manifest, validation, attempt and report preserve case identity, values,
hash and mode. Attempts additionally preserve the original returned triple and
binding status/reason, alongside all existing qualification dimensions. Schema
and operational failures remain unevaluated rather than mathematical failures.

Report rebuilding reads the saved application case, verifies agreement with the
saved brief and every attempt, and independently recomputes exact binding from
the candidate. Missing results or forged pass flags fail closed. Rebuilding
needs neither provider access nor a trusted-database read. Historical free-mode
models and serialization are unchanged; historical evidence is never rewritten.
Local hashes provide consistency evidence, not a digital signature or external
authentication of a wholly replaced run directory.

The qualification CLI adds `--controlled-case A` through `H`. It validates the
selected case before constructing a provider. A future authorized run can use
`--attempts 1` with one selected case. P6A.6c's proposed eight separate live runs
require a later task; none are executed here. Dry-run remains available.

## Verification and freeze

`tests_p0/test_controlled_inputs.py` covers all eight cases, exact equivalent
encodings, distinct brief hashes, immutable context, existing math/expression/
provenance gates, composition, saved-case replay, malformed cases before factory
construction, changed case/id/hash, old-triple rejection, solution-copy mismatch,
missing mode/gate, and replay tampering. All authors in these tests are synthetic.

`tests_p0/controlled_acceptance.py` records network-blocked test results and
creates eight clearly labeled offline synthetic runs. It replays P6A.2–P6A.5
without changing their artifacts. `tests_p0/controlled_baseline.py` creates v1.6
only after exact-source focused/regression evidence and replay pass, preserving
v1.1–v1.5 baseline files. Evidence is under `output/p6a6_controlled_inputs/`.
The acceptance artifact records actual results and the active manifest hash.

The known historical full-suite missing brainstorming PPTX is outside this
milestone. Any occurrence is reported explicitly, never suppressed. No parser,
provenance implementation, core mathematics, renderer, trusted database,
governance record, protected snapshot or historical academic artifact is edited.
