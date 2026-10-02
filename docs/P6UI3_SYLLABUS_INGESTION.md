# P6UI.3A — Bounded syllabus ingestion

The console supports real PDF upload and extraction. Parsing is a separate action.
No uploaded curriculum is promoted, published, academically approved, or connected
to the Standard Deviation teaching pipeline.

## Supported input and profile

- Text PDF only; MIME `application/pdf`, filename `.pdf`, maximum 10 MiB and 200 pages.
- Initial profile: `edexcel-4ma1-topic2-2017/1`, Pearson Edexcel International GCSE
  Mathematics A, Issue 2 November 2017, known 70-page local specification.
- Exact supported source SHA-256:
  `d58830e570d58aeccd7146f5465b3c117378c42d08d663f18478f2793c7e737b`.
- Foundation PDF pages 21–22; Higher pages 37–38. These are one-based PDF page
  positions, not the printed page numbers. Extraction accepts an explicit valid
  range of at most 10 pages; parsing requires the supported tier's exact range.
- No OCR, Word, arbitrary syllabus interpretation or automatic profile inference.
  Valid but unknown PDFs receive `UNSUPPORTED_CURRICULUM_PROFILE`; extraction/
  parsing is blocked rather than attempting an unverified profile. Another PDF
  revision, even one with similar wording, needs a separately verified profile.

## Startup and configuration

Retain the P6UI.2 local startup; install `requirements-p0.txt` and
`requirements-p6ui.txt`. PyMuPDF 1.28.2 is used for the original extraction method.
`python -B -m console_api` binds only 127.0.0.1:8765. The launcher supports local
dependencies in `tmp/p6ui-deps`. Build/start `frontend/` on 127.0.0.1:3000.

For a future explicitly requested AI parse, also install `requirements-p6a.txt`
and configure `ACADEMIC_OS_CURRICULUM_MODEL` and `OPENAI_API_KEY` in the backend
environment or project `.env`. The parser uses the existing dotenv convention,
never overrides environment values, and has no default/fallback model. The original
prototype used `gpt-5.6-luna`; this milestone does not change or qualify a model.
Missing configuration produces a BLOCKED run with `MODEL_CONFIGURATION_MISSING`.
The SDK is imported only inside the explicit live operation.

The parser retains the original bounded instructions and `CurriculumTopic` schema,
using the SDK's `responses.parse`/`output_parsed` boundary described in the
[official structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
One attempted call, 60-second timeout, zero retries, `store=False`. No provider
exception body, raw response, key or full environment is saved. `model_calls` in
live run metadata counts attempted parser invocations, not billed success.

## Three distinct operator actions

1. Upload PDF: creates a document record and source bytes; zero model calls.
2. Extract text: explicit path/range from the registered document, real page text,
   extractor version and warnings; zero model calls.
3. Parse: either **Replay preserved parse** or **Parse with AI**.

Preserved mode is openly labelled historical parser-output replay. It checks the
exact PDF hash, extracted text digest, tier/range and preserved JSON digest from
`preserved_4ma1.json`. It then calls the same parsing/ID/validation/tree pipeline.
It cannot be used with arbitrary uploaded content. It is not a new AI response.
Live mode requires both the explicit parse action and `confirm_model_call=true`;
the UI has a separate paid-call checkbox. Upload never triggers it.
The implementation and acceptance were offline; live model quality/availability
have not been newly qualified.

## Storage and immutable evidence

`var/p6ui/uploads/<opaque-document-id>/` contains `source.pdf` and immutable
`document.json`: original display filename, hash, byte/page counts, timestamp,
profile and upload status. Filename is never an identity or storage path.

`var/p6ui/runs/<opaque-run-id>/` contains append-only event snapshots and a
write-once terminal `result.json`. Extraction, parsed curriculum, structured
validation and topic tree are separate write-once files with SHA-256 bindings.
A parse run references its successful extraction run and document hash. Repeated
operations create new IDs. Completed records survive backend restart; interrupted
runs are not resumed automatically. Mutated PDF/output bytes are rejected on read.

`queued`, `running`, `succeeded`, `failed`, `blocked` reflect real work on a bounded
single-worker executor, at most two outstanding ingestion tasks. Downstream stages
after a failure remain NOT_EVALUATED. The SD executor is separate and unchanged.

## API

- `POST /api/syllabi?filename=<display-name>` — raw PDF body, not multipart.
- `GET /api/syllabi/{document_id}`
- `POST /api/syllabi/{document_id}/extract` — profile, tier, start/end pages.
- `POST /api/syllabi/{document_id}/parse` — extraction run ID, mode and live consent.
- `GET /api/syllabi/{document_id}/runs`
- `GET /api/curriculum-runs/{run_id}`
- Run subresources: `/extraction`, `/tree`, `/validation`, `/capabilities`.
- Capability query optionally accepts `subtopic` and `objective`; selections must
  exist in that validated run. It never accepts a topic-to-service routing key.

All mutations retain local Host/Origin/session protection. Raw bodies are counted
while streaming, so omitted Content-Length does not bypass bounds. Filename path
components, drive/ADS separators, invalid IDs, symlinks and Windows junctions are
rejected. Storage uses normalized real-path containment and exclusive file creation.
There is no upload-file download or arbitrary filesystem/command endpoint.

## Validation, tree and future adapter boundary

The original metadata, tier, subtopic ordering, objective ordering, source-ID,
duplicate and special empty-subtopic rules are extracted into a structured service.
CLI validation still delegates to these rules. Source IDs are assigned after
parsing and before validation, matching historical ordering and values.

STRUCTURE_VALID does not confirm official wording or mathematical extraction.
Private-use/replacement glyphs generate SYMBOL_EXTRACTION_WARNING; empty page text
is identified without OCR. Original parser warnings and validation warnings remain
visible. A failed validation produces no browsable tree.

Uploaded trees expose document/hash/run/profile/tier, topics, subtopics, objective
codes, official text, source IDs, notes and warnings. Canonical status is currently
unmapped for uploaded document versions: matching an old source ID alone does not
grant a governed mapping. The existing historical explorer still displays its
13/41 promoted mappings separately.

SelectedCurriculumTarget binds document ID, source hash, run ID, parsed digest,
profile/specification/tier, topic/subtopic, objective codes/source IDs and validation
state. Its deterministic target ID is the digest of this selection. The returned
CurriculumCapabilityPackage always has browsing=true and lesson/question/
presentation generation=false. No learning-specification adapter is implemented.

## Compatibility and verification

Legacy extraction retains default CLI PDF/ranges/output paths and now has an
explicit-path reusable function. Parsing CLI requires `--live` and a new `--output`;
the source-ID CLI requires explicit input/output. Importing any wrapper performs no
IO or provider construction. Historical outputs were not rewritten.

Tests: `python -B -m unittest tests_p0.test_syllabus_ingestion
tests_p0.test_p6ui_console -v`. Browser acceptance:
`node node_modules/@playwright/test/cli.js test --config playwright.ingestion.config.ts`
from `frontend/`. It starts real local servers and uses Microsoft Edge. Stop other
console servers first. Default test artifacts go to ignored temporary directories;
do not point `P6UI_ACCEPTANCE_DIR` at a frozen acceptance directory. Backend tests
save optional evidence only to a new `P6UI_INGESTION_EVIDENCE` path.

The browser test uploads the actual local PDF, extracts both tiers, replays the
bound preserved parses, validates and browses them, and verifies downstream blocking.
Existing SD and historical Topic 2 browser acceptance is also retained. Runtime
uploads, runs and caches are gitignored; selected acceptance evidence, source,
tests, documentation and reference manifests are retained.
