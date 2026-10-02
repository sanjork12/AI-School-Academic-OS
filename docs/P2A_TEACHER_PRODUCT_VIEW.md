# P2A — Trusted knowledge to teacher product view

P2A implements the Standard deviation **calculation from summary statistics** slice. It reads the protected Q2 and Q3 publications without changing academic records, source verification, governance, publication targets, identities or snapshots. No frontend, generation, model calls, external APIs or `.env` access is introduced.

## Three boundaries

The Trusted Knowledge Layer owns immutable versions, source checks, human decisions, defer governance and publication validity. Its snapshots contain internal evidence graphs and review history; those records are not frontend APIs.

The Product Read Layer checks trust, composes publications, selects this narrowly configured academic slice and translates approved meaning into `TeacherTopicView` (`teacher-topic/2`). The normal payload contains course identity, concept descriptions, student capabilities, task forms, bounded assessment wording, individual marks, separately labelled curriculum wording and a compact trust summary. It contains stable product refs, but no canonical IDs, proposal IDs, source IDs, decision IDs, hashes or review heads.

The future Teacher UI consumes this product model. It must obtain a fresh model through `AcademicProductService.get_topic_view`, not join raw snapshots or treat a saved JSON file as continuing authority. `artifact_kind=teacher_product_read_model` and the validity notice distinguish the demo artifact from a trusted publication.

The backend/operator configures the authoritative database path. A future web endpoint must not accept database files or database paths from a teacher request; a copied historical database cannot know decisions recorded later in its authoritative source.

## Protected inputs and strictly read-only validity

- Q2: `04765fa526fc03ee889f8e0691a23e07de4dcbd5486a779317a928c0809a7070`
- Q3: `4c48326cc3b4e3315118d8dc675764a1cff2d8e0c7d37a2f741bc26d928fe826`

`product_reader.py` opens the existing SQLite database with `mode=ro`, makes one consistent ephemeral in-memory database image and calls the **unchanged `Service.snapshot`** for every requested publication. All original source-file integrity checks still run. Existing stored withdrawal blocks remain effective. Any unusable, missing or corrupt input rejects the whole request; the reader never quietly drops an invalid publication and presents the rest as complete. There is no cross-request cache and no detached JSON input path. A missing database is not created; an unsupported schema is not migrated.

This read adapter is needed because `Service.snapshot` may append withdrawal diagnostics. Such writes occur only in disposable memory here, never in the real database. The image is not rebuilt academic knowledge, a new trusted snapshot, or a publication. Durable governance/withdrawal operations remain the foundation's responsibility. Trust is checked for the current read; a previously saved view does not establish later usability. The database image is consistent, but the product layer does not lock external PDF files across a UI session.

## Meaning and evidence selection

`product_catalog.py` is explicit navigation configuration: this slice selects concept `CON-STAT-SD`, competency `CAN-STAT-SD-CALC` and task condition `TC-SUMMARY-STATISTICS`. These selectors do not contain question IDs or expected answers. All names and descriptions come from the checked published objects, and assessment claims come from published semantic interpretations and approved parsed spans. The model does not infer that every use of the concept is this calculation capability: Q2(c)'s distinct variation interpretation is outside this slice.

The two reviewed examples are June 2025 Q2(b) and June 2023 Q3(b)(ii). Both trace to the same competency and task condition, with one deduplicated concept. Question text uses approved `comparison_context` and `prompt` spans, not a whole PDF page or every statement in shared context. Q3's calculation directive is retained. Marks are taken from each approved parsed part, not inferred from grouped printed totals. Existing extraction cautions are preserved in `reading_notes`. No dataset taxonomy or new context label is invented.

Session, year and paper are separated only when recognized in the approved question label; the complete label is also preserved. Unknown label formats produce null metadata, not inferred dates or paper identities. Filenames are never semantic evidence.

The page title is independent presentation configuration; the concept name and definition are copied from the approved concept: no new textbook definition is generated. The curriculum quotation selector is presentation configuration and must match whitespace-normalized text in a verified **official syllabus** locator attached to that concept. The returned wording is that actual text slice; an absent match produces no quotation and `curriculum_verified=false`. Optional provenance records normalized-text offsets and the locator identity.

