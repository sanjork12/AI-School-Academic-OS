# Teaching & Assessment Generator Demo v0.1

Teacher-generated teaching/practice material. **Not official Pearson material.**

## Immediate classroom use

Open `Edexcel_9MA0_Statistics_Exploring_Data.pptx`. It contains 24 editable slides, 10 original worked examples (A–J), 24 student checks and speaker-note answers. Suggested pacing is two 55-minute lessons (slides 1–14, then 15–24), followed by a separate assessment. A calculator is required. Review pacing for your class.

Print `Edexcel_9MA0_Statistics_Assessment.pdf`: 48 marks, 55 minutes, eight questions, 21 separately mapped parts, nine pages including instructions. Answers are excluded. Each question has its own page and working space. Use the matching `Edexcel_9MA0_Statistics_Mark_Scheme.pdf` (nine pages) for marking. DOCX versions are editable; the PDFs provide stable print layout. Changing a DOCX does not automatically update the JSON or PDF: edit the source and rebuild to keep the pack consistent.

## CHANGED FILES

Only new files were added. Root files:

- `teaching_assessment_content.py`: original lesson/question content and source references.
- `teaching_assessment_schema.py`: strict isolated demo models.
- `build_teaching_assessment_demo.py`: deterministic offline JSON/report builder.
- `render_teaching_assessment_artifacts.py`: PowerPoint, Word and PDF generation.
- `validate_teaching_assessment_demo.py`: structural, provenance, reference and unchanged-file checks.
- `verify_teaching_assessment_artifacts.py`: artifact/content consistency and file hashes.
- `test_teaching_assessment_demo.py`: 26 focused tests including negative/mutation cases.

All deliverable data and artifacts are in this directory. Private rendering intermediates are under `tmp/teaching-demo/`. No stable schema, canonical graph, Topic 2 output, human review record or existing frontend file was edited. No database, API, environment secret, OpenAI call or automatic promotion is involved.

## GENERATED ARTIFACTS

- `Edexcel_9MA0_Statistics_Exploring_Data.pptx`
- `Edexcel_9MA0_Statistics_Assessment.pdf` and `.docx`
- `Edexcel_9MA0_Statistics_Mark_Scheme.pdf` and `.docx`
- `curriculum_context.json`
- `competency_model.json`
- `teaching_blueprint.json`
- `assessment_blueprint.json`
- `assessment_questions.json` (teacher-side source, includes answers)
- `mark_scheme.json`
- `question_competency_mapping.json`
- `assessment_coverage_report.json`
- `teaching_assessment_alignment.json`
- `pack.json`: validated core snapshot.
- `teachingAssessmentDemo.json`: static teacher-facing presentation model.
- `stable_baseline_sha256.json`: pre-change hashes for 58 protected files.
- `artifact_validation_report.json` and `validation_report.json`: delivery evidence.

Keep the teacher-side JSON and mark scheme separate from the student paper when distributing files to pupils.

## CURRICULUM CONTEXT

Pearson Edexcel **UK A Level Mathematics (9MA0), 2017 qualification**, UK Level 3 / A Level, Statistics / Applied Mathematics. This is not IAL, IGCSE, or the separate A Level Statistics qualification. The unit is **Statistics: Exploring and Summarising Data**.

Sources consulted on 18 September 2026:

