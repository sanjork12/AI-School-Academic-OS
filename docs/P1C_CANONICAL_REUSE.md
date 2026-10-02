# P1C — Canonical knowledge reuse and expansion

P1C.1 adds explicit, target-specific human defer governance; see [the companion workflow](P1C1_DEFERRED_UNRESOLVED.md). Without that decision, the original five-required-root blocking behavior below remains unchanged. Real Q3 has no defer decision.

## Scope and evidence

Second evidence case: supplied Pearson Edexcel 9MA0/31 June 2023 Q3, from `output/p1c_case2/sources/June 2023 QP (Stats) (1).pdf` and `June 2023 MS (Stats).pdf`. QP cover identifies 20 June 2023, 9MA0/31, P72819A; MS cover identifies Summer 2023, 9MA0, Paper 31 Statistics. Both supplied copies carry PMT branding. These observations support candidate identity metadata, not verification of authenticity. SHA-256 is recorded per source. The original downloaded bytes are copied without editing. Operator verification remains mandatory.

QP PDF page 8 contains Q3; MS PDF page 9 contains scoring and notes. The parser creates separate source identities QP-2023/MS-2023, 13 locators (QP whole question, b/c containers and five assessable parts; five MS parts), a question, seven hierarchy nodes, one question condition, one dataset-evidence scope and five parsed parts. Individual marks are 2,1,2,1,1; QP prints grouped totals 2,3,2. MS scoring rows provide the individual allocation. Parsed spans retain exact page text, character boundaries and locator versions. The formula extraction remains layout-defective; no equations or glyphs are silently repaired. PDF renderer also warns about Symbol fonts; operator must use original pages.

Dataset context (Leeming, 1987, Daily Total Rainfall, the frequency table, tr notation, supplied summaries, May–October coverage, winter expectations and the estimate reasoning) is retained in located evidence and question-specific condition/scope, not canonical identity. MS notes include a review caveat about winter rainfall; the complete note span is preserved. Dataset rainfall expectations are scheme-specific evidence, not universal factual assertions.

## Generation versus acceptance oracle

`q3_parsing.py` contains only source registration/structure rules. Fixture-specific anchors and mark allocations locate the actual source, not academic mappings.

`canonical_proposals.py` accepts source-derived prompt, directive, scoring text, notes and given context. It has no question-ID, year, numerical answer or fixture-name semantic branches. It uses small explicit linguistic rules: preparation plus numerical replacement; calculation of mean/standard deviation using supplied summaries; representativeness supported by coverage-based scoring. Directional estimate reasoning without an established narrow rule stays unresolved. Arbitrary unknown text also stays unresolved without inventing the representativeness explanation.

This is a deliberately limited deterministic vocabulary, not a general semantic parser or trained model. Normalized-name lookup supports articles and basic average/mean wording; it does not claim general synonym/equivalence resolution. Ambiguous or existing pending identities are unresolved rather than duplicated. New names/descriptions are generic rule vocabulary, not claimed human approvals. No paid model or LLM integration.

`Registry.lookup` queries actual immutable objects and the P0 journal. Reuse requires a unique matching identity with a currently publishable dependency closure, including intact source evidence. Matching a mutable ID or a candidate's approved field is insufficient. Canonical query outcomes are recorded on the proposal for audit; this saved metadata is not a trusted credential. In an unresolved interpretation, a lookup with no existing match is only a search result, not permission to create a competency; the overall proposal action remains UNRESOLVED. The gate derives all actual trust from the existing journal.

`tests_p0/fixtures/q3_gold_standard.json` is an acceptance oracle only. Production modules never load it. Tests assert the expected direction and include alternative contexts/years and changed evidence to detect identity-based shortcuts. `q2_gold_standard.json` protects the approved Q2 semantics and identifies the existing snapshot; it does not replace or rebuild that snapshot.

## Outcomes

- a: CREATE_CANDIDATE — Data cleaning / data preparation; Prepare data for statistical analysis; Handle special/non-numeric values before calculating summary statistics. Evidence scope explicitly limits the claim to the supported replacement operation, not all cleaning methods.
- b(i): REUSE_EXISTING — Mean, CAN-STAT-MEAN-CALC, TC-SUMMARY-STATISTICS.
- b(ii): REUSE_EXISTING — Standard deviation, CAN-STAT-SD-CALC, TC-SUMMARY-STATISTICS.
- c(i): CREATE_CANDIDATE — Representativeness; Assess whether data are representative; Compare dataset coverage with the target population/time period. No assertion about every aspect of data suitability.
- c(ii): UNRESOLVED — exact observed reasoning and alternatives retained; no competency ID asserted, no reuse of pending CAN-STAT-CONTEXT-INFER. Unresolved is neither rejection nor absence of observation nor exclusion.

