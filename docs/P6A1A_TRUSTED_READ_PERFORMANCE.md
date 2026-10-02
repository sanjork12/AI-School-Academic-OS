# P6A.1a — Trusted read performance

The change caches deterministic PDF computation, never a trust decision. The only
production file changed is `academic_os/sources.py`. There is no database migration,
persistent receipt, new approval, governance action, or snapshot publication.

## Cause and measured work

The preceding read-only diagnosis measured `read_inputs()` / `compile_brief()` at
108.20 seconds: 80 product reads, 160 snapshot checks, 240 integrity calls and 880
reader constructions/page extractions for five distinct pages. The old page cache
lived inside one integrity invocation. Each product read extracted three Q2 pages,
three deferred-governance pages, then five Q3-closure pages.

The new representative regression requires the same 160 snapshot checks, 160 direct
integrity calls and 80 governance integrity calls. A cold process extracts five pages;
an immediate warm read does no additional parsing/extraction. These fixture-specific
counts are tests, not constants in production.

See `output/p6a1a_trusted_read_performance/acceptance.json` for final test totals,
database/artifact comparisons and timings. `performance.json` contains instrumented
cold/warm measurements and the actual CLI dry-run result. Timing is informational:
instrumentation and concurrent regression work affect elapsed time. There is no
wall-clock threshold in tests.

The completed focused suite has 181/181 passing tests. Full discovery ran 1,075:
1,071 passed, three failed and one errored, with zero skipped. The three failures
are the source-byte freeze assertions described below; the error is the historical
missing PPTX. Exact traces are retained in `full-results.json` and `full-tests.txt`.
`performance-after-tests.json` repeats timing after both test processes finished.

## Cache identity and population

Every locator request reads the current local file bytes and computes SHA-256,
including on cache hits. The digest must match the registered source digest. A miss
parses those same bytes via `BytesIO`, avoiding a separate reopen after hashing.
Selected source records retain their existing independent file-digest check.

The reader key contains byte SHA-256, running `pypdf.__version__`, and an immutable
reader-policy tuple describing current defaults. The text key additionally contains
physical page index, extraction method and an immutable tuple of extraction options.
Current options are empty (existing pypdf defaults). Future behavior changes must
update the corresponding policy/options. Stored locator `extractor_version` trust
semantics are unchanged: the running parser's output is compared with stored text.

Only actual PDF parsing populates entries. Candidate text, AI responses, saved product
JSON, reference manifests and detached exports are never cache inputs. A private reset
function exists for tests; normal callers do not manage cache lifecycle.

## Bounds and concurrency

Two process-local LRU structures hold at most eight readers and 128 extracted page
strings. Text may outlive its reader; a text hit does not need another reader. These
are entry bounds, not a strict resident-memory byte cap: individual PDF/object sizes
still vary. They are conservative for the current five-file workload; large-document
resource limits would be a separate change.

A reentrant lock serializes lookup, lazy reader access, extraction, insertion and
eviction. pypdf readers are not concurrently mutated. File reads/hashing happen before
the lock. Concurrent identical misses result in one extraction. Failed extraction
never inserts a text result; no trust/negative-result cache exists. No normal-read
logging or metrics enter trusted identities.

## Invalidation and unchanged trust boundary

Changed bytes produce a different computation identity even with unchanged path,
length and restored modification time. Missing/unreadable files fail before cache
lookup. A parser/options change selects another entry. Every selected locator still
checks current source version, page identity, extracted text, text digest and anchor.
Multiple locators sharing a page are checked independently.

`Service.snapshot`, graph validation, dependency manifests, review-state evaluation,
governance selection and snapshot-block enforcement are untouched. Current reviews,
versions, approvals and usability are never cached. This includes deferred Q3
dependencies checked by `governance.event_state`. Candidate registration/extraction
still does not confer verification or academic approval.

The product reader continues to use a read-only database backup in memory. Its
existing behavior for transient integrity blocks in that disposable image is unchanged.
The implementation does not claim atomicity against arbitrary external filesystem
changes after a read; hashing and parsing do use one coherent byte buffer.

## Remaining scope

Upstream Product/Learning/Assessment reconstruction still fans out to 80 product
reads. No composition refactor was performed. Any later request-scoped reuse must
define its consistency boundary without retaining stale trust decisions.

Persistent receipts were deferred: five cold extractions are inexpensive after the
repeated work is removed, while durable receipts require their own authority,
tamper-handling and invalidation design. Live-model qualification was not run.

The older P5D/freeze tests also pin production source bytes. Their three whole-file
freeze assertions detect the authorized `academic_os/sources.py` edit. The old pins
and tests are deliberately retained; unchanged reference output artifacts do not
imply unchanged current production code. The qualification engineering preflight
likewise reports `freeze_inventory_matches=false` for this source edit and would
block a live run before an API call. A separately reviewed engineering-baseline
transition is required before live qualification resumes; this task neither resets
the old inventory nor bypasses that guard. Dry-run does not execute that live-run
preflight and is not evidence of live qualification readiness.

## Reproduction

```powershell
python -B -X utf8 -m unittest tests_p0.test_source_cache tests_p0.test_source_cache_integration
python -B -X utf8 -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --dry-run
```

The acceptance directory also retains focused/full test logs. The historical missing
`AI_Academic_Operating_System_Brainstorm_CN.pptx` integrity error, if present, must be
reported rather than changing its pinned hash or manufacturing the file.
