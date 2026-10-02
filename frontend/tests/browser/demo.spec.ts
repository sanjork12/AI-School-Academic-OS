import { test, expect } from "@playwright/test";
import data from "../../src/data/demo.json";
// Runs against either the dev server or a server hosting the static out/ build.
test("complete five-step demonstration and review actions", async ({
  page,
  baseURL,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const remote: string[] = [];
  page.on("request", (r) => {
    if (new URL(r.url()).origin !== new URL(baseURL!).origin) remote.push(r.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Import a Syllabus" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Process Syllabus" }),
  ).toBeDisabled();
  await page.screenshot({
    path: "test-results/import-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Use Demo Syllabus" }).click();
  await page.getByRole("button", { name: "Process Syllabus" }).click();
  await expect(
    page.getByRole("button", { name: "Explore Curriculum" }),
  ).toBeVisible({ timeout: 10000 });
  await expect(
    page.getByText("13 mapped objectives · 2 approved human decisions"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explore Curriculum" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Topic 2 · Equations, formulae and identities",
    }),
  ).toBeVisible();
  await expect(
    page.getByText(data.reviewQueue[0].objectives[0].wording, { exact: true }),
  ).toBeVisible();
  await page.locator(".objective summary").first().click();
  await expect(
    page.getByText("Official source ID: EDX-4MA1-F-2.8-A", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Higher", exact: true }).click();
  await expect(
    page.getByText(
      "identify harder examples of regions defined by linear inequalities",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("button", { name: "2.4 Linear equations" }).click();
  await expect(
    page.getByRole("heading", { name: "No separate objectives in this tier" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Foundation", exact: true }).click();
  await expect(page.locator(".objective")).toHaveCount(2);
  await page.getByRole("button", { name: "Open Human Review" }).click();
  await expect(
    page.getByRole("heading", { name: "Human Review", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Approved · local demo only",
  );
  await page.getByRole("button", { name: /02 \/ Skill consolidation/ }).click();
  await expect(
    page.getByText("Same underlying competency", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Simple linear inequalities", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Harder examples", { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/review-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Modify", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByLabel("Skill Name", { exact: true })
    .fill("Demo revised region skill");
  await page.getByLabel("Subject Domain", { exact: true }).fill("Demo domain");
  await page
    .getByLabel("Description", { exact: true })
    .fill("Temporary expert revision.");
  await page.getByRole("button", { name: "Save demo changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Demo revised region skill" }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toHaveText(
    "Modified · local demo only",
  );
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Rejected · local demo only",
  );
  await page.getByRole("button", { name: "View Approved Graph" }).click();
  await expect(
    page.getByRole("heading", { name: "Approved Academic Graph", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Demo revised region skill", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Identify regions defined by linear inequalities",
      exact: true,
    }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "test-results/graph-desktop.png",
    fullPage: true,
  });
  await page
    .getByText("Explore all 10 approved academic skills", { exact: true })
    .click();
  await expect(page.locator(".graph-card")).toHaveCount(10);
  await page.getByRole("button", { name: "Reset Demo" }).click();
  await expect(
    page.getByRole("button", { name: "Process Syllabus" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: /4. Review/ }).click();
  await expect(page.getByRole("status")).toHaveText(
    "Your academic judgement matters.",
  );
  await page.getByRole("button", { name: "Modify", exact: true }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Import a Syllabus" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
  expect(remote).toEqual([]);
});
test("local PDF selection, invalid file, and responsive layout", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByLabel("Select syllabus PDF")
    .setInputFiles({
      name: "notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("test"),
    });
  await expect(
    page.getByRole("alert").filter({ hasText: "Please select a PDF" }),
  ).toContainText("Please select a PDF");
  await page
    .getByLabel("Select syllabus PDF")
    .setInputFiles({
      name: "my-syllabus.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 demo"),
    });
  await expect(
    page.getByText("my-syllabus.pdf", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Process Syllabus" }),
  ).toBeEnabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/import-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: /4. Review/ }).click();
  await page.getByRole("button", { name: /02 \/ Skill consolidation/ }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/review-mobile.png",
    fullPage: true,
  });
});
