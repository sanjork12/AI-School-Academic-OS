# P3A — Evidence-backed Learning Specification Core

`learning-specification/1` describes WHAT a downstream product must cover. It
does not prescribe HOW to teach, a lesson sequence, formulas, calculator steps,
prerequisites, difficulty, or student mistakes. The Standard deviation slice
contains three learning requirements, two separate product coverage constraints,
and ten evidence boundaries.

## Contract chain and read safety

Production entry:
`LearningSpecificationService(database).read_topic(topic_key, snapshot_ids)`.
It returns `.view` plus separate internal `.provenance`.

The service first calls `AssessmentIntelligenceService`, which freshly builds
`teacher-topic/2` through `AcademicProductService` and validates the trusted
snapshots and source files. P3A then reads the teacher contract again to retain
qualification/course identity, which P2B does not carry. It requires identical
upstream provenance and matching contract semantics before generating anything.
Inconsistent reads fail explicitly. This is two existing read-only service calls,
not a new raw database reader or independent snapshot composer.

Both upstream contracts and their generators are unchanged. P3A reuses the
existing P2B pure derivation function to verify the input pair; it does not copy
P2B's observation rules. Upstream arrays are compared as unordered collections
while retaining duplicate multiplicity. Output is generated from the normalized
validated pair. No snapshot cache, saved JSON authority, academic decisions,
governance actions, source verification, or database migrations are introduced.

The core `build_learning_specification(teacher, assessment)` is a pure transform
for already validated input, also usable with explicit test fixtures. It cannot
authenticate JSON. Production callers must use the service. As in P2A/P2B,
validity is checked for the current read; saved artifacts are not permanent trust
credentials. Revocation prevents a later read on the same service instance.

## Semantic generation rules

1. A trusted Product concept description gives one `conceptual_understanding`
   requirement. The description is retained exactly rather than expanded.
2. A trusted Product capability description gives one `capability` requirement,
   preserving its Product identity.
3. A capability's nested task form gives one `capability_under_task_form`
   requirement only when reviewed evidence explicitly links that capability and
   task-form ref. It references both Product entities and all matching evidence.

An unassessed nested task form is not silently promoted into the evidence-backed
task-specific requirement set. No rules inspect topic names, years, question
numbers, question wording, expected answers, or Gold Standard files to invent
learning requirements. Source-quality notes remain attached to evidence.

For Standard deviation, these rules retain:

- The measure of dispersion about the mean in the units of observations.
- The ability to calculate standard deviation of a distribution.
- That same capability when using supplied summary statistics, supported by
  June 2025 Q2(b) and June 2023 Q3(b)(ii).

Conceptual basis is shown separately. This projection creates no canonical
competency. Curriculum wording remains verified and its association remains
candidate; product requirements do not declare confirmed curriculum equivalence.

## Coverage policy and boundaries

`coverage_requirements` is separate from `learning_requirements`. It records the
user-authorized `learning-specification/1 coverage policy`, rather than presenting
product governance as a new fact inferred from exam questions:

- For supported assessed capability/task pairs, teaching material must provide
  an aligned assessment connection. Copying a past-paper question is not required.
- Assessment material must declare included Learning Requirement refs and must
  not silently mark unsupported content as covered.

Each coverage constraint lists the relevant learning refs, Product source refs,
and reviewed evidence refs. Stable refs allow future consumers to declare
`covers_learning_requirements` or `assesses_learning_requirements`. P3A does not
implement lesson, question, or PPT coverage validation.

The ten machine-readable boundaries distinguish five inherited P2B limitations
from five current-contract scope limits:

- Frequency is not established.
- Typical marks are not established.
- Difficulty is not calibrated.
- Future exam appearance is not predicted.
- Common student mistakes are not established.
- Prerequisites have not been modelled.
- Teaching sequence has not been established.
- A required calculator/manual method has not been established.
- Formula knowledge/memorisation requirements have not been established.
- Not every possible task form is automatically included.

Boundary statements do not become positive learning requirements. In particular,
Σx, Σx², formulas, calculator procedures and mathematical prerequisites are not
generated from question wording or general knowledge. Display grouping/order is
not a recommended instructional sequence.

## Stable identities and traceability

`lr-`, `cr-`, and `eb-` refs use SHA-256 over canonical JSON containing the awarding
body, qualification, specification code, upstream view key, semantic role/code,
and sorted source refs. They are Learning Contract identities. Display wording,
marks, question years/numbers, snapshot versions, current time and random values
do not determine Learning Requirement IDs. A revised description with the same
source identity retains its ref; validity still depends on a fresh service read.

Normal output uses Product refs and P2B evidence refs. Internal provenance links
each Learning Requirement to Product concept/capability/task refs, then inherited
canonical identities, content versions, snapshots and evidence traces. No normal
consumer needs canonical IDs. Coverage reference checks in the schema validate
internal links only; they are not future product validators.

## Human Gold Standard

`tests_p0/fixtures/learning_standard_deviation_gold.json` is an acceptance oracle
transcribed from the user's supplied expectations. It records three LR, two CR
and ten EB semantic expectations. Human-readable oracle IDs such as `LR-SD-01`
map to generated refs in the acceptance report. Production neither reads this
file nor contains those IDs. Tests disable file reads around the pure core and
exercise unrelated TEST-only concepts, capabilities, task forms and question
coordinates to verify generation by role rather than fixture branching.

## CLI and artifacts

From `D:\AI-School-Academic-OS`:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 learning-specification standard-deviation
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 learning-specification standard-deviation --json
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 learning-specification standard-deviation --json --output output/p3a_learning_specification/standard_deviation.json
```

The protected Q2/Q3 pair is the default; `--snapshot` can be repeated. The CLI
uses the existing output protection: a differing existing file is not overwritten.
Choose another path when exporting changed content. Importing core modules has
no file writes or external calls. No paid models, APIs, or new frontend are used.

Outputs are under `output/p3a_learning_specification/`: normal JSON, separate
`provenance.json`, `acceptance.json`, protected before-state and test logs.

## Verification

```powershell
python -X utf8 -m unittest tests_p0.test_learning_specification -v
python -X utf8 -m unittest discover -v *> output/p3a_learning_specification/full-suite.txt
python -X utf8 -m tests_p0.learning_specification_acceptance
```

Acceptance checks frozen upstream file hashes and byte-identical fresh outputs,
real database byte/table hashes and review/request/governance/snapshot counts,
protected source hashes, both snapshots' usability, Gold Standard meaning,
repeated output and reversed snapshot/evidence order. Governance remains in the
existing immutable requests journal. No real approval is created for testing.

The known missing `AI_Academic_Operating_System_Brainstorm_CN.pptx` integrity error
remains reported separately; its original test and pinned hash are preserved.
