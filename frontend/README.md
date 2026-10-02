# Current home page: P6UI.2 local authoring console

P6UI.3A adds a bounded PDF upload/extract/parse workspace. See
[syllabus ingestion](../docs/P6UI3_SYLLABUS_INGESTION.md) for the exact supported
edition, explicit AI boundary, offline replay and current browser tests.

The primary route now requires the localhost Python API and uses real deterministic
Standard Deviation services. See [startup, boundaries and tests](../docs/P6UI2_INTERNAL_AUTHORING_CONSOLE.md).
The browser-only description below documents the retained historical v0.1 demo
components, which are not mounted on the current home page.

---

# Curriculum Intelligence UI Demo v0.1

A five-step, browser-only walkthrough of Pearson Edexcel International GCSE Mathematics A (4MA1), Topic 2 — Equations, formulae and identities.

## Run

Use Node.js 20.9 or later and npm. From `frontend/`:

```sh
npm install
npm run dev
```

Open http://127.0.0.1:3000. Build and lint with:

```sh
npm run build
npm run lint
```

The build produces a static `out/` directory. No Python runtime, API, database, authentication, environment variables, remote fonts, or paid service is required. After building, `npm start` serves only the exported `out/` files at http://127.0.0.1:3000 using a small local static preview server. Production hosting needs no server process.

This workstation has Node but no global npm. A disposable npm CLI was downloaded to the ignored `.tools/package/` directory. Here, the equivalent commands are `node .tools/package/bin/npm-cli.js install`, `node .tools/package/bin/npm-cli.js run dev`, and `node .tools/package/bin/npm-cli.js run build`. This workaround is not needed in a normal Node/npm installation or on Vercel.

## Three separate layers

1. **Source data:** the existing Python `output/` artifacts. Nothing in the frontend writes to them.
2. **Derived view data:** `scripts/prepare-demo.mjs` reads exactly eight named JSON artifacts and creates `src/data/demo.json`. The `CurriculumDemoView` TypeScript interface isolates components from Python schemas. The snapshot is disposable presentation data, never a source of truth.
3. **Local demo state:** React state holds approval, modification, rejection, and file-selection interactions. Refresh or Reset Demo clears these. No persistent storage or network writes are used.

Preparation is explicit and not part of `npm run build`. The checked-in static snapshot makes `frontend/` independently deployable. To refresh it while inside the full repository:

```sh
npm run prepare:data
npm run test:data
```

Sources in `../output/`:

- `topic2_foundation_parsed.json`, `topic2_higher_parsed.json`: official wording, tiers, subtopics, source warnings.
- `topic2_ai_mapping_proposals.json`: original AI recommendation, confidence, reasoning.
- `topic2_ai_consolidation_proposals.json`: consolidation recommendation and reasoning.
- `topic2_scope_metadata_prototype.json`: approved scope descriptions and constraints only.
- `topic2_human_review_decisions.json`: historical decision provenance and approved domain when absent from legacy proposals.
- `topic2_canonical_prototype.json`: bootstrap reference, inspected during preparation.
- `topic2_canonical_promoted.json`: official approved skills and mappings.

Counts are derived: 41 official objectives, 10 approved skills, 13 approved mappings, 13 mapped objectives, 28 unmapped objectives, 2 historical human decisions. The two demo review cases are a replay of already-approved decisions, not two pending audit entries. AI proposal artifacts retain their original pending status.

## Five-step demonstration (3–5 minutes)

1. **Import:** select Use Demo Syllabus. Alternatively browse or drop a PDF to demonstrate local selection. File bytes are not parsed or uploaded. Metadata and subsequent results always refer to the prepared Topic 2 dataset.
2. **Process:** run the approximately 3-second replay. AI suggestions and human decisions have distinct roles. View the real summary.
3. **Curriculum:** explore eight subtopics and both tier sources. Start with Inequalities. Expand Technical details for IDs and mapping evidence; source notes remain contextual and do not become objective evidence.
4. **Review:** approve the inequality-symbol example. Open consolidation to compare Foundation 2.8E and Higher 2.8B: one underlying skill with separate scope. Modify a skill name, domain, or description; reject or approve locally. These are practice actions only.
5. **Approved Graph:** inspect the official skill-to-objective connections. Demo Review Result is separate and cannot change the approved snapshot. Expand the remaining skills. The five downstream cards are future modules, not implemented features.

Use Reset Demo to start again. Workflow navigation also allows direct access to any step.

## Tests

```sh
npm run test:data
# With npm run dev active in another terminal:
npm run test:e2e
```

Data tests require the parent repository's source JSON. Browser tests use Playwright and installed Microsoft Edge (`channel: msedge`). On a machine without Edge, install a Playwright browser and adjust the channel in `playwright.config.ts`. Tests cover the complete workflow, both tiers, empty tier state, original wording, technical details, approve/modify/reject/reset, modal Escape, refresh, PDF selection, mobile overflow, runtime errors, and external requests. Screenshots are written to ignored `test-results/`.

## Vercel

Import the repository, set **Root Directory** to `frontend`, use the Next.js preset, `npm install` (or `npm ci`) and `npm run build`. The static export is `out/`. Alternatively deploy `out/` to any static host. Do not run data preparation on Vercel: the generated JSON is already included. No `D:` path, parent `output/` directory, Python process, backend, or secrets are needed at runtime or normal build time. This task prepares deployment; it does not publish a site.

## Known data issues and boundaries

- Foundation 2.8A contains private-use glyphs in the parsed source. The exact text is displayed with “Source formatting requires verification”; it is never silently repaired. The human-reviewed skill description is displayed separately.
- Legacy AI proposals have no `proposed_subject_domain`. The example displays the historical human-approved domain, with an explicit provenance label; it does not attribute that value to the old AI proposal.
- The scope JSON still contains legacy `difficulty_level` fields although the current schema no longer defines them. The adapter excludes them, without altering source files.
- The graph's legacy top-level `prototype` label says Topic 2.6. UI scope and title come from the actual parsed curriculum, not that stale label.
- Higher 2.4 has no separate objective records and refers to Foundation in its notes. An empty state preserves this distinction.
- Only Topic 2 is demonstrated. There is no real upload processing, persistent review backend, database, authentication, or downstream assessment/mastery implementation.

## Future Python API integration

Replace the static view-model loader with a read-only API returning the same presentation contract. A separately authorized review endpoint should validate and append candidate decisions through the existing decision-log rules, then rebuild and validate the approved graph from baseline plus complete history. Keep authoritative responses distinct from unsaved local UI edits. Do not let components mutate source JSON or automatically approve AI proposals.

## Verification on the implementation workstation

- Dependency installation completed using the local npm CLI; a lockfile is included.
- Production static export succeeded; TypeScript passed.
- ESLint: zero errors and warnings.
- Three data tests passed; two browser scenarios passed on the development server and the production static export (desktop and 390px mobile).
- Original Python engine files and all output artifacts remained byte-identical. Existing 11 decision-log tests passed. Canonical validator: 0 errors, 1 expected unmapped-objectives warning.
- No external browser requests or JavaScript runtime errors were observed in the full walkthrough. Only the named JSON files are copied into presentation data; `.env` is never read or bundled.

To test the production export alongside the dev server, use `node scripts/serve-static.mjs 3001`, then run the browser suite with `DEMO_BASE_URL=http://127.0.0.1:3001` (PowerShell: `$env:DEMO_BASE_URL='http://127.0.0.1:3001'`).
