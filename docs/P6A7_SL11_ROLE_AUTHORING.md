# P6A.7b — SL-11 role-generalized numerical authoring

Scope: offline implementation only. No model/provider calls, live qualification,
production lesson replacement, renderer integration, or academic approval.

## Contract and policy

`ai-author-candidate/2` and its ProviderContent schema remain unchanged. SL-11
uses an empty `scaffold_steps` list. The application owns the single formula hint;
it is never represented as one of SL-10's four calculation-step meanings.

- Role: `profiled-sd-standard-lesson-SL-11`, `guided_practice`.
- Brief: `numerical-role-authoring-brief/1`, identity
  `standard-deviation-standard-lesson-SL-11/1`.
- Support policy: `sl11-single-formula-hint/1`.
- Acceptance policy: `sl11-numerical-provenance-required/1`.
- Hint: `sl11-application-formula-hint/1`, sourced from the current deterministic
  SL-11 object's `scaffolding/0`, bound to its hash and the summary formula hash.
- Controlled mode: `summary-statistics-controlled-input/1`; reuses ControlledCase,
  exact rational input comparison, feasibility and encoding checks.

The role/policy/brief/hint are application-owned. Candidate v2's existing brief
hash and current-input binding cover them without adding model-owned authority.
Unknown or stale bindings, missing hints, and any model-authored scaffolds fail.
Only the existing closed question templates are student-facing; solutions remain
separate teacher content. An answer is not detected by banning numeric substrings:
the actual template/support allowlist controls what can be shown.

## Shared core and compatibility

`ai_authoring/numerical.py` contains the extracted numerical stages used by both
SL-10 and SL-11: scalar encoding, summary feasibility, solution inputs and values,
expression semantics, provenance, exact radicand, root and display validation.
The arithmetic, parser, provenance and controlled-input implementations and their
versions are unchanged. Existing SL-10 public entry points retain their behavior;
wrong-role submissions additionally receive `role_binding_invalid`.

`roles.py` defines the bounded SL-11 policy and authenticates its deterministic
support source through current P5C. `role_authoring.py` compiles the brief, binds
candidate identities, validates role/support plus mathematics, and produces a
standalone experimental role object. It does not mutate or adapt a P5 package.

The SL-11 report is `numerical-role-validation/1`. It exposes role and support
checks, numeric encoding, controlled-input status and mathematical stages.
`scaffold_valid` is null with `NOT_APPLICABLE`; it is never an artificial pass.
The existing SL-10 validation/report schemas remain readable and unchanged.

## Offline qualification

`ai_qualification/role_offline.py` accepts supplied candidates; it has no provider
or live-mode entry point. It uses existing exclusive, content-addressed storage.
Evidence includes the candidate, brief/version, role, semantic role, support
policy/hash, hint identity/hash, validation stages and experimental composition.
Rebuild requires caller-supplied current trusted inputs and recomputes validation
and composition. It never calls a model or reads the database itself.

The standalone composition keeps student question/inputs/hint separate from the
teacher solution and binds candidate, brief, policy and validation provenance.
`academic_approval`, `ready_for_p5c`, `ready_for_rendering` and `publishable` remain
false. Qualification does not certify pedagogy or grant publication permission.

## Verification and engineering freeze

Run with Python bytecode disabled:

```text
python -B -m tests_p0.sl11_acceptance focused
python -B -m tests_p0.sl11_acceptance evidence
python -B -m tests_p0.sl11_acceptance replay
python -B -m tests_p0.sl11_acceptance baseline
python -B -m tests_p0.sl11_acceptance postfreeze
python -B -m tests_p0.sl11_acceptance full
python -B -m tests_p0.sl11_acceptance close
```

Each evidence destination is exclusive; these are acceptance commands, not an
overwrite/retry workflow. All acceptance execution blocks network connections.
The baseline step refuses existing v1.7, requires passing exact-source focused
tests and offline evidence, verifies frozen candidate/composition/report replays,
checks unchanged candidate schemas and trusted state, and records the authorized
source delta. It preserves v1.1–v1.6 manifests and artifacts.

Evidence lives in `output/p6a7b_sl11`. The full suite is unfiltered. Its historically
known missing `AI_Academic_Operating_System_Brainstorm_CN.pptx` error is recorded
explicitly if still present; any other failure blocks closure.

## Limits

This proves one additional role and two bounded controlled fixtures, not a broad
stress qualification or a live SL-11 success rate. The existing renderer's one-hint
layout is compatibility context only. SL-09, SL-12, other topic mathematics,
complete-lesson coherence and publication approval remain future work.
