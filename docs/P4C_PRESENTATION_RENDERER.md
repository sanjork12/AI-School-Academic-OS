# P4C — Validated content to a classroom presentation

## Result and boundaries

The Standard Deviation profile produces an English, editable, 16:9, 11-slide student PPTX from the current P4A package only after the live P4B gate passes. Four practice/check solutions are copied without alteration to a separate teacher sidecar; the worked example solution is visible on slide 6. No approvals, governance decisions, snapshots, original sources, Gold content or upstream outputs are written. No model, network or `.env` access is used.

This is a presentation adapter, not another academic content author or validator. P4B remains responsible for mathematics and academic boundaries. The layout layer converts the three existing Learning Requirement types into the requested student goal wording, renders supplied formula ASTs, substitutes supplied question inputs without evaluating answers, and positions the existing visual dataset on one common scale. It does not infer new formulae or teaching claims.

## Modules and contract compatibility

- `academic_os/presentation_models.py`: additive `presentation-manifest/1` and `artifact-render-validation/1` contracts; no upstream schema changes.
- `academic_os/presentation_manifest.py`: deterministic 11-slide profile, stable object references, visibility, coverage and current input hashes. Unknown or altered manifest mappings fail closed.
- `academic_os/presentation_layout.py`: mechanical reference resolution into transient editable drawing instructions. Source references remain internal.
- `academic_os/presentation_renderer.mjs`: installed Artifact Tool backend and finalization; editable text and native shapes, including ten data points. It makes no academic selection.
- `academic_os/presentation_validation.py`: reads the actual PPTX ZIP/XML and compares text, symbols, shape identity/order, dimensions, positions, fonts, colours, visibility and teacher-answer separation with the validated plan.
- `academic_os/presentation_service.py`: reads fresh upstream services, compares their provenance, invokes gates/backend, validates final bytes and publishes the artifact last. Existing output is reused only after live upstream and actual artifact checks, including its receipt.
- `academic_os/cli.py`: additive `render-presentation` command before the writable Store branch.

The public service/CLI is the trust boundary. Pure manifest/layout functions accept already obtained typed data; they do not authenticate caller-supplied JSON. Do not expose the internal JS drawing-plan interface directly as a trusted API. A future API should invoke `PresentationService`, retain the live gate, and return the manifest, artifact receipt and output paths.

## Reproduce

From `D:\AI-School-Academic-OS`:

```powershell
python -m academic_os --db var/p0_q2.sqlite3 render-presentation standard-deviation --output-dir output/p4c_presentation
python -m unittest tests_p0.test_presentation -v
python -m unittest discover -v
python -m tests_p0.presentation_acceptance
```

Protected Q2/Q3 snapshots are the command's defaults. Explicit `--snapshot` arguments are repeatable. For a fresh render use a new output directory. Existing final artifacts are never silently replaced. An interrupted partial output fails closed; retry in a new directory.

The supplied environment uses Node and `@oai/artifact-tool` with the presentation skill's finalizer and bundled Python. Runtime discovery is local only. Overrides: `P4C_NODE`, `RUNTIME_NODE_MODULES`, `P4C_PYTHON`, `P4C_SKILL_DIR`. Missing dependencies cause an explanatory failure; no automatic installation or alternate renderer occurs.

## Outputs

- `output/p4c_presentation/student/Standard_Deviation.pptx`: student-facing deck.
- `presentation_manifest.json`: stable references and visibility rules, not a duplicated teaching package.
- `teacher_solutions.json`: four teacher-only source solution records, bound to the authored package hash. Do not distribute this with the student deck.
- `artifact_render_validation.json`: actual PPTX preservation receipt and hashes.
- `provenance.json`: current upstream provenance and private build location.
- `.build/render-speu6e3e/toolkit-validation.json`: finalization checks.
- `.build/render-speu6e3e/preview/slide-01.png` through `slide-11.png`: previews imported from the final PPTX. All 11 were individually visually inspected; no clipped content or exposed practice/check answers were observed.
- `before.json`, test logs and `acceptance.json`: baseline/protection evidence and test results.

Slide order: title/goals, meaning, spread comparison, five-step method, summary formula, worked example, two practices, concept check, calculation check, summary. Student slides carry neither source identifiers nor hashes nor review/debug fields.

## Limits

Validation proves preservation within this restricted editable-shape profile, not pedagogical effectiveness, student understanding, aesthetic quality, complete accessibility or teacher preference. There is no quality score. Preview inspection used Artifact Tool's import/render, not native Microsoft PowerPoint execution. Formulae use editable Cambria Math text, explicit parentheses, roots, superscripts and slash fractions; they are not native Office equation objects.

Manifest and layout selection are deterministic. A repeat into the same validated directory reuses identical PPTX bytes. Fresh exports may differ in library-generated package identifiers/metadata; byte-for-byte reproducibility across fresh exports is not claimed.

The initial P4A/P4B baseline was 95 passing tests. P4C adds 43 passing tests. Full-suite results are recorded separately without changing legacy pins: the known historical `AI_Academic_Operating_System_Brainstorm_CN.pptx` is absent, so its preservation test remains an error. Historical data is not recreated to hide this error.
