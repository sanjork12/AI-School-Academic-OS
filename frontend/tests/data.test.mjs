import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const read = async (name) =>
  JSON.parse(await readFile(new URL(name, import.meta.url), "utf8"));
const view = await read("../src/data/demo.json");
const [f, h, g, history] = await Promise.all(
  [
    "foundation_parsed",
    "higher_parsed",
    "canonical_promoted",
    "human_review_decisions",
  ].map((name) => read(`../../output/topic2_${name}.json`)),
);
test("all official wording is preserved exactly, including damaged glyphs", () => {
  const originals = [f, h].flatMap((c) =>
    c.subtopics.flatMap((s) => s.objectives),
  );
  const shown = view.topics.flatMap((t) =>
    t.tiers.flatMap((t) => t.objectives),
  );
  assert.equal(shown.length, originals.length);
  for (const o of originals)
    assert.equal(
      shown.find((v) => v.id === o.source_id).wording,
      o.official_text,
    );
  assert.ok(shown.find((v) => v.id === "EDX-4MA1-F-2.8-A").formattingWarning);
});
test("summary and graph are computed from approved source records", () => {
  const approved = g.mappings.filter((m) => m.review_status === "approved");
  const mapped = new Set(approved.map((m) => m.official_source_id));
  assert.equal(view.processingSummary.mappings, approved.length);
  assert.equal(view.processingSummary.mapped, mapped.size);
  assert.equal(
    view.processingSummary.unmapped,
    view.processingSummary.official - mapped.size,
  );
  assert.equal(
    view.processingSummary.skills,
    g.canonical_objectives.filter((n) => n.status === "approved").length,
  );
  assert.equal(view.processingSummary.decisions, history.decisions.length);
  assert.equal(
    view.approvedGraph.flatMap((s) => s.objectives).length,
    approved.length,
  );
});
test("review provenance and source boundaries remain explicit", () => {
  assert.equal(view.reviewQueue.length, 2);
  assert.ok(
    view.reviewQueue.every(
      (c) => c.historicalStatus === "approve" && c.sourceStatus === "pending",
    ),
  );
  assert.ok(
    view.reviewQueue.every((c) =>
      c.domainSource.includes("Historical human review"),
    ),
  );
  assert.equal(
    view.reviewQueue.find((c) => c.id === "regions").objectives.length,
    2,
  );
  assert.ok(
    view.provenance.sources.every(
      (s) => s.startsWith("output/") && s.endsWith(".json"),
    ),
  );
  assert.ok(!JSON.stringify(view.topics).includes("difficulty_level"));
});
