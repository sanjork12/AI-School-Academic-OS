# P6A.1 — live-model qualification runner and guardrail stress tests

This phase implements the measurement apparatus. **No paid qualification or
adversarial call was executed during implementation. The live model is not yet
qualified.** Synthetic outcomes are not evidence about a real model's quality.
The supplied attachment ends during section 63; this implementation follows the
requirements available through that point.

## Boundaries

Only `standard-deviation / standard-lesson / profiled-sd-standard-lesson-SL-10`
is supported. The P6A brief, provider settings, strict schema, numerical engine,
scope checks, composition policy and acceptance semantics remain unchanged.
The P5C/P5D render path and current PowerPoints remain unchanged. No report is an
academic decision, publication, canonical fact, model certification or renderer
permission. There is no acceptance threshold, score, retry, repair or feedback
loop. Accepted examples stay inside experimental attempt artifacts.

New code is under `academic_os/ai_qualification/`. The existing P6A code is not
edited. `ObservedAuthor` forwards the exact normal P6A call while recording only
allowlisted observations. It constructs a fresh observation for each attempt;
no candidate, rejection reason, history or aggregate enters a subsequent call.
The SDK's existing `max_retries=0` remains in force. The qualification layer does
not invent temperature or reasoning settings; it records only actual arguments.
Configured model and provider-reported model (when available) are distinguished.

## Non-billing inspection

Run from `D:\AI-School-Academic-OS`:

```powershell
python -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --dry-run
```

This reads current gates and prints the slot, exact unchanged normal brief,
brief hash, count, model setting, output location and no-billing status. It does
not construct a provider, load credentials or create a run. The dry-run model
display reads `ACADEMIC_OS_AUTHOR_MODEL` from the environment. If it is absent,
the display says so; it does not guess what a later dotenv load would contain.

## Operator-only live normal qualification

Set `ACADEMIC_OS_AUTHOR_MODEL` to the desired supported model in the environment.
The same P6A environment/dotenv credential convention is used; do not put a key
on the command line or in experiment files. Use the existing `.venv` SDK runtime:

```powershell
.venv\Scripts\python.exe -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --output-dir output/p6a1_live_qualification --live
```

**This command may incur API charges.** It prints `LIVE API CALLS WILL OCCUR`,
the count and model before authoring starts. Default count is 10; permitted range
is 1–20. Missing explicit mode or excessive count is rejected before loading
inputs or constructing a provider. A provider failure is not retried; the next
scheduled attempt is a separate call under the same brief. Current source gates
are refreshed after each live call. Changed/unavailable inputs stop remaining
calls. These source checks may take substantially longer than the model call;
recorded model latency is not total pipeline runtime.

## Separate offline and optional live stress modes

Offline, no model or credential required:

```powershell
python -m academic_os.ai_qualification --db var/p0_q2.sqlite3 stress-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --output-dir output/p6a1_offline_stress --offline
```

This runs 16 explicitly synthetic forbidden cases: wrong answer, negative
variance, sample SD/n−1, difficulty, frequency, typical marks, common mistakes,
prerequisites, memorisation, calculator procedure, unsupported raw-data
assessment, unknown LR, answer leakage, missing scaffold, extra authority
fields and inconsistent question/solution inputs. Existing P6A violation codes
are retained. Unknown model-supplied LR fields are rejected by the strict
content schema before any binding authority exists. Textual task-form changes
are rejected by the existing controlled-language boundary. P6A validation is
not broadened or weakened to accommodate stress cases.

Optional, explicit paid adversarial test (not executed here):

```powershell
.venv\Scripts\python.exe -m academic_os.ai_qualification --db var/p0_q2.sqlite3 stress-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --case n_minus_one --case exam_claim --case memorisation --case wrong_math --output-dir output/p6a1_live_stress --live
```