- [Pearson Mathematics 2017 qualification page](https://qualifications.pearson.com/en/qualifications/edexcel-a-levels/mathematics-2017.html).
- [Pearson GCE Maths and Further Maths Qualification and Assessment Guide](https://qualifications.pearson.com/content/dam/pdf/A%20Level/Mathematics/2017/Teaching%20and%20learning%20materials/gce-maths-assessment-guide.pdf), page 9, for LDS structure and teaching purpose.
- [Pearson 9MA0/31 June 2023 examiner report](https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/9ma0-31-pef-20230817.pdf), Question 3 discussion, for trace rainfall and limited month coverage.

No local official 9MA0 specification or official LDS workbook was available. The older specification URL could not be retrieved. Therefore no exact official objective IDs or verbatim specification mappings are asserted. Course scope is explicitly teacher-selected and pending subject review. Source-derived LDS facts are separated from original explanations and synthetic practice values. No official question or textbook question is reproduced, and no Pearson logo is used.

The actual LDS covers selected weather stations and dates. **All numerical teaching and assessment datasets in this pack are ILLUSTRATIVE DATA, not official LDS observations.** Official-context facts do not turn fictional station values into official data. To replace examples later, retain station/date/variable/unit and cleaning-policy provenance, recalculate all answers and rebuild derived reports. Students should also work directly with the official workbook during the course.

## COMPETENCY MODEL SUMMARY

18 teaching competencies: **17 candidate canonical competencies**, **one teaching-only grouping** (`GROUP-LDS-PURPOSE`), **zero approved/promoted competencies** and zero reused existing canonical competencies. The current real graph is algebra-focused. All review statuses remain pending.

Generic identities such as `CAN-STAT-MEAN-CALCULATE` have no qualification, stage or difficulty embedded. Context-specific expectations live in separate curriculum scopes. Predicted demand belongs to question parts on a teacher-estimated 1–5 scale, not to curricula or skill identities. The stored question maximum is a derived blueprint summary, not a level of the curriculum.

## TEACHING PPT SUMMARY

24 slides cover fast data-type review, location, grouped means and percentiles, IQR, variance and SD, contextual comparisons, outlier decisions, LDS context, cleaning and applied reasoning. Native tables and one native chart remain editable. Speaker notes include check answers, example explanations, conventions and sources. Examples A–F meet the requested minimum, with G–J adding grouped estimation, summary-statistic SD, weather comparison and outliers.

The raw quartile examples use the explicitly stated median-of-halves convention. Grouped quantiles use position pn and uniform-within-class interpolation. These are declared task conventions, not assertions of a universal software or exam-board quartile algorithm. Variance and SD describe the observations with divisor n.

## ASSESSMENT SUMMARY

48 marks; 55 minutes; eight questions; 21 question parts. Demand generally moves from classification and calculation to interpretation, incomplete weather records and evaluation of a selective deletion. Several parts have multiple competency links, and the mean competency appears in multiple questions.

## MARK SCHEME SUMMARY

Every assessable part has an answer/method, one-mark allocation points, alternatives and interpretation notes. M = method, A = accuracy, B = independent statement. The entire scheme is labelled **TEACHER-GENERATED PRACTICE MARK SCHEME — NOT AN OFFICIAL PEARSON MARK SCHEME**. No grade boundaries or official marking endorsement are claimed.

## ASSESSMENT COVERAGE

Exclusive mark allocation: data types **6 (12.50%)**; location **11 (22.92%)**; spread **11 (22.92%)**; comparison **11 (22.92%)**; LDS/application **9 (18.75%)**. These meet the requested demo target bands. They are not Pearson weightings.

Predicted demand 1–5 receives respectively **2, 17, 14, 9, 6 marks**, across **1, 9, 6, 3, 2 parts**. This is an uncalibrated teacher judgement.

18 competencies taught; **16 assessed (88.89%)**. Two taught competencies are deliberately unassessed in the written test: **mode identification** and **LDS purpose/structure**. Both appear in classroom retrieval checks. “Assessed” here means linked to a part, not proof of mastery.

Every part attributes its marks once to its primary competency and that competency's topic. Supporting competencies receive zero exclusive marks. Inclusive linked marks are exposed separately to show multi-skill involvement and must not be summed. For example, Q8(a) counts under comparison, while calculation of a mean is a supporting competency; this is an explicit blueprint allocation rather than a claim that every mark is uniquely diagnostic of one skill.

## TEACHING ↔ ASSESSMENT ALIGNMENT

`teaching_assessment_alignment.json` links every competency to actual teaching slide IDs, worked-example IDs where present, student-check IDs and assessment part IDs. It records both exclusive and inclusive linked marks. All assessed competencies have teaching and practice references. Alignment is a traceable planning link; teacher review must still assess whether each practice opportunity is sufficient.

## VALIDATION RESULTS

Pack validation checks context isolation, IDs, candidate status, scopes, provenance, section/slide links, assessment links, mark points, totals, coverage targets and consistency of every exported report. Mutating/removing mark scheme, mapping or alignment records is rejected. The static view model is checked against the same source.

Artifact checks cover all slide body text, speaker-note check answers, native tables/chart values, every printed question/answer, PDF page count, non-official notices and DOCX title styling. All 24 slide renders and all pages of the two PDFs and Word previews were reviewed. PPTX package and geometry checks report zero findings and zero warnings. The deck was rendered using Artifact Tool; it was not manually opened in PowerPoint. DOCX QA used installed Word because LibreOffice was unavailable. Artifact generation itself uses python-pptx, python-docx and ReportLab and does not need Microsoft Office.

## TEST RESULTS

26 new focused tests pass. The combined suite has **70 passing tests**: 26 teaching demo, 33 Academic Knowledge v0.2, and 11 Human Review Decision Log tests. Independent numerical checks cover the assessment's principal calculations.

## EXISTING REGRESSION RESULTS

All 58 protected v0.1/v0.2/frontend source/data files retain their pre-change SHA-256 hashes. Academic Knowledge v0.2 validation: zero errors. Scope validation: zero errors, zero warnings. Canonical prototype validation: zero errors, one existing warning for 29 unmapped objectives. This warning is preserved rather than “fixed” by altering old data. The promoted graph also retains its existing 28-unmapped-objective warning.

## FRONTEND DEMO STATUS

The existing frontend was left unchanged. Its files are included in the stable regression boundary, and the immediate classroom pack takes priority. No frontend build was necessary because no frontend file was changed. A complete static teacher-facing view model is supplied here for a future isolated route.

Recommended future UI: curriculum selection (9MA0 only) → topic selection → teaching plan → pack files/24 slides/18 competencies → assessment/48 marks → coverage → teaching-to-assessment alignment. Label actions as static demonstration; do not imply live generation. Keep answers behind teacher access in any later student-facing implementation. No authentication or access-control system is provided by this offline demo.

## KNOWN LIMITATIONS

This is an offline deterministic prototype, not an AI service, a validated exam or a full Statistics specification map. The real LDS workbook is not bundled. Content and difficulty labels are not externally moderated. JSON artefacts and binaries must be rebuilt together after source changes. PDF and Word layouts are intentionally not pixel-identical, but assessed content matches.

## ACADEMIC CONTENT REQUIRING HUMAN REVIEW

Before classroom use, a subject teacher should check the selected 9MA0 scope against the current specification, raw quartile and calculator conventions, the stated trace/missing-data policy, accepted alternatives and suitability of the 55-minute assessment. New canonical candidates remain unapproved; no review decision has been manufactured. Structural/test pass status is distinct from academic approval.

## Rebuild and validate

From the project root, use Python with Pydantic 2 for data and tests:

```powershell
python -X utf8 build_teaching_assessment_demo.py
python -X utf8 validate_teaching_assessment_demo.py
python -X utf8 -m unittest test_teaching_assessment_demo test_academic_knowledge_v02 test_review_decision_log
```

For artifacts, use an environment containing python-pptx, python-docx, ReportLab, pypdf and lxml. The implementation currently uses Windows Arial font files for PDF embedding:

```powershell
python -X utf8 render_teaching_assessment_artifacts.py
python -X utf8 verify_teaching_assessment_artifacts.py
```

On this machine the artifact runtime is `C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. Neither command contacts an API. After content or layout changes, render and inspect the new artifacts again. Do not recreate the stable baseline to conceal changes.