**Curriculum wording is not scope equivalence.** The existing scope explicitly remains a candidate association even though its object was reviewed and published. The product preserves that qualification and its explanation. `curriculum.references[].association_status` remains `candidate` where the published candidate scope exists. `curriculum_verified` means the displayed syllabus wording has verified provenance; `curriculum_association_confirmed` remains false under the present candidate/unresolved scope schema. It must not be interpreted as an approved official objective mapping.

## Deterministic composition and conflicts

Every supplied snapshot is checked before composing. Duplicate input IDs are deduplicated. Published objects are merged by their typed identity; different content versions of the same identity produce `CompositionConflict`. Contradictory definitions under an allegedly identical version are also rejected. Review receipt identifiers are not academic definition content. There is no latest-wins rule, name-based identity merge or silent conflict resolution. The check conservatively applies to all overlapping input objects, not only the final display fields.

Assessment evidence is deduplicated by paper-source identity and part identity; both different source questions survive. A differing representation of the same assessment identity is a conflict. Mixed curriculum contexts are rejected. Ordering is explicit: input IDs/object identities sorted, evidence by descending year then session/paper/part/identity, trace identifiers and cautions sorted. Serialized UTF-8 JSON has sorted keys, stable indentation and a trailing LF. It includes no current time, random IDs or database row positions.

Internally, `AcademicProductService.read_topic(...).provenance` supplies checked input IDs, canonical versions and ownership, mapping/parsed-part identities, curriculum excerpt locators and supporting source identities. This separate debug structure proves reuse without exposing governance details in normal teacher presentation. Frontend code must not need it to render the topic.

`source_count` counts unique verified sources in the dependency closure of the selected claims: one syllabus, two question papers and two mark schemes for the combined real slice. It is distinct from `reviewed_example_count=2`. Two examples justify no frequency, trend, difficulty, exam-probability, typical-marks or common-error claims. No confidence percentage is emitted.

## Exclusion safety

The reader never consults staging proposals, pending candidates, oracle files or fixture expectations to construct teacher meaning. The Q3(c)(ii) deferred interpretation is outside the effective publication; it has no teacher evidence item. A shared MS c(ii) locator may exist in the Q3 snapshot for other reviewed claims, but this product does not render that whole locator or its unresolved interpretation. Q2's pending contextual-inference candidate is likewise absent. Only approved interpretations matching the configured canonical slice are rendered.

## API and CLI

```python
from academic_os.product_service import AcademicProductService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS

service = AcademicProductService('var/p0_q2.sqlite3')
view = service.get_topic_view('standard-deviation', PROTECTED_SNAPSHOTS)
frontend_payload = view.model_dump(mode='json')
```

