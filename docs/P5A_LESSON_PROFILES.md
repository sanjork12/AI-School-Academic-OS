# P5A — Lesson profiles and pedagogical density

P5A is a new downstream product/pedagogical planning layer. It does not change
learning scope, trusted academic state, the P3B base skeleton, authored content
or either presentation. It makes no model/API calls and reads no PPTX to infer
a profile.

## Contracts and entry points

- `academic_os/lesson_profile_models.py`: strict, extra-field-forbidden models
  for `lesson-profile/1`, `profiled-pedagogical-specification/1` and a small
  `profiled-pedagogical-validation/1` result.
- `academic_os/lesson_profiles.py`: two deterministic Gold product configurations
  directly specified by the user. They are design policies, not academic approval
  records or fabricated human reviews. Only these two bounded configurations are
  supported in v1.
- `academic_os/profiled_pedagogy.py`: pure transformation, role lineage, scope
  fingerprint and fail-closed profile validation. It reuses the current P3C
  validator and verifies all declared fields against the supported profile design.
- `academic_os/lesson_profile_service.py`: obtains one fresh trusted Learning
  Specification, builds the unchanged P3B base through its existing core, checks
  P3C and derives both profiles from those same inputs. Source consistency and
  snapshot usability remain enforced by the upstream live service.
- `academic_os/cli.py`: additive read-only commands, before the writable Store path.

No frozen model or renderer module was modified. Profile-specific role references
are new pedagogical identities; Learning Requirement and Coverage Requirement
references are never cloned. Role origin describes pedagogical design lineage,
not the epistemic origin of future authored content.

## Reproduce

From `D:\AI-School-Academic-OS`:

```powershell
python -m academic_os lesson-profiles
python -m academic_os --db var/p0_q2.sqlite3 profile-pedagogy standard-deviation --output-dir output/p5a_lesson_profiles
python -m unittest tests_p0.test_lesson_profiles tests_p0.test_learning_specification tests_p0.test_pedagogical_specification tests_p0.test_pedagogical_validation -v
python -m tests_p0.lesson_profile_acceptance
```

The CLI uses the protected Q2 and Q3 snapshots by default, with repeatable
`--snapshot` overrides. Without `--output-dir`, it prints the two profiled
specifications. Repeated exports are byte-identical and idempotent. A differing
existing output is rejected before writing; use a new output directory for a new
version. Pure transformation/validation functions do not authenticate JSON;
production consumers must enter through `LessonProfileService`.

## Density, timing and coverage

Focused Review targets 25 minutes (20–30), with 9 substantive roles. Standard
Lesson targets 60 minutes (50–60), with exactly SL-01 through SL-15: 15 pedagogical
roles, of which orientation is framing and 14 are substantive. The independent
practice set is one role with minimum 2 and target 3 items. Consequently Standard
Lesson plans 15 minimum / 16 target substantive content items. Role counts, item
counts and eventual slide counts are distinct.

Both plans preserve all three actual LR refs, both existing Coverage Requirement
refs and every Evidence Boundary. The scope fingerprint hashes definitions,
conceptual basis, curriculum, supported product refs and assessment/boundary
content. It includes no duration, profile name, role count or layout. The two
profiles also bind to identical complete learning/base-pedagogy hashes.

Phase ranges are suggestions, not an additive timetable or guaranteed classroom
runtime. The chosen role sequence is a pedagogical design choice, not a trusted
academic requirement. Duration does not produce any fixed slide count. Guided
and independent are support modes, never learner ability or difficulty levels.
Prerequisites, difficulty and learner history remain not asserted.

## P5B interface and incomplete content

Every substantive role exposes an unpopulated authoring requirement with source
LR/coverage refs and minimum/target items. Existing P4A reuse is only a candidate
hint; P5A does not read P4A or certify any content reuse.

Standard Lesson explicitly requests new content for SL-04 (early retrieval),
SL-06 (mini example), SL-09 (second full example), SL-10/11 (guided practice),
SL-15 (exit check), plus one additional target item in SL-12. No wording, numbers,
solutions or questions are generated. If potential reuse fails validation, P5B
must author the full remaining requirements, not treat hints as completed items.

P5B should consume the typed profiled specification and source bindings, refresh
live upstream trust, populate or validate reuse for each role, and validate
content and scope before creating a presentation manifest. P5A marks planned
coverage and readiness for content authoring only. `ready_as_authored_content`
and `ready_for_rendering` remain false for both profiles.

## Evidence

`output/p5a_lesson_profiles` contains both profile configurations, both profiled
specifications, validation reports, provenance, baseline hashes, test logs and
`acceptance.json`. Acceptance explicitly records density comparison, identical
scope hashes, item/role counts, unchanged database state and frozen-file hashes.

Baseline: 40 existing P3C tests passed. Current regression: 180 passed, including
50 new profile tests and 130 P3A/P3B/P3C tests. The entire repository suite was not
rerun for this additive planning layer; unchanged P4C/P4C.1 artifacts and prior
acceptance files were checked by hash, not regenerated.
