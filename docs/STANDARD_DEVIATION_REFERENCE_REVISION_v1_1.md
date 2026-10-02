# Standard Deviation Vertical Slice v1.1

Pre-AI Reference Implementation — Trusted-Read Performance Revision.

This is a revision of [the original architecture](STANDARD_DEVIATION_REFERENCE_ARCHITECTURE.md),
not a replacement. The original architecture, v1 manifest, acceptance and freeze
artifacts remain byte-identical. Their SHA-256 inventory is recorded in v1.1 lineage.

## Why this revision exists

P6A.1a changed `academic_os/sources.py` to reuse PDF parsing and page extraction by
current byte hash, running parser version, page and extraction policy. Its bounded,
locked process-local cache contains computation, not verification or approval.
The original v1 source hash correctly differs. It has not been reset.

The only changed production file in the v1 protected inventory is `sources.py`.
P6A/P6A.1 modules added after v1 are separately inventoried as experimental authoring
and qualification code, not reference academic content. Older examples/migration files
omitted by v1's shallow source inventory are explicitly identified as coverage additions;
v1 did not establish their historical byte hashes. No historical equality is claimed for
uninventoried files. P6A.1b additionally changes the qualification engineering preflight
and adds its version-aware verifier; these are explicitly authorized baseline-selection
changes, separate from the P6A.1a performance delta.

## What is preserved and independently checked

Acceptance rebuilds the current profile/product chain through the normal source,
review, governance and snapshot gates. It compares live learning requirements,
assessment evidence, lesson profiles, pedagogy, authored packages, validators and
presentation manifests/teacher solutions with the protected deterministic reference.
It recomputes the academic scope fingerprint through P5A logic. The requirements remain
understanding SD, calculating SD, and calculating SD from supplied summary statistics.
Reviewed examples remain 2025 Q2(b) and 2023 Q3(b)(ii).

Focused Review remains 25 minutes / nine substantive roles; Standard Lesson remains
60 minutes / 15 pedagogical roles. Role counts are not slide-count requirements.
Database byte hash, table summaries, review/governance counts and both snapshot IDs
are unchanged. Reference PPTX and Gold Standard files are compared by hash without
regeneration. P6 experimental candidates remain engineering evidence and are not
inserted into reference content, approvals or snapshots.

## Explicit engineering selection

`academic_os.ai_qualification.reference_baseline.ACTIVE_REFERENCE_BASELINE` is `v1.1`.
`output/reference_freeze_active.json` binds that version to an exact manifest path and
SHA-256. There is no latest-directory selection or generic upgrade framework. The
manifest does not hash itself; its digest is outside it in the active descriptor and
acceptance metadata. No self-referential hash cycle is created.

`verify_reference(..., 'v1')` verifies the recorded historical parent documents and
reference artifacts. It does not demand that current source code match historical
source bytes, and does not pretend to reconstruct the old source file. Those historical
hashes stay in v1. `verify_reference(..., 'v1.1')` also checks the current approved file
inventory, detects unexpected production additions/removals, and checks the trusted
database. Tests that mean current conformance explicitly select v1.1.

The qualification CLI now performs engineering preflight before constructing any
provider, including dry-run. A mismatch fails closed. The experiment runner retains
its before/after integrity checks. The descriptor and manifest are local operator
engineering configuration, not signed production authentication or academic authority.
`Service.snapshot`, source integrity, review/governance evaluation and P5C remain the
runtime academic gates. None of them consume the reference baseline.

## Performance and remaining limitations

P6A.1a measured 880 reader constructions/extractions reduced to five cold extractions,
then zero additional warm extractions. Each input read still performs 160 snapshot
checks and 240 integrity checks (including deferred Q3 governance). Observed cold/warm
times were 6.28/5.97 seconds and dry-run 7.00 seconds. These are evidence, not an SLA.
The cache retains at most eight readers and 128 page strings, not a fixed RSS limit.
The upstream 80 product reads are intentionally not refactored here.

See `output/reference_freeze_v1_1/acceptance.json` for current comparisons and exact
test results, including the historical missing `AI_Academic_Operating_System_Brainstorm_CN.pptx`
error. Its file is not fabricated, its pinned hash is not changed, and its test is not
skipped. No model call or paid qualification is performed by this revision.

## Reproduce checks

```powershell
python -B -X utf8 -m unittest tests_p0.test_reference_revision tests_p0.test_source_cache tests_p0.test_source_cache_integration
python -B -X utf8 -m academic_os.ai_qualification --db var/p0_q2.sqlite3 qualify-ai-author standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --attempts 10 --dry-run
```

The manifest generator in `tests_p0/reference_revision.py` verifies a closed allowlist
and live invariance before writing new files. It refuses to replace an existing manifest
or active descriptor. Acceptance logs and final acceptance are outside the manifest's
protected inventory to avoid circular hashing.
