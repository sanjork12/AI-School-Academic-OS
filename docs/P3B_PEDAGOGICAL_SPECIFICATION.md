# P3B — Pedagogical Specification Candidate

`pedagogical-specification/1` describes how the included learning MAY be taught
and checked. The artifact is always `candidate`. It does not change academic
meaning, add Learning Requirements, approve teaching content, or publish a lesson.

## Read path and frozen contracts

`PedagogicalSpecificationService(database).read_topic(topic_key, snapshot_ids)`
calls the current `LearningSpecificationService` on every request. That service
retains the P2A → P2B → P3A chain, including source and snapshot validation.
P3B does not read raw database objects, parse PDFs, or compose snapshots itself.
All three upstream schemas and generator files are unchanged. Saved JSON is an
artifact, not authority; a new read refreshes upstream validity, and revocation
blocks the next request. P3B writes no trusted database state.

`build_pedagogical_specification(learning)` is the pure deterministic transform
for already validated input and isolated tests. It does not authenticate arbitrary
JSON. No model/API calls, .env reads, embeddings or web searches are involved.

## Candidate contract

The contract contains identity, candidate status, a source-learning projection,
teaching blocks, instructional content slots, planned coverage map, ten inherited
boundaries, generator constraints and a clear trust boundary.

The source-learning projection retains all three Learning Requirements, both
Coverage Requirements and all ten boundaries without changing their content or
refs. Collections have deterministic ref ordering; this does not change meaning
or establish a teaching order. Evidence is represented by P2B refs, assessment
coordinates, capability/task refs and original source-quality notes. It deliberately
omits question wording: linking an assessment structure does not require copying
a Pearson question into a worked example.

## Five pedagogical roles

- `conceptual_meaning`: carries the exact conceptual requirement as required
  content. A visual comparison illustrating the cited meaning is recommended.
  Context, data and visual representation remain flexible.
- `calculation_method`: requires a valid instructional method for the capability.
  Its method slot is unfilled candidate content; no formula is invented.
- `supported_task_form`: carries the task-specific requirement exactly, including
  “From summary statistics”. The block title is generic; no display-string parsing
  or matching is used to infer task identity.
- `worked_assessment_connection`: covers the capability, task-specific requirement
  and teaching-assessment coverage constraint. It requires at least one aligned
  worked-example design slot, not a generated question.
- `practice_learning_check`: covers the relevant capability and task-specific
  requirements plus the assessment-alignment constraint. It requires at least one
  learning-check design. The slot declares `assesses_learning_requirement_refs`.

These roles are generated from Learning/Coverage Requirement types and source-ref
relationships, not topic names, years, question numbers or fixture IDs. The policy
is intentionally scoped to this first calculation-oriented vertical slice; it is
not a universal pedagogy engine for every capability type.

## Required, recommended, flexible

Every constraint has a literal machine-readable level. `required` protects
academic meaning, coverage and boundaries and states necessary design obligations.
`recommended` includes visual support and a supported/guided-to-independent
progression. Neither is promoted to academic truth or a Learning Requirement.
`flexible` includes method presentation, original example contexts and values,
visual styles, slide layouts, question counts and practice formats.

There is no numeric confidence, importance or freedom score. A fixed sequence of
guided practice → independent practice → exit ticket is not required. Block list
order is a stable display order, not a mandatory lesson sequence.

## Instructional content and evidence limits

Four `candidate_slot` objects describe a calculation method, task inputs, worked
example and learning check. They carry supporting Learning/Product refs and
reviewed evidence refs. `formula_memorisation_required` is always false.

The frozen upstream contract supplies no exact calculation formula or structured
n/Σx/Σx² input excerpt. P3B therefore leaves the method and input slots unfilled;
it does not infer formulas from general knowledge or reconstruct notation from
damaged glyphs. Original extraction warnings remain visible. These slots are
pedagogical support only, not new prerequisites, competencies or learning outcomes.

No common mistakes, prerequisite relationships, calibrated difficulty, frequency
claims, calculation button sequences or exam predictions are added. All ten P3A
boundaries remain in force, even where a pedagogical recommendation might otherwise
tempt a generator to infer new academic truth.

## Planned coverage and traceability

`coverage_map.status` is `planned_coverage`. It maps exact upstream LR and CR refs
to block refs. Internal model checks ensure the map matches the blocks and every
included requirement has intended coverage. This is reference integrity checking,
not a Lesson/PPT/Question Validator and not evidence of sufficient teaching content.
Unfilled slots make that distinction explicit.

Block and content refs hash the course/view identity, pedagogical role and sorted
Learning Requirement refs. They are distinct from academic and Learning identities
and independent of labels, current time, random UUIDs or mutable statement text.
Separate provenance links blocks → Learning Requirements → Product identities →
canonical identities and reviewed snapshots/evidence. Normal payloads do not expose
canonical IDs or require the frontend to interpret them.

The Gold Standard at
`tests_p0/fixtures/pedagogical_standard_deviation_gold.json` is acceptance-only.
Tests cover its five roles, coverage and levels; production does not read it.
Tests also substitute unrelated TEST-only labels and disable file reads around
the pure transform to detect fixture coupling.

## Run and validate

From `D:\AI-School-Academic-OS`:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 pedagogical-specification standard-deviation
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 pedagogical-specification standard-deviation --json
python -X utf8 -m unittest tests_p0.test_pedagogical_specification -v
python -X utf8 -m unittest discover -v *> output/p3b_pedagogical_specification/full-suite.txt
python -X utf8 -m tests_p0.pedagogical_specification_acceptance
```

The protected Q2/Q3 snapshots are the default; `--snapshot` can be repeated.
`--output` uses the existing CLI guard: differing existing files are not replaced.
Normal JSON, separate provenance, acceptance report, before-state and logs live in
`output/p3b_pedagogical_specification/`.

Acceptance checks upstream hashes, current P3A output equality, preserved 3/2/10
content, Gold Standard relationships, deterministic output, database/table hashes,
review/request/governance/snapshot counts, source pins and snapshot usability.
No academic/source/governance decision or snapshot is created. The known missing
`AI_Academic_Operating_System_Brainstorm_CN.pptx` remains the original protected-file
test error; neither its pinned hash nor test is weakened.
