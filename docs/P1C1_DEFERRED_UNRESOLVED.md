# P1C.1 — Deferred unresolved governance

An **UNRESOLVED** proposal remains a required blocker until a local operator explicitly defers it from a named publication target. **DEFERRED UNRESOLVED** means a publication scope decision has been recorded; the academic interpretation remains unresolved. Inspection, registry lookup, source verification and academic approval never create a defer decision.

## Storage and boundaries

`academic_os/governance.py` uses the existing append-only SQLite `requests` journal, with service-owned `record_type=publication_governance/1`. These are governance receipts, separate from academic `reviews`; no candidate field can manufacture a receipt. The current governance head is derived from ordered events for `(target_id, proposal_key)`. No schema migration, mutable academic flag or new competency is introduced. Decisions record action, operator, reason, timestamp, request ID, superseded event, proposal version, complete dependency manifest, target version and inspected ticket.

The CLI identifies the operator as `local-os:<username>`. This is the existing local machine/DB ownership trust boundary, not production authentication or a signed attestation. OS/DB owners can bypass local controls. A future API must authenticate the caller before invoking the same service operations.

Tickets reuse the existing bundle guard and additionally bind the target and governance head. Changed content, dependency versions, target policy, academic review heads or competing governance decisions reject stale submissions. Exact request retries return the same event; conflicting reuse fails. An IMMEDIATE transaction serializes writes; receipts and snapshot withdrawals commit or roll back together.

An accepted defer continues to bind content/dependency and target versions. Subsequent source verification or academic approval of unchanged evidence does not invalidate the committed scope decision; those normal reviews are independently required by the publication gate. New content never inherits an old defer. `reopen` appends a superseding event and returns the proposal to required participation. Future evidence can instead create a new proposal version and undergo normal resolution/review.

## Publication and trusted reads

Target definitions remain unchanged, including all five Q3 roots. The effective roots remove only unresolved proposals with a current explicit defer for that exact target. The manifest is recomputed from the remaining roots, preserving all shared/transitive dependencies. A proposal still required by another root cannot be excluded. Empty targets cannot publish. A different target requires its own scope decision.

The existing schema, source integrity, source verification and academic approval gates still apply. Deferred proposals and their parsed semantic interpretations do not enter trusted objects or semantic units. Shared original evidence may remain: Q3(c)(i)'s scope uses the MS c(ii) locator. This source fragment is not an approved c(ii) interpretation.

Governed snapshots include the immutable governance receipt under `publication_governance`, separate from trusted academic objects. Repeated publication of identical content/reviews/governance is deterministic. Reopen/supersede immediately adds an append-only snapshot block. On every `Service.snapshot` read, target policy, governance validity and current effective closure are checked; a changed excluded proposal also withdraws the old snapshot even though it was never an academic snapshot member. Snapshot bytes/history are preserved; blocked payloads are not served. Detached JSON cannot assert current usability; consumers must use the service read path. Q2 snapshots without governance retain their existing shape and hashes.

## Operator workflow

Inspection only (no decision):

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-unresolved PROPOSE-Q3-2023-c-ii --target Q3-2023-CORE --save-ticket var/q3-cii-governance-ticket.json
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check --target Q3-2023-CORE
```

Only after an actual human scope decision, submit it with the saved ticket:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 decide-unresolved PROPOSE-Q3-2023-c-ii defer --target Q3-2023-CORE --ticket var/q3-cii-governance-ticket.json --reason "<operator's actual scope rationale>" --request-id "<unique operator request ID>"
```

To reopen, inspect again into a new ticket file and submit `reopen` with a new request ID and reason. No real defer, source verification, academic approval or publication was executed by this implementation. The real Q3 target remains blocked.

## Reproducible isolated demonstration

```powershell
python -X utf8 -m unittest tests_p0.test_deferred_governance -v
python -X utf8 -m tests_p0.deferred_demo
python -X utf8 -m unittest discover -v
```

The demo creates disposable fixtures with copied sources and explicitly TEST ONLY operators. State A blocks unresolved material. State B explicitly defers c(ii), preserves its complete proposal and still blocks pending reviews. State C verifies sources and approves only the first four bundles, then publishes exactly four semantic units. It writes `output/p1c1_deferred_unresolved/temporary-defer-test.json`. The real database is never opened by the demo.

Core governance, storage, rendering, CLI and test fixtures remain separate. Future parsing/mapping stages continue to stage immutable proposals; they have no authority to defer them. A broader indexed governance store can replace the current small journal scan later without changing the service boundary.
