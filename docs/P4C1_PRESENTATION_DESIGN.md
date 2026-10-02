# P4C.1 — Classroom presentation design

P4C.1 adds the `standard-deviation-classroom/2` design profile while retaining
`presentation-manifest/1` and `artifact-render-validation/1`. The classic profile
remains the default. Both profiles use the same live P4B gate, P4A content refs,
Learning Requirement refs, coverage, solution visibility and input hashes.
Only the profile identifier and renderer layout intent differ in the manifest.

## Run

```powershell
python -m academic_os --db var/p0_q2.sqlite3 render-presentation standard-deviation --design classroom-v2 --output-dir output/p4c1_presentation_design
python -m unittest tests_p0.test_presentation_design tests_p0.test_presentation tests_p0.test_authored_teaching tests_p0.test_content_validation -v
python -m tests_p0.presentation_design_acceptance
```

A new output directory creates the v2 deck; rerunning against the same output
validates current upstream inputs and actual PPTX bytes before reusing them.
The original `output/p4c_presentation` tree, including its acceptance and test
logs, is preserved. No source, approval, snapshot or upstream contract changed.
No model or paid API is called.

## Implementation

`academic_os/presentation_design.py` supplies reusable deterministic components:
lesson opening, concept statement, dot plot, process flow, input cards, formula
panel, worked stage, practice question, learning check, working space and summary
checklist. It defines one blue colour family with neutral tones and eight
explicit typography roles. Arial and Cambria Math are installed locally; no fonts
are bundled. Text, cards, data points, lines and formulas remain editable.

`presentation_manifest.py` selects the bounded profile without adding a second
content store. `presentation_layout.py` dispatches to the new components after
validating the manifest. `presentation_service.py` and the CLI add the opt-in
design argument and distinct output filename. The existing JS renderer and
independent actual-PPTX validator are reused.

Each text element is classified as upstream_content, renderer_label, footer or
slide_number. Substantive text retains its source reference and field path.
Renderer labels come from a small closed allowlist; unsupported label text raises
an error. No new academic statements, examples, answers, timing or exam advice
are authored by the renderer.

The dot plot shares a scale from 2 to 18 and positions points proportionally.
Both means are sourced as 10. Formula panels render the validated AST through the
existing notation converter. The four worked stages preserve all original
solution steps, with 3.16 emphasised. The upstream simplification is
`population variance = 110 - (10)^2 = 10`; the renderer does not invent a separate
`110 - 100` intermediate step. It only changes notation and grouping.

Practice and check answers remain in the byte-identical teacher sidecar. The
student deck contains no answer notes. Blank working regions are intentional.

## Outputs and evidence

Under `output/p4c1_presentation_design`:

- `Standard_Deviation_v2.pptx`
- `presentation_manifest.json`
- `artifact_render_validation.json`
- `teacher_solutions.json` (teacher only)
- `provenance.json`
- `montage.png`
- `acceptance.json`, `before.json`, test and CLI logs

The final imported-PPTX previews and finalizer receipt are under the private build
directory recorded in `provenance.json` (`.build/render-fxcjc93j/preview`). All 11
final slides and the montage were visually inspected. Text/formula readability,
spacing, footer alignment, numerical plot scale and question/answer separation
were checked. The actual PPTX preservation gate and package finalizer passed.

Native PowerPoint was detected at the registered Office 15 application path, but
native execution/rendering was not performed. Preview verification uses Artifact
Tool, not Microsoft PowerPoint. Editable math uses Unicode and explicit
parenthesised fractions, not Office equation objects. Structural and visual
checks are not evidence of learning effectiveness, accessibility perfection or
teacher preference; no presentation quality score is produced.

## Tests

Baseline: 43 existing P4C tests passed before changes.
Targeted regression: 44 new design tests + 43 P4C + 38 P4A + 57 P4B = 182 tests.
See `focused-tests.txt` and `acceptance.json` for executed results. The entire
repository suite was not rerun for this presentation-only change. The previous
P4C full-suite result (725 passed, one missing historical PPTX error) is preserved
as historical evidence, not claimed as a P4C.1 execution.
