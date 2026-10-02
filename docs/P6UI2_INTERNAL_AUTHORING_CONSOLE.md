# P6UI.2 — Internal Academic Authoring Console

The home page now calls real local Python services. It does not execute the old
filename-only import or processing timer. Those legacy components remain unused
in the source tree; their data tests still describe a historical demo.

## Supported workflows

- Existing 9MA0 Standard Deviation, Standard Lesson: current deterministic assembly
  and validation through all nine existing public services, 15 ordered roles,
  questions, separate teacher answers, stage evidence and registered run artifacts.
- Existing 4MA1 Topic 2: Foundation/Higher tree from parsed artifacts, existing
  structure validator output, original wording/source IDs/notes/warnings, promoted
  mappings including unmapped objectives. It has no teaching adapter.
- Frozen P6A.5, P6A.6 and P6A.7b evidence: accepted and rejected cases, separate from
  the current P5 lesson. SL10 historical live and SL11 offline capability only.
- Existing P5 Standard Lesson PPTX, manifest, solutions and rendering validation.

No uploads, live AI, generic topic authoring, question/exam generation, governance
decisions, publishing, rendering, or P6-to-P5 integration are implemented.

## Local startup (Windows PowerShell)

From `D:\AI-School-Academic-OS`, use Python with the existing P0 requirements:

```powershell
python -m pip install -r requirements-p0.txt -r requirements-p6ui.txt
python -B -m console_api
```

Backend always binds `127.0.0.1:8765`. The launcher also supports dependencies
installed locally in `tmp/p6ui-deps`; this directory is not part of the baseline.
The implementation was tested with Python 3.14, Pydantic 2.12.5, FastAPI 0.135.1,
Starlette 1.7.0 and Uvicorn 0.42.0. A Starlette TestClient deprecation warning about
httpx is non-failing; tests use the existing httpx 0.28.1.

In another terminal:

```powershell
cd D:\AI-School-Academic-OS\frontend
npm ci
npm run build
npm start
```

Open `http://127.0.0.1:3000`. With existing dependencies and Node but no npm wrapper:
`node node_modules/next/dist/bin/next build`, then `node scripts/serve-static.mjs`.
The API endpoint is deliberately fixed for this local milestone. Do not change
the listener to a public interface. Start the backend before loading the page;
reload the page after recovering a backend startup failure.

## Architecture and boundary

React client -> FastAPI DTOs -> existing Academic OS services -> isolated run files.
No academic parsing, math, qualification or authoring logic is duplicated in React
or HTTP handlers. Topic 2 structural validation invokes the existing validator as
a fixed, bounded command (no shell); operators cannot submit commands or paths.

The teaching database is explicitly `var/p0_q2.sqlite3`, never a default database.
Both protected snapshot IDs are displayed. Current product services perform source
checks and use the existing read-only/in-memory database boundary. Database hashes
are checked before/after each run. No trusted write API is exposed.

The single-worker executor permits at most two outstanding jobs. Every stage is
updated after its actual service call, initially NOT_EVALUATED; polling only reads
state. Exceptions fail the run, preserve completed evidence, and withhold lesson
endpoints. No automatic retry, synthetic success, or provider fallback exists.
Run metadata and outputs are saved beneath `output/p6ui2/runs/<opaque-id>`.
Completed-run API state is session-local; files remain for audit after restart but
are not automatically reloaded. They are excluded from the engineering baseline.

## API

GET: `/api/health`, `/api/session`, `/api/sources`, `/api/curriculum/topic2`,
`/api/topics/standard-deviation`, `/api/history`, `/api/artifacts`,
`/api/artifacts/{id}`, `/api/runs/{id}`, and run subresources `/lesson`,
`/evidence`, `/questions`, `/solutions`.

POST: `/api/runs/assemble-standard-lesson` only. Explicit request literals constrain
source/topic/profile to SD/SD/Standard Lesson; extra fields are rejected.
Mutations require an allowlisted browser Origin and a session token. Allowed
origins are localhost or 127.0.0.1 on port 3000. Host checks prevent DNS rebinding;
JSON request size is bounded. No secrets or raw provider responses are returned.

Artifacts use registered content-bound opaque IDs. Path normalization, output-root
containment and digest checks reject unregistered paths, traversal and changed files.
Historical P5 artifacts and P6 evidence are checked against v1.7 evidence hashes;
P6A.6 candidate digests are also bound by the frozen P6A.7b replay report. These
checks establish historical file identity, not new academic approval.

## Evidence semantics

PASS means the named service/check passed for its stated scope. Availability is
not approval. `curriculum_verified=true` and
`curriculum_association_confirmed=false` are displayed separately. The latter is
NOT_EVALUATED with its actual false value, not a positive binding claim.
Academic approval is NOT_EVALUATED; publication is NOT_APPLICABLE. Current P5
renderer eligibility reflects P5C, but no render is requested. Historical P6
qualification does not confer renderer readiness or replace P5 content.

Questions expose inputs and solution IDs, never answer fields. Teacher solutions
have a distinct endpoint, tab and teacher-only label. This internal console is not
a student delivery security boundary; operators may intentionally open teacher files.
Worked-example solutions are also kept in that separate tab in this minimal UI.

## Tests and acceptance

```powershell
python -B -m unittest tests_p0.test_p6ui_console -v
cd frontend
node node_modules/@playwright/test/cli.js test --config playwright.console.config.ts
```

The browser tests launch both real servers and use installed Microsoft Edge. Stop
manually started servers first. On restricted Windows hosts Playwright process-tree
cleanup can stall after tests finish; stop only the two server PIDs printed by that
test run. Do not terminate unrelated Node/Python processes.

Backend tests block external sockets/model construction and cover binding, core
assembly, contracts, failures, history, downloads, origin/session checks and traversal.
Browser acceptance verifies role order, real validation, answer separation, PPT byte
identity and Topic 2 restrictions. `output/p6ui2` stores acceptance evidence.
The next baseline preserves historical artifacts/manifests and adds console source,
UI source/configuration/locks, tests, documentation and acceptance proof; caches,
dependency folders, builds, secrets and transient runs are excluded.
