# P2B — Evidence-backed Assessment Intelligence

P2B adds `assessment-intelligence/1` downstream of frozen `teacher-topic/2`.
It reads Standard deviation for Pearson Edexcel A Level Mathematics 9MA0
Statistics. No ontology, source, locator, review, governance, publication,
snapshot, or upstream contract migration is involved.

## Read path and trust

`AssessmentIntelligenceService(database).read_topic(topic_key, snapshot_ids)`
calls `AcademicProductService.read_topic` on every request. P2A performs source
and snapshot validity checks and composition using its existing read-only
database adapter. P2B does not query raw objects or repeat that composition.
Revocation prevents subsequent reads, including on the same service instance.

The return value contains `.view` and separate internal `.provenance`.
`_derive` is an internal pure comparison function, also used with explicitly
labelled test fixtures. It cannot authenticate JSON. Production has no saved
teacher-JSON input option. Flags in arbitrary JSON do not provide trust.
Saved P2B JSON is a derived read artifact, not a snapshot or decision; consumers
must refresh through the service rather than treat the file as permanently valid.

## Contract

- `identity`: upstream view key/title, downstream `assessment_intelligence` type.
- `assessment_focus`: upstream concepts and capabilities, their Product refs and
  nested task forms. Names and descriptions retain approved meaning.
- `reviewed_examples`: all upstream examples, with exact wording, marks, refs and
  source-quality notes, plus downstream example identity and epistemic level.
- `observed_patterns`: deterministic comparisons with `evidence_refs`, counts,
  and explicit `derived_observation` level.
- `evidence_summary`: count and shared capability/task-form/wording observations.
- `limitations`: machine-readable limits on frequency, typical marks, difficulty,
  predictions, student errors and context classification.
- `curriculum`: unchanged candidate/unavailable association semantics.
- `trust_summary`: fresh upstream validation, analytics disabled, original upstream
  trust facts and validity notice. No numeric trust score is introduced.

Observed evidence is level 1. Comparisons are level 2. P2B does not produce level 3
generalising analytics. It has no model calls, difficulty estimation, frequency
statistics, generation, student modelling, or new frontend.

## Comparison rules

With at least two examples, shared capability requires the same capability ref
for all examples. Shared task-form observations use the intersection of their
task-form refs. Shared marks requires the same known mark value for all examples.
Unknown marks do not become zero. Single or empty evidence sets produce no
comparison patterns. Every statement is bounded to reviewed examples.

The current two examples both carry 2 marks. This does not establish typical
marks. Their shared summary-statistics task form does not establish how Edexcel
usually assesses the topic. Their presence does not establish frequency.

Different whitespace-normalized wording supports `distinct_question_wording`.
It does **not** establish different semantic contexts. Since the frozen contract
does not provide structured context, P2B deliberately omits
`different_question_context` and sports/weather classifications. This conservative
choice needs no upstream change. Notes about defective formula extraction remain
evidence/source-quality notes and never become student errors or difficulty.

## Stable identities and provenance

Example refs are `assessment-example-` plus SHA-256 of a canonical JSON array:
awarding body, qualification, specification code, year, session, paper, question
part. These structured assessment coordinates are available in teacher-topic/2.
Wording, display labels, marks, array position, current time, snapshot versions
and random identifiers do not participate. Missing coordinates or duplicate
coordinates fail explicitly rather than guessing or merging potentially different
evidence. Distinct evidence rows for the same question would require an explicit
future identity policy; the current slice has one row per question part.

Existing concept/capability/task Product refs are preserved. Canonical IDs remain
in separate provenance inherited from P2A. Example refs map to upstream evidence
traces; each pattern lists the evidence refs it compared. Normal teacher output
contains no canonical IDs or snapshot IDs. Output ordering is deterministic,
including when evidence, nested refs, notes, or snapshot input order changes.

## Run

From `D:\AI-School-Academic-OS`:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 assessment-intelligence standard-deviation
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 assessment-intelligence standard-deviation --json
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 assessment-intelligence standard-deviation --json --output output/p2b_assessment_intelligence/standard_deviation.json
```

The protected Q2/Q3 snapshot pair is the default. `--snapshot` can be repeated.
Output creation follows the existing CLI guard: identical existing output is
accepted; a different existing file is not overwritten. Choose a new path when
exporting a changed view.

The reviewed examples remain June 2025 9MA0/31 Q2(b) and June 2023 9MA0/31
Q3(b)(ii). Q3(c)(ii), pending contextual proposals and deferred unresolved
interpretations stay outside the product. Curriculum wording is verified while
its canonical association remains candidate.

## Verification and outputs

```powershell
python -X utf8 -m unittest tests_p0.test_assessment_intelligence -v
python -X utf8 -m unittest discover -v *> output/p2b_assessment_intelligence/full-suite.txt
python -X utf8 -m tests_p0.assessment_intelligence_acceptance
```

The acceptance command requires the completed full-suite log and records real
database byte hash, table digests, review/request/governance/snapshot counts,
protected snapshot usability, frozen upstream JSON equality, deterministic output,
and test results. Governance events reside in the immutable requests journal and
are counted by `publication_governance/1` record type. No approvals are added.

Output folder: `output/p2b_assessment_intelligence/`:
`standard_deviation.json`, `provenance.json`, `acceptance.json`, `before.json`,
and test logs. P2A artifacts remain untouched.

The existing missing `AI_Academic_Operating_System_Brainstorm_CN.pptx` integrity
error is reported separately; its test and pinned hash are not weakened or skipped.
