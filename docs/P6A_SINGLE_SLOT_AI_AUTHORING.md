# P6A — constrained single-slot AI candidate authoring

This opt-in experiment replaces only `profiled-sd-standard-lesson-SL-10`
(Standard Lesson, Guided Practice 1). The frozen pre-AI path remains unchanged.
The supplied task attachment ends in section 47 at “accepted content → AI
candidate”; this implementation covers the requirements available in that file.

## Authority and contracts

`authoring-brief/1` is compiled from live, usable Q2/Q3 snapshots through the
existing learning, pedagogical, authored-content and P5C gates. Only two existing
learning target statements, the validated summary-statistics formula, the role
and content constraints leave the application. No source wording, local paths,
academic hashes, review identities, snapshot internals or reference manifest is
sent to the model. The brief stored in an audit is exactly the brief sent.

The provider returns strict `ProviderContent`: a student question template,
numerical inputs, four typed scaffold steps, and separate proposed solution
arithmetic. Extra fields are rejected at every level. The application supplies
candidate ID, current input binding, role/LR/task references, origin and provider
metadata in `ai-author-candidate/1`; the model cannot select these fields.

`ai-candidate-validation/1` records individual schema, binding, completeness,
scaffold, maths, solution, scope, boundary, separation, origin and composition
checks. No score or model confidence supplies authority. `accepted=true` means
only that this particular candidate satisfies the bounded slot contract. It
does not mean human academic approval, trusted snapshot membership, publication
permission or pedagogical quality certification.

## Deliberately narrow language policy

The model chooses original feasible numerical values, one of two newly supplied
question templates and one permitted wording for each of four scaffold types.
All four ordered actions are required: first term, second term, subtraction,
square root. Numbers are supplied in structured fields and interpolated only
after validation. The output is genuinely the provider's numerical candidate,
not the old deterministic `(6, 30, 174)` fixture. Synthetic demonstrations are
labelled `synthetic_test`, never live AI.

This is stricter than arbitrary free-form AI prose: unfamiliar wording is
rejected, even if a human might consider it correct. This makes question/answer
separation and scope checks structural. Existing boundary checks are reused as
an additional check, not as a claim that keyword rules prove natural language
safe. No general plagiarism detector is implemented. No source question wording
is supplied; candidates cannot claim Pearson authorship or endorsement.

The numeric policy permits positive integer `n` up to 1,000,000 and bounded
decimal/fraction strings (up to 128 characters, no exponent encoding). These
are resource/display safeguards, not difficulty or “nice numbers” rankings.
The existing P4A rational/Decimal engine checks feasibility and recomputes the
mean, variance, exact radicand, numeric SD and display. Proposed intermediate
terms and independently supplied solution inputs must agree. The same existing
solution verifier is reused; there is no second AI maths engine.

## Compatibility with frozen P5B/P5C/P5D

P5C/1 intentionally accepts only its deterministic provider's representation.
P6A does not weaken that check or change the protected files or pinned hashes.
An explicit composition adapter proves the unchanged base with P5C, checks the
single substitution independently, and creates `experimental-profiled-ai-content/1`.
Only SL-10's question, solution, role mapping and associated verification change.
Other new/reused content and all scope/boundary/LR/CR data are retained.

This composition result is **not a P5C/1 renderer report for the AI package**.
The experimental schema, origin and status are distinct; `ready_for_rendering`
and `ready_for_p5c` remain false. Existing renderers reject the experimental
package. A future versioned P5C/P5D adapter must validate this actual schema
before AI content can be rendered. There is no fallback that claims old content
was AI-generated, and no automatic retry, repair, promotion or publication.

The runtime never imports test fixtures or treats the engineering freeze manifest
as trust authority. The new subpackage is separate to preserve every frozen
pre-AI file, while reusing existing live services and pure validators.

## Operator commands (PowerShell, project directory)

Inspect the exact outbound brief without credentials or a model call:

```powershell
python -m academic_os.ai_authoring --db var/p0_q2.sqlite3 ai-author-slot standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --show-brief
```

The live path is opt-in and may incur an API charge. Set
`ACADEMIC_OS_AUTHOR_MODEL` to an explicitly selected model supporting structured
outputs. The existing environment/dotenv credential convention is loaded only
when constructing the live provider. No credential value belongs in a command
line argument or output file. The project `.venv` already contains the SDK.

```powershell
.venv\Scripts\python.exe -m academic_os.ai_authoring --db var/p0_q2.sqlite3 ai-author-slot standard-deviation --profile standard-lesson --role profiled-sd-standard-lesson-SL-10 --live --output-dir output/p6a_live
```

The separate module CLI is intentional: `academic_os/cli.py` belongs to the
byte-protected pre-AI baseline. Missing mode, unsupported profile/role or missing
audit destination is rejected before any model call. Live authoring reloads
current source gates after the attempt; stale or revoked sources block acceptance.

The adapter uses the SDK's `responses.parse(..., text_format=ProviderContent)`
interface with `store=False`, no tools, a bounded output limit, 60-second timeout
and `max_retries=0`. Refusal, incomplete output, API failure or validation failure
ends the attempt. API exception bodies are not logged. SDK parsing failures may
prevent recovery of the raw response/usage; the audit then records a generic
failure code rather than unsafe exception details. See the
[official structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

Each attempt is atomically saved under a new application-generated ID. Audits
contain the brief, clearly labelled untrusted raw output, candidate if parsed,
validation, and experimental package only if accepted. Token usage and latency
are operational metadata; monetary cost is `not_computed`. Secret-like output is
withheld and rejected. An existing attempt is never overwritten. Audit files
and exported acceptance flags are not runtime authorisation credentials.

## Tests and reproducible offline demonstration

```powershell
python -m unittest tests_p0.test_ai_authoring -v
python -m tests_p0.ai_authoring_acceptance
```

The acceptance command uses explicitly synthetic structured output, saves both
an accepted example and a rejected wrong-answer example, compares all protected
files and database state, and records that no live API was called. It does not
overwrite an existing acceptance directory. Unit tests use fake providers and
mock SDK clients; they do not need a real secret. The known historical missing
`AI_Academic_Operating_System_Brainstorm_CN.pptx` full-suite error remains outside
this change; neither that file nor its pin is fabricated.
