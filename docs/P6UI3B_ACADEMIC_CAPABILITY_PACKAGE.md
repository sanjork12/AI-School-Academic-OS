# P6UI.3B — Selected curriculum target to academic capability package

This deterministic core bridge describes available curriculum evidence and missing
academic prerequisites. It constructs no learning specification, lesson, question,
exam or presentation, calls no model, and writes no trusted academic state.
The existing Standard Deviation pipeline is unchanged.

## Contracts and input identity

The existing `SelectedCurriculumTarget` is extended to
`selected-curriculum-target/2`. Its digest now also covers schema version, validation,
tree and terminal parser-run hashes, plus topic/subtopic names. Existing document,
source hash, run, parsed hash, profile, specification, tier, codes and source IDs
remain. Refresh v1 selections through the existing capabilities endpoint; saved
P6UI.3A runs and historical acceptance artifacts are never migrated or rewritten.

The target is a reference, not caller-authoritative academic content. The service
resolves its source, parsed output, validation and tree; reproduces validation and
tree projection; checks extraction/document/tier bindings; and compares the whole
target to a freshly derived identity. Missing, stale or inconsistent evidence fails
closed. Hashes detect drift against registered evidence, not a hostile actor who
can rewrite every local source, manifest and application together.

## Package schema and deterministic identity

`AcademicCapabilityPackage`, version `academic-capability-package/1`, contains:

- The existing selected target and explicit source/run/output hashes.
- Selected objective records with exact original parsed source wording, source ID,
  tier, topic/subtopic names, notes, run-wide warnings and validation hash.
- Separate canonical abstractions, historical review labels, available decision IDs,
  source-bound mapping evidence and explicit mapping gaps.
- Coverage counts, unresolved prerequisites, warnings, eligibility and evidence hashes.
- Fixed `academically_approved=false` and `model_calls=0`.

Construction version is `topic2-capability-construction/1`. Canonical UTF-8 sorted
JSON bytes determine the package SHA-256 and package ID. Identical supplied evidence
produces identical bytes; a different document/run ID intentionally produces a
different package even if the PDF matches. A separate immutable receipt holds
construction time, package ID/hash and selected-target ID. Time does not enter the
content hash. Repeated persistence reuses the original receipt without overwriting.

Default storage is `var/p6ui/runs/capability-packages/<sha256>/`, covered by the
existing runtime ignore rule. Selected acceptance copies live under
`output/p6ui3b/packages/`. A package is run-bound and needs its referenced ingestion
evidence to validate on read. An interrupted two-file write is not auto-repaired.

## Canonical coverage and trust

The bounded historical evidence manifest pins the promoted Topic 2 graph, the two
human-review decisions, historical AI proposals and Foundation/Higher parsed files.
Associations require the known PDF hash, matching tier/subtopic/objective/source ID,
and byte-exact parsed official wording. IDs alone never establish equivalence.

`MAPPED` means a matching association exists in the preserved promoted prototype;
it does not mean this uploaded target is governed or approved. `UNMAPPED` means no
matching association/proposal. `REVIEW_REQUIRED` covers unresolved historical AI
proposals or source wording that no longer matches the historical association.
Counts are disjoint and sum to selected objectives. Multiple bindings count as one
mapped objective. Historical AI proposal IDs are retained even when later evidence
supersedes the proposal. Canonical wording never replaces source wording.

Legacy graph entries labelled `approved`/`human` do not all have separate review
receipts. Bindings therefore record `historical_review_status` separately from
`human_review_evidence`: only an exact approved mapping in a recorded human decision
gets `RECORDED_DECISION`; otherwise it is `NOT_AVAILABLE`. Historical promotion is
explicitly separate from uploaded-objective promotion, which remains false. No
Topic 2 trusted snapshot binding is asserted. Parser-derived, structure-valid and
source-bound are independent of human-reviewed, promoted and snapshot-backed.

