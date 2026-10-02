# P6A.2 direct v2 qualification: implementation and preflight only

P6A.1 rejected ten outputs whose four intermediate scalar fields contained
equations. P6A.1c introduced `ai-author-candidate/2`: expression is explanatory
text; value is a strict scalar integer, decimal or simple rational. P6A.1d's
explicit offline transcriptions passed for all ten historical candidates. That
did not measure the live model's ability to emit v2 directly.

P6A.2 prepares ten new, independent normal attempts using the configured
`gpt-5.6-sol`, standard-deviation, standard-lesson and SL-10. Default attempts is
10, maximum 20. No provider call is made by this implementation/preflight task.
No model qualification threshold exists; `model_qualified` remains null.

## Explicitly authorized engineering revision

The original request required both new CLI/runner behavior and unchanged v1.2
current-code conformance. v1.2 pins those exact files, so both cannot hold.
The operator explicitly authorized v1.3 to complete implementation while
preserving v1.1/v1.2 artifacts and hashes. P6A.2 requires the active v1.3 baseline;
v1.2 is verified as historical artifact integrity, not current-code conformance.
This exception is recorded in acceptance and in the child baseline manifest.
The candidate contract remains v2. No academic source, review or snapshot is
approved through an engineering manifest.

## Preflight

The same CLI reads the current trusted chain, validates sources, snapshots,
review/governance/dependencies, lesson profile and P5C, compiles the brief, and
checks the active engineering inventory before creating a provider. Model
resolution uses the same environment/dotenv function as the adapter, with
environment precedence. Missing/invalid configuration and a model other than
the requested experiment model fail closed. No SDK client is constructed for
dry-run; credentials, authentication, network access and model availability are
not tested by preflight.

The operator authorized the following process-local model setting. It does not
write `.env` or change credentials. From the project root in PowerShell:

```powershell
$env:ACADEMIC_OS_AUTHOR_MODEL = 'gpt-5.6-sol'
.venv\Scripts\python.exe -B -X utf8 -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --output-dir output/p6a2_live_qualification --dry-run
```

Dry-run reports the resolved model/provider, candidate and engineering versions,
brief hash and full brief, exact slot, output directory, no stress cases, and
`live_api_will_be_called=false`. Repeated runs with identical inputs produce the
same brief/hash and plan. No content hash includes timestamps.

## Operator-only future live command — not executed by Codex

```powershell
$env:ACADEMIC_OS_AUTHOR_MODEL = 'gpt-5.6-sol'
.venv\Scripts\python.exe -B -X utf8 -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --output-dir output/p6a2_live_qualification --live
```

The existing adapter requires its existing credential configuration at live
startup. Each execution creates a unique immutable run folder. Raw responses,
parsed candidates, exact brief, metadata/usage/request ID where available,
latency, validation and attempt records are retained under that new folder.
Secret-like responses remain withheld by the existing safety boundary; SDK
parse failures may prevent raw response recovery. Neither exception bodies nor
credentials are persisted. No pricing or cost is invented.

## Runtime behavior

Every attempt now performs a fresh trusted-input read and P5C check before
constructing/calling its author, then retains the existing post-call refresh.
Revocation or changed inputs before the next attempt prevent that call. Invalid
input/trust state stops the run as incomplete, without pretending it is a
model-quality rejection. Ordinary candidate rejection or provider failure does
not trigger retries or stop the remaining independent normal attempts.

Provider failures and candidate rejections remain separate. The new optional
numeric_encoding_valid attempt field is true, false or null for unevaluated.
Historical records lacking it remain readable as unknown. Aggregate reports add
numeric encoding counts, completed provider calls and provider failures. Reports
still separate normal/stress results; no quality score or threshold is added.
The first operator run above is normal-only with stress_attempted=0.

Raw content is validated as received. There is no RHS extraction, expression
evaluation, correction, normalization, retry, repair or adaptive prompt. The
unchanged arithmetic engine recomputes all values, exact radicand, finite decimal
SD with tolerance 1e-40 and two-decimal ROUND_HALF_UP display. Input identity is
enforced. The brief explicitly forbids equations, prose, units and calculation
chains inside value. Controlled question/scaffold and scope checks remain.

## Interpretation limits and tests

Expression semantics remain unverified, even when scalar values pass. Candidate
acceptance grants no academic approval, publication permission, teacher-content
approval or renderer readiness. No past candidate is used as new live evidence.

Focused tests cover no-provider preflight, deterministic output, missing/wrong
model, baseline mismatch, upstream trust errors, P5C failure, fresh pre/post-call
reads, between-attempt revocation, raw preservation, no early stop on rejection,
and separate operational failures. Existing P6A.1c/P6A.1d and P4B/P5C tests cover
numeric contract/negative controls and real trust semantics using isolated data.
All SDK/provider behavior in tests is synthetic or mocked.

```powershell
python -B -X utf8 -m unittest tests_p0.test_direct_v2_preflight tests_p0.test_candidate_contract tests_p0.test_offline_candidate_replay tests_p0.test_ai_authoring tests_p0.test_ai_qualification tests_p0.test_content_validation tests_p0.test_profiled_validation -v
python -B -X utf8 -m unittest discover -v
```

Implementation/preflight results, integrity comparisons and exact test counts
are in `output/p6a2_live_qualification/acceptance.json`. The historical missing
`AI_Academic_Operating_System_Brainstorm_CN.pptx` error remains visible; its test
and pinned hash are not changed. This milestone ends before live execution.