Estimation, cleaned data, weather, year and marks do not create duplicate mean/SD identities. Existing definitions and concept links are referenced without mutation. Five new question-to-canonical proposals remain pending even where their canonical definitions are already approved.

## Small compatible model extension

One new `proposal` envelope kind (`SemanticProposal`) holds action, parsed evidence reference, resolved canonical/concept/link/task references when present, observation, reasoning, evidence scope, alternatives and lookup audit. It derives from existing Reviewable, stays pending in candidate JSON, and uses the same immutable versions, CAS staging, review events and dependency manifest. It is the pending question-to-knowledge claim; no second review database, no schema migration, no approval flags accepted from input. Existing kinds serialize exactly as before.

Resolved proposals require complete concept relationships and a task condition. Unresolved proposals cannot assert a competency and require alternatives. Both direct P0 approval and bundle approval reject unresolved canonical identity. Resolution requires an explicit versioned stage revision followed by human review. A `revise` bundle decision records revision needed; it does not automatically edit content.

Canonical approval and question-mapping approval are distinct. Bundle approval reuses valid existing approvals but reviews each new dependent academic object and the proposal. New evidence is attached to the proposal/parsed records, not appended as reverse evidence against reused canonical definitions. That preserves Q2's original approval dependency manifests.

## Compatibility issue discovered

The legacy v0.3 validator assumes that every locator's descriptive question/part association is present in the validated set. Canonical reuse brings some old source locators into a new question closure without bringing the old questions themselves. Expanding dependency edges would invalidate old approvals and mix unrelated questions.

The compatibility adapter therefore first validates the entire original candidate graph (including all associations) with no external trust. Only in the temporary scoped v0.3 projection, association metadata pointing outside the selected closure is omitted. Original locators, SHA versions, source integrity checks, selected evidence and snapshot bytes remain unchanged. A regression test confirms that invalid original associations are still rejected. Existing P0 evaluates trust and publication solely over the selected dependency closure. No legacy schema or pinned data was edited.

P0 does not yet support resource-dependent conditions. Rather than adding dataset ingestion, the existing scope record holds the located MS dataset claims. No syllabus objective ID or curriculum equivalence has been invented.

## Review and publication

Source bundles: SOURCE-BUNDLE-QP-Q3-2023 and SOURCE-BUNDLE-MS-Q3-2023. Academic bundles: BUNDLE-Q3-2023-A, BUNDLE-Q3-2023-B-I, BUNDLE-Q3-2023-B-II, BUNDLE-Q3-2023-C-I, BUNDLE-Q3-2023-C-II.

All use existing inspect → ticket → explicit decision infrastructure and the same transaction/idempotency guarantees. `SOURCE_BUNDLES` retains its historical Q2-only API; `ALL_SOURCE_BUNDLES` supplies the extended CLI catalog. Listing filters to cases actually present in a database, so old Q2-only installations remain usable.

Q3-2023-CORE requires all five proposal roots. It is a complete-question target, not a partial-answer export. c(ii) is explicitly required and unresolved, so the target remains blocked even if all other objects become approved. Human resolution must create a reviewed version before a complete snapshot can exist. Q2-CORE and its definition/version remain unchanged. If another partial Q3 target is wanted later, that is an explicit policy decision, not silent exclusion.

Read-only inspection:

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-source SOURCE-BUNDLE-QP-Q3-2023 --save-ticket var/q3_2023_qp.ticket
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-source SOURCE-BUNDLE-MS-Q3-2023 --save-ticket var/q3_2023_ms.ticket
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 review-bundle BUNDLE-Q3-2023-B-I --save-ticket var/q3_2023_b_i.ticket
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 check --target Q3-2023-CORE
```

Only after actual human review, the operator can call `decide-source ID verify|reject --ticket FILE --reason REASON --request-id UNIQUE` and `decide-bundle ID approve|reject|revise ...`. No such real decisions were executed during implementation. The local OS/SQLite-owner trust boundary is unchanged; tickets do not authenticate users.

Reproducible candidate planning (writes a plan file only, exclusive creation):

```powershell
python -X utf8 -m academic_os --db var/p0_q2.sqlite3 plan-q3-2023 --output var/q3_2023_plan.json
```

Persist with existing `stage --file FILE --request-id UNIQUE`; plans carry expected versions. Generation is deterministic for the same graph, and regenerating still-pending owned candidates does not duplicate identities/versions. Different existing source/candidate content requires explicit revision, never silent overwrite. The submitted real plan and before/after evidence are stored in `output/p1c_case2/`.

## Validation

Run `python -X utf8 -m unittest tests_p0.test_canonical_reuse -v` and `python -X utf8 -m unittest discover -p test_*.py`. All test decisions use temporary databases and explicitly marked test operators/reasons. The production candidate-generation logic never imports the oracle. Historical v0.1/v0.2/v0.3 files and the known protected-PPT integrity check remain unchanged. Exact final counts are in `output/p1c_case2/acceptance.json`.
