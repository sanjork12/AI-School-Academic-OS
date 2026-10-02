# P5C: Profiled content validation

P5C adds a read-only, deterministic composition gate with report schema
`profiled-content-validation/1`. It does not change P5B candidates or grant academic
approval. A P5B package retains its frozen `ready_for_rendering=false`; the new
P5C report independently expresses current renderer eligibility.

## Run

From the repository root:

```powershell
python -m academic_os --db var/p0_q2.sqlite3 validate-profiled-content standard-deviation --output-dir output/p5c_profiled_validation
python -m unittest tests_p0.test_profiled_validation tests_p0.test_profiled_content tests_p0.test_lesson_profiles tests_p0.test_content_validation -v
python -m tests_p0.profiled_validation_acceptance
```

The CLI reads the current trusted chain, revalidates upstream inputs, and returns
zero only when both profiles are ready. JSON exports are inspection artifacts,
not approval credentials. Identical exports are idempotent; different existing
exports are rejected. Use a new directory for changed input versions.

## Boundaries and policy

`profiled_content_validation.py` is the pure composition validator;
`profiled_validation_models.py` defines its report;
`profiled_validation_service.py` supplies current read-only upstream inputs and
checks that their provenance agrees. Future renderer/API integrations must use
this service and the exact bound content versions, refreshing before rendering.
The pure function alone cannot establish source trust from arbitrary JSON.

Role population and density use valid mapped content, not candidate flags, counts,
titles or stored mathematical results. Reuse requires the current P4B result,
original object identity and full question/solution/formula dependency hashes.
New items use the existing deterministic provider's bounded content contract and
the existing mathematical verifier. All six new numerical items are recomputed.
This does not claim general semantic validation of arbitrary authored language.
Questions and solutions remain separate. Raw-data demonstration remains an
instructional example, not a newly supported assessed task form.

Current `lesson-profile/1` has no mandatory-target field. Minimum counts are hard
requirements; targets above minimum are preferred. Unknown schema or additional
policy fields fail closed. A target equal to its minimum is necessarily hard.
For Standard Lesson independent practice, two valid items satisfy minimum=2;
target=3 remains unmet with a warning. The isolated Case C test removes the new
third question, its solution and their mapping references, retaining the two
verified reused items. Readiness remains true. Any explicitly unresolved required
role still blocks readiness, even when its content count meets minimum.

Reports include role/content coverage, aggregate learning and original coverage
requirements, scope fingerprint checks, boundary checks, numerical verification,
violations, warnings and bound input hashes. Focused Review has 9 populated roles;
Standard Lesson has 15 including orientation framing (14 substantive roles).
Both current complete packages meet minimum and preferred target densities.

## Verification scope

The baseline runs the 45 P5B tests. P5C adds 50 isolated tests, including required
Cases A–F, numeric corruption, stale bindings, unknown references, unsupported
claims, scope expansion, unresolved roles, spoofed flags, read-only CLI behavior
and immutable exports. The final related regression suite contains 202 tests.
`output/p5c_profiled_validation/acceptance.json` records executed results and
checks the pre-change database state and protected file hashes.
The delivered final run is recorded in `verified-tests.txt`. Acceptance records
bind the exact captured logs; a later test run has different elapsed-time text,
so retain the delivered logs when reproducing the acceptance evidence.

No presentations, academic reviews, governance decisions, snapshots, model calls,
student mastery estimates or quality scores are created. Duration remains planning
guidance, not a guaranteed classroom runtime. The whole repository test suite is
not part of this run; results are limited to the named related suites.