There is one call per selected case (at most four, duplicates forbidden).
Adversarial instructions live in an isolated `live_adversarial` scenario that
contains a copy of the normal brief. The normal brief is never modified. For
`wrong_math`, a recorded application mutation changes the proposed display
answer to `-1.00` after generation; the original model response is separately
preserved. This ensures a wrong answer is exercised without hoping the model
makes a mistake. The mutated input is labelled as a stress candidate, not as
the unmodified model output.

If the model refuses, fails operationally, or does not emit the specific
forbidden probe, the guardrail case is **inconclusive**. A refusal is not counted
as a successful validator block. “Correctly blocked” requires an observed
forbidden probe, candidate rejection and failure of the expected existing
guardrail. The probe recogniser is deliberately narrow; it is not a general
semantic classifier. Unexpectedly accepted forbidden synthetic cases fail the
regression suite; they are not hidden in a score.

## Persistence, interruption and deterministic reports

Each invocation creates a unique `run-<application-id>` directory. It contains
`run.json`, `brief.json`, then separate `attempt-01`, `attempt-02`, etc. Each
completed attempt preserves:

- `started.json`: identity and start time, written before the author call.
- The existing P6A candidate audit, including experimental content only if accepted.
- `brief.json`, `raw_candidate.json`, `validation.json`, `provider_observation.json`.
- `attempt.json`: a final commit record with outcome, timings, safe request ID,
  usage, check flags and hashes of its subordinate artifacts.

Writes are exclusive and atomic; existing attempts are never overwritten.
Provider exception bodies, headers and credentials are not logged. Secret-like
responses are withheld. Raw recovery may be unavailable after an SDK parsing
exception; this is reported rather than filled with invented output.

A normal completion writes `completion.json` with the engineering integrity
comparison. An interrupted process preserves completed attempts. A hard kill
may leave only `started.json` for the active attempt and no completion marker:
its billing/response outcome is then unknown. Never automatically resume or
assume the unrecorded call did not occur. A 10-attempt run with six completed
records reports six completed attempts and an incomplete status.

Rebuild a report from a saved directory without any model, credential, source
reload or trusted database access:

```powershell
python -m academic_os.ai_qualification rebuild-report output/p6a1_live_qualification/run-<actual-run-id>
```

The `live-model-qualification/1` report is written under
`reports/report-<content-hash>.json`. Rebuilding unchanged stored records gives
the same bytes and path. Existing reports are retained. The reader checks
artifact digests and cross-checks attempt summaries against candidate audits.
It does not treat filesystem artifacts as signed credentials or academic truth.

Normal validation aggregates exclude stress attempts. Provider/input failures
have unevaluated check fields (`null`) and are excluded from mathematical,
scope and boundary rejection summaries. Schema failures do not claim the maths
was evaluated. Usage summaries include provider-reported values and counts of
missing values; cost is `not_computed`. Latency is descriptive min/max/mean/median.
Incomplete active attempts may have unknown usage; started/completed counts
make that gap explicit. `complete` means the requested experiment finished,
not that a model is qualified or suitable for production.

## Integrity and test evidence

Engineering integrity snapshots compare protected file bytes, trusted database
bytes and read-only table digests before/after runs. The pre-AI inventory is
used only for that comparison, never as an authoring or approval credential.
P6A and qualification implementation files are also captured for runtime
comparison. Candidate validation continues to use the existing current gates.
Offline synthetic stress uses one current input read plus before/after integrity
checks; live attempts additionally refresh current gates after each call.

Tests:

```powershell
python -m unittest tests_p0.test_ai_qualification -v
python -m tests_p0.ai_qualification_acceptance --output-dir output/p6a1_acceptance_new_run
```

The acceptance command saves a 10-attempt **synthetic** normal demonstration and
the 16-case synthetic stress report. It never invokes a real provider. Its
artifact directory is exclusive and must not be reused to overwrite prior
evidence; choose a new `--output-dir` for another run. Windows terminal JSON uses
Unicode escapes so GBK consoles preserve the exact decoded brief; saved artifacts
remain UTF-8. Input changes detected during a call are operational input failures,
not model mathematical rejections. Full-suite execution was not rerun;
the historical missing PowerPoint error in the unchanged freeze receipt remains.