From `D:\AI-School-Academic-OS`:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 teacher-topic standard-deviation
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 teacher-topic standard-deviation --json --output output/p2a_teacher_view/standard_deviation.json
```

Use repeated `--snapshot <ID>` arguments to explicitly select checked inputs. Without them, the CLI uses the two protected IDs above. An existing identical output file is accepted without rewriting; a different file is refused. Choose a fresh output path when the product schema/content changes. An exported product JSON is a reproducible demonstration, not an offline substitute for the trusted status check.

## Verification and limits

```powershell
python -X utf8 -m unittest tests_p0.test_teacher_product -v
python -X utf8 -m unittest discover -v
python -X utf8 -m tests_p0.teacher_product_acceptance
```

Focused tests use read-only protected publications; adversarial revisions/revocations use disposable SQLite copies and TEST ONLY operators. Pure composition tests use explicitly modified copies of already checked payloads to exercise version conflicts, since today's single-current-head store would normally reject an older conflicting snapshot before composition. The private composer is not an alternative trusted input API.

`output/p2a_teacher_view/acceptance.json` records input usability, identity reuse, examples, determinism, before/after row digests/counts and database hash, plus the full suite outcome. The protected missing-PPT test remains unchanged and is reported separately if still the only error.

The current reader copies a small local database into memory; larger deployments may need a foundation-provided side-effect-free read transaction API. This is a local operator/DB ownership boundary, not production authentication. No speculative topic ontology, lesson schema, analytics, frontend or additional subject slice is added.


## P2A.1 contract migration: teacher-topic/1 → teacher-topic/2

This is a Product Contract change only. Academic ontology, publication targets, source/academic/governance decisions and the two protected snapshots retain their identities and bytes. The previous P2A artifacts are archived in `output/p2a_teacher_view/p2a1_baseline/`; the main `standard_deviation.json`, provenance and acceptance artifacts now describe v2.

Repository searches found v1 consumers in the product service, renderer/CLI, tests and documentation, with no production/frontend consumer. Those consumers are intentionally migrated; no indefinite compatibility duplicates are kept. The CLI command and Python service entry points stay the same. A consumer must inspect `schema_version`; v1 is not silently parsed as v2. The CLI output-file guard is unchanged: a different existing artifact is refused. The scoped acceptance builder regenerates the requested v2 artifact; ordinary CLI callers can choose a fresh path.

### Product view identity and academic identity

`identity.view_key=standard-deviation` and `identity.view_type=knowledge_topic` identify a product navigation view. Its configured title currently matches the academic concept label, but these are different entities. A change in a concept's approved display name does not change the view key or implicitly rename the product page. No curriculum taxonomy is inferred.

The Product Layer uses **Capability** for a teacher-facing projection of an Academic Competency. This does not rename the underlying ontology. `capabilities[]` replaces `competencies[]`; each capability has `ref`, `name`, `description`, `concept_refs`, and its own nested `task_forms[]`. The ambiguous top-level task-form array is removed. A capability-to-concept association must be supported by a published concept link and interpretation; its task form must be supported by the published mapping. Missing support is refused rather than guessed.

### Product references and relationships

`product_catalog.PRODUCT_REFS` is a small, explicit product alias registry keyed by typed internal identity:

- `concept-standard-deviation` corresponds internally to `concept:CON-STAT-SD`.
- `capability-standard-deviation-calculate` corresponds internally to `competency:CAN-STAT-SD-CALC`.
- `task-form-summary-statistics` corresponds internally to `task_condition:TC-SUMMARY-STATISTICS`.

The aliases are stable product identifiers, not replacements for canonical identities. They are not generated from current display text, snapshot IDs, definition versions, row order or timestamps. A new canonical identity needs an explicit product alias; unknown identities and alias collisions fail clearly. Alias spelling is a product contract and must not be casually changed when display wording changes.

Assessment evidence now uses `capability_ref` and `task_form_refs`. It no longer duplicates capability/task-form display strings as relationships. The renderer resolves names through the referenced capability and its nested task forms. The schema rejects duplicate entity refs, dangling concept/capability refs and task refs that do not belong to the referenced capability. Both protected questions resolve to the same capability and task-form refs. `provenance.product_refs` retains the corresponding typed canonical key, version and contributing snapshot IDs, outside normal teacher data.

This phase implements only the existing calculation slice and its supported relationships. It does not create additional capabilities or infer prerequisite/teaching relationships. Future capability additions must provide supported relations and explicit non-colliding entity refs.

### Other v2 field migrations

- `curriculum_wording[]` becomes `curriculum.references[]`.
- Display-text `association` becomes machine-readable `association_status` (`candidate` or `unavailable`), with the original `association_note` preserved. The actual combined case remains `candidate`; verified wording does not mean confirmed alignment.
- `reading_notes` stays with each assessment example. Its schema description and CLI label explicitly classify it as evidence/source-quality information, not teaching content, common mistakes or concept explanation. Existing warnings are preserved.
- Assessment labels, dates, paper, question parts, bounded wording and individual marks are unchanged.
- Trust facts and source counts are unchanged; no percentage, score or ranking is introduced.

The v2 normal payload contains neither `competencies[]` nor top-level `task_forms[]`, and evidence contains neither `competency` nor display-name `task_forms`. Consumers resolve product references without joining internal snapshot or governance objects. Contract tests cover independent display renaming, reference stability across both snapshots, relationship support, dangling/colliding refs, preservation of v1 academic text/notes, and explicit rejection of the old schema version. Existing trust checks and composition-conflict policy remain in force.