The existing governance stack checks content/dependency versions and current
decisions and may withdraw stale snapshots. `product_reader.read_usable_snapshots`
uses an ephemeral SQLite backup to preserve read-only operation. Prototype JSON
approval labels do not replace these checks.

## Warnings and eligibility

Extraction, parser and validation warnings propagate without rewriting their text.
Warnings are run-wide because current evidence does not locate every ambiguous
glyph to an individual objective. Subtopic notes remain available. Missing mapping
and target-review warnings are added. Warnings do not prevent browsing.

Every capability carries `eligible`, `status`, `reason_code` and
`missing_requirements`. Browsing is `PASS_WITH_WARNINGS`. Learning-spec, pedagogy,
lesson authoring, question authoring and presentation eligibility remain `BLOCKED`.

Learning-spec prerequisites are target source verification; governed canonical
bindings; approved concept/capability/task relationships; reviewed assessment
evidence; current usable trusted snapshots; a bounded topic catalog adapter; and
consistent `teacher-topic/2` plus `assessment-intelligence/1` contracts. Mapping gaps
add the need for resolved coverage or an explicitly governed partial scope. Full
canonical coverage alone would still be insufficient. Later stages require their
own upstream contracts and adapters; no selection falls back to Standard Deviation.

## Standard Deviation comparison and next P6UI.4 boundary

The current `LearningSpecificationService` reads teacher and assessment services
from the same snapshots and compares provenance. Its generic architecture includes
versioned contracts, unique resolving references, source/evidence-backed learning
requirements, assessment coverage rules and explicit evidence boundaries.

Standard Deviation-specific elements are the catalog entry, product aliases,
concept/competency/task-condition IDs, bounded verified curriculum excerpt and
reviewed question relationships. These live upstream of the generic learning
projection. They must not be copied to Topic 2 under a different label.

Topic 2 aligns on curriculum identity, wording, source references, warnings and
explicit trust state. It lacks current snapshot-backed concept descriptions,
competency/concept/task relationships, reviewed assessment examples and the
consistent teacher/assessment input contracts. Historical canonical descriptions
are supplemental evidence, not substitute approved concept definitions.

The present Product service requires at least one reviewed assessment example.
Learning projection creates task-form requirements only where matching reviewed
examples exist; it does not require an example for every capability, nor invent
prerequisites, formula memorisation or teaching sequences. P6UI.4 must define a
bounded source-review and canonical relationship contract, verify usable evidence,
register an explicit topic adapter, and then provide mutually consistent upstream
contracts. There is no generic Learning Specification generation in this milestone.

`output/p6ui3b/standard-deviation-comparison.json` records the actual read-only
Standard Deviation result and the new package's gaps.

## Service, API and verification

Core: `AcademicCapabilityService(ingestion)` exposes
`build_capability_package(selected_target)`, `validate_capability_package(package)`,
`persist(package)` and `read_capability_package(id)`. Validation rebuilds from
current bound evidence. Reads verify content digest and revalidate provenance.
No client-provided mappings or filesystem paths are accepted.

Thin local API routes:

- `POST /api/curriculum-targets/{target_id}/capability-package`, body the current
  selected-target DTO, returns an immutable receipt.
- `GET /api/capability-packages/{package_id}`, returns the validated package.

Existing localhost/Host/Origin/session controls remain; this POST has a 16 KiB
stream-counted limit. Other JSON operations retain their 2 KiB limit. No UI changes.

Offline tests: `python -X utf8 -B -m unittest tests_p0.test_curriculum_capability`.
Acceptance reuses explicitly named completed P6UI.3A runs, forbids parsing/provider
calls, persists both tiers plus subtopic/objective selections and checks replay.
Historical bytes and the trusted database are checked before and after acceptance.

## Limitations

Only the verified 2017 4MA1 Topic 2 PDF/profile is supported. A target selects one
tier; combined-tier input is explicitly rejected. Consumers may retain two separate
packages; objectives are never deduplicated across tiers. Canonical coverage is
partial, warnings are not objective-localised, no new human approval is inferred,
and generic downstream generation remains unavailable.
