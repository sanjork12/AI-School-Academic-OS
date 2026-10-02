# P5D profile-aware presentations

P5D extends P4C.1 into two English student decks for Standard deviation. It
consumes current P5B content after current P5C validation. It creates no academic
or pedagogical content, reviews, governance decisions or trusted snapshots.

## Run from the project root

```powershell
python -m academic_os --db var/p0_q2.sqlite3 render-profiled-presentations standard-deviation --output-dir output/p5d_profiled_presentation
python -m unittest tests_p0.test_profile_presentation -v
python -m tests_p0.profile_presentation_acceptance
```

The CLI accepts optional repeated `--snapshot` identifiers. The default is the
protected Q2/Q3 pair. Both profiles must pass the current service gate and scope
comparison before output work starts. Saved `ready_for_rendering=true` JSON is
not a credential. If any upstream input has changed, a stale manifest or artifact
is rejected. Existing matching output is revalidated and reused without rewriting
its bytes. Conflicting or partial public output requires a new directory.

## Implementation and compatibility

`academic_os/profile_presentation.py` extends the existing models into
`presentation-manifest/2`: the existing slide/content/solution fields retain their
meaning, with profile identity, target duration, P5C version bindings, role refs,
student-visible refs and layout variants added explicitly. No frozen v1 schema
or old P4C/P4C.1 output changes. The pure adapter is not a source-trust authority.

`profile_presentation_layout.py` reuses P4C.1 `Components` and `classroom_plan`
for all existing content. Its extra grammars resolve quick retrieval, raw-data
modelling, guided practice and exit-check fields directly from validated P5B
objects. Labels use a closed allowlist. Formula ASTs, numbers, wording, scaffolds
and solution values come from upstream; the renderer performs no answer arithmetic.

`profile_presentation_service.py` reads the live service chain, compares provenance,
recomputes the P5C gate, checks cross-profile scope, renders in a private build
directory and validates final OOXML before writing public output. The small
`profile_presentation_renderer.mjs` uses the same Artifact Tool shape backend and
finalizer as P4C, without the old fixed 11-slide constraint. It adds no prose.

`profile_presentation_validation.py` re-resolves the expected manifest/layout and
inspects actual finalized PPTX shapes, text, geometry, fonts, notes and object
order. Exact region-aware question/scaffold comparison catches inserted answers
without treating every appearance of a common number as a leak. Teacher solutions
are separate profile-keyed sidecars retaining the actual upstream solution objects,
item refs, role refs and visibility. Worked solutions are intentionally visible.

## Current result

Focused Review has 11 slides: opening, its nine substantive roles and closure.
Standard Lesson has 19: opening, nine reused content blocks, seven new content
items, an extra page for the two-part exit check, and closure. SL-12's three
independent items each get a page. SL-15 maps to concept retrieval, calculation
retrieval and the learning summary. Slide count follows these rules and current
content, not profile minutes or an assigned count.

Both decks use the same three learning requirements, two original coverage
requirements, assessed task-form scope, evidence boundaries and academic scope
fingerprint. The raw-data example remains instructional modelling only. Profile
labels show planning targets, not promised classroom runtime or difficulty.

The isolated minimum-only case removes the third independent item and its
solution/mapping. A fresh P5C report accepts the two remaining valid items, and
P5D produces one fewer manifest page, reports target attainment false internally,
and invents no replacement. Required unresolved roles still prevent rendering.

## Outputs and checks

Each profile directory contains the student PPTX, presentation manifest,
teacher solution JSON, artifact validation and current provenance. `.build`
contains finalizer receipts and PNG previews re-imported from finalized PPTX.
Every delivered page was individually inspected at full size. The old P4C.1
worked-example preview was also compared against the new reuse rendering.

Baseline: 137 P5C/P4C/P4C.1 tests. New tests exercise gates, scope, role/child
coverage, minimum-versus-target behavior, semantic reuse, teacher separation,
scaffolds, deterministic manifests and actual PPTX answer/number/object mutation.
Final counts and hashes are in `output/p5d_profiled_presentation/acceptance.json`.
The whole repository suite is not run. Visual checks use Artifact Tool imports;
native PowerPoint rendering is not claimed. Editable text and diagram marks are
native shapes, not slide-sized screenshots. Rendering eligibility does not grant
academic publication or certify pedagogical effectiveness.
