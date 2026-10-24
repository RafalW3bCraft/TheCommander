import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("browser-owner");
  await page
    .getByLabel("Password", { exact: true })
    .fill("fictional-browser-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Today", exact: true }),
  ).toBeVisible();
}
test("desktop owner memory connections three skills approvals and receipts", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page);
  await page.getByRole("button", { name: "Memory", exact: true }).click();
  await page.getByLabel("Preference or fact").fill("Browser preference");
  await page
    .getByLabel("What should I remember?")
    .fill("Use three short bullets.");
  await page
    .getByLabel("Memory expiry (optional, your browser’s local time)")
    .fill("2030-01-01T12:00");
  await page.getByRole("button", { name: "Save memory", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Browser preference" }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Memory", exact: true }).click();
  await expect(
    page.getByText("Use three short bullets.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit Browser preference" }).click();
  await page
    .getByLabel("What should I remember?")
    .fill("Use concise paragraphs.");
  await page.getByRole("button", { name: "Save correction" }).click();
  await expect(
    page.getByText("Use concise paragraphs.", { exact: true }),
  ).toBeVisible();
  const memories = await (await page.request.get("/api/memory")).json();
  expect(
    memories.find(
      (memory: { key: string; expires_at: string }) =>
        memory.key === "Browser preference",
    ).expires_at,
  ).toBeTruthy();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export memory" }).click();
  expect((await download).suggestedFilename()).toBe("thecommander-memory.json");
  await page.getByRole("button", { name: "Connections", exact: true }).click();
  for (const name of [
    "Nebius · NVIDIA inference",
    "GitHub",
    "Tavily research",
    "Workspace notes",
  ]) {
    const section = page
      .locator("section")
      .filter({ has: page.getByRole("heading", { name, exact: true }) });
    if (name !== "Workspace notes")
      await section
        .getByLabel("API credential", { exact: true })
        .fill("offline-fixture-secret");
    if (name === "GitHub")
      await section
        .getByLabel("Repository", { exact: true })
        .fill("fictional/browser");
    if (name === "Tavily research")
      await section
        .getByLabel("Approved research domains (comma separated)")
        .fill("docs.python.org");
    await section
      .getByRole("button", {
        name:
          name === "Workspace notes" ? "Enable workspace" : "Save connection",
        exact: true,
      })
      .click();
    await section
      .getByRole("button", { name: "Test connection", exact: true })
      .click();
    await expect(section.getByText("validated", { exact: true })).toBeVisible();
  }
  await page.getByRole("button", { name: "Skills", exact: true }).click();
  for (const name of [
    "Engineering briefing",
    "Follow-through",
    "Research to action",
  ]) {
    const section = page
      .locator("section")
      .filter({ has: page.getByRole("heading", { name, exact: true }) });
    await section
      .getByLabel("What needs your attention?")
      .fill("Review retry handling for " + name);
    await section
      .getByRole("button", { name: "Run task", exact: true })
      .click();
    const details = page.getByRole("region", { name: "Run details" });
    if (name === "Research to action") {
      await expect(
        details.getByText("waiting approval", { exact: true }),
      ).toBeVisible();
      await details.getByRole("button", { name: "Edit proposal" }).click();
      await details.getByLabel("Issue title").fill("Reviewed retry safety");
      await details
        .getByRole("button", { name: "Save and require new approval" })
        .click();
      await expect(
        details.getByRole("heading", { name: "Reviewed retry safety" }),
      ).toBeVisible();
      await details
        .getByRole("button", { name: "Approve this exact issue" })
        .click();
      await expect(
        details.getByRole("link", { name: "Open verified issue ↗" }),
      ).toHaveAttribute(
        "href",
        "https://github.com/fictional/browser/issues/1",
      );
    } else
      await expect(
        details
          .getByText("succeeded", { exact: true })
          .filter({ visible: true }),
      ).toBeVisible();
    await details.getByRole("button", { name: "Close details" }).click();
  }
  await page.getByRole("button", { name: "Activity", exact: true }).click();
  await expect(page.locator(".run-item")).toHaveCount(3);
  await page.screenshot({
    path: "../docs/evidence/browser-desktop.png",
    fullPage: true,
  });
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByRole("button", { name: "Memory", exact: true }).click();
  await page.getByRole("button", { name: "Delete Browser preference" }).click();
  await expect(
    page.getByRole("heading", { name: "Browser preference" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("mobile keyboard schedule survives closed page and can be edited paused deleted", async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await login(page);
  const me = await (await page.request.get("/api/auth/me")).json();
  for (const kind of ["nebius", "workspace"])
    expect(
      (
        await page.request.put("/api/connections/" + kind, {
          headers: { "X-CSRF-Token": me.csrf },
          data: { secret: "offline-fixture-secret", enabled: true },
        })
      ).ok(),
    ).toBeTruthy();
  await page
    .getByLabel("Scheduled task")
    .fill("Offline browser scheduled follow-through");
  const future = new Date(Date.now() + 60000);
  const local = new Date(future.getTime() - future.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
  await page.getByLabel("First run (your browser’s local time)").fill(local);
  await page
    .getByRole("button", { name: "Schedule task", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Offline browser scheduled follow-through",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(page.getByText("paused", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Edit schedule" }).click();
  const past = new Date(Date.now() - 60000);
  await page
    .getByLabel("First run (your browser’s local time)")
    .fill(
      new Date(past.getTime() - past.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16),
    );
  await page
    .getByRole("button", { name: "Save schedule", exact: true })
    .click();
  await page.getByRole("button", { name: "Resume", exact: true }).click();
  await expect(page.getByText("paused", { exact: true })).toHaveCount(0);
  await page.close();
  const next = await context.newPage();
  await next.setViewportSize({ width: 375, height: 812 });
  await next.goto("/");
  await expect(
    next.getByRole("heading", { name: "Today", exact: true }),
  ).toBeVisible();
  await expect(
    next
      .getByRole("button")
      .filter({ hasText: "Offline browser scheduled follow-through" })
      .first(),
  ).toContainText("succeeded", { timeout: 15000 });
  await next.keyboard.press("Tab");
  expect(await next.evaluate(() => document.activeElement?.tagName)).not.toBe(
    "BODY",
  );
  expect(
    await next.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await next.screenshot({
    path: "../docs/evidence/browser-mobile.png",
    fullPage: true,
  });
  expect((await new AxeBuilder({ page: next }).analyze()).violations).toEqual(
    [],
  );
  await next.getByRole("button", { name: "Delete schedule" }).click();
  await expect(
    next.getByRole("heading", {
      name: "Offline browser scheduled follow-through",
    }),
  ).toHaveCount(0);
});

test("expired session returns to sign-in and tablet navigation remains usable", async ({
  page,
  context,
}) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await login(page);
  await page.getByText("Usage and limits", { exact: true }).click();
  await expect(page.getByText(/Daily limits:/)).toBeVisible();
  for (const destination of [
    "Memory",
    "Skills",
    "Connections",
    "Activity",
    "Today",
  ]) {
    await page.getByRole("button", { name: destination, exact: true }).click();
    await expect(
      page.getByRole("heading", { name: destination, exact: true }),
    ).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../docs/evidence/browser-tablet.png",
    fullPage: true,
  });
  await context.clearCookies();
  await page.getByRole("button", { name: "Memory", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary" })).toHaveCount(
    0,
  );
});

test("delayed responses preserve memory search, edits, selected notes and cancelled runs", async ({
  page,
}) => {
  await login(page);
  const me = await (await page.request.get("/api/auth/me")).json();
  const headers = { "X-CSRF-Token": me.csrf };
  for (const key of ["Race Alpha", "Race Beta"])
    expect(
      (
        await page.request.post("/api/memory", {
          headers,
          data: { key, content: key, kind: "explicit" },
        })
      ).ok(),
    ).toBeTruthy();
  await page.getByRole("button", { name: "Memory", exact: true }).click();
  await page.getByRole("button", { name: "Edit Race Alpha" }).click();
  let releaseSave!: () => void;
  const saveGate = new Promise<void>((resolve) => {
    releaseSave = resolve;
  });
  let saveArrived!: () => void;
  const saveSeen = new Promise<void>((resolve) => {
    saveArrived = resolve;
  });
  await page.route("**/api/memory/*", async (route) => {
    if (route.request().method() !== "PUT") return route.continue();
    const response = await route.fetch();
    saveArrived();
    await saveGate;
    await route.fulfill({ response });
  });
  await page.getByLabel("What should I remember?").fill("Corrected Alpha");
  await page.getByRole("button", { name: "Save correction" }).click();
  await saveSeen;
  await expect(
    page.getByRole("button", { name: "Edit Race Beta" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Cancel edit" }),
  ).toBeDisabled();
  await page.getByLabel("Search memory").fill("Race Beta");
  await expect(
    page.getByRole("heading", { name: "Race Alpha", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Cancel edit" }),
  ).toBeDisabled();
  releaseSave();
  await expect(
    page.getByRole("button", { name: "Edit Race Beta" }),
  ).toBeEnabled();
  await expect(
    page.getByRole("heading", { name: "Race Alpha", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("Search memory")).toHaveValue("Race Beta");
  await page.getByRole("button", { name: "Edit Race Beta" }).click();
  await page.getByRole("button", { name: "Delete Race Beta" }).click();
  await expect(
    page.getByRole("heading", { name: "Remember something" }),
  ).toBeVisible();
  await page.unroute("**/api/memory/*");

  for (const kind of ["nebius", "workspace", "github", "tavily"])
    expect(
      (
        await page.request.put("/api/connections/" + kind, {
          headers,
          data: {
            secret: "offline-fixture-secret",
            enabled: true,
            repository: "fictional/browser",
            domains: ["docs.python.org"],
          },
        })
      ).ok(),
    ).toBeTruthy();
  for (const name of ["race-alpha.md", "race-beta.md"])
    expect(
      (
        await page.request.post("/api/notes", {
          headers,
          data: { name, content: "Content of " + name },
        })
      ).ok(),
    ).toBeTruthy();
  await page.getByRole("button", { name: "Connections", exact: true }).click();
  await page.getByRole("button", { name: "Load saved notes" }).click();
  let releaseNote!: () => void;
  const noteGate = new Promise<void>((resolve) => {
    releaseNote = resolve;
  });
  let noteArrived!: () => void;
  const noteSeen = new Promise<void>((resolve) => {
    noteArrived = resolve;
  });
  await page.route("**/api/notes/race-alpha.md", async (route) => {
    const response = await route.fetch();
    noteArrived();
    await noteGate;
    await route.fulfill({ response });
  });
  await page
    .getByRole("button", { name: "race-alpha.md", exact: true })
    .click();
  await noteSeen;
  await page.getByRole("button", { name: "race-beta.md", exact: true }).click();
  await expect(
    page.getByText("Content of race-beta.md", { exact: true }),
  ).toBeVisible();
  const deliveredNote = page.waitForResponse("**/api/notes/race-alpha.md");
  releaseNote();
  await (await deliveredNote).finished();
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await expect(
    page.getByRole("heading", { name: "race-beta.md" }),
  ).toBeVisible();
  await expect(
    page.getByText("Content of race-beta.md", { exact: true }),
  ).toBeVisible();
  await page.unroute("**/api/notes/race-alpha.md");

  await page.getByRole("button", { name: "Skills", exact: true }).click();
  const research = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Research to action", exact: true }),
  });
  await research
    .getByLabel("What needs your attention?")
    .fill("Race approval cancellation");
  await research.getByRole("button", { name: "Run task", exact: true }).click();
  const details = page.getByRole("region", { name: "Run details" });
  await expect(
    details.getByText("waiting approval", { exact: true }),
  ).toBeVisible();
  let releasePoll!: () => void;
  const pollGate = new Promise<void>((resolve) => {
    releasePoll = resolve;
  });
  let pollArrived!: () => void;
  const pollSeen = new Promise<void>((resolve) => {
    pollArrived = resolve;
  });
  let held = false;
  await page.route(/\/api\/runs\/[^/]+$/, async (route) => {
    if (held || route.request().method() !== "GET") return route.continue();
    held = true;
    const response = await route.fetch();
    pollArrived();
    await pollGate;
    await route.fulfill({ response });
  });
  await pollSeen;
  await details.getByRole("button", { name: "Cancel further work" }).click();
  await expect(details.getByText("cancelled", { exact: true })).toBeVisible();
  const deliveredPoll = page.waitForResponse(/\/api\/runs\/[^/]+$/);
  releasePoll();
  await (await deliveredPoll).finished();
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
  await expect(details.getByText("cancelled", { exact: true })).toBeVisible();
  await expect(
    details.getByRole("button", { name: "Approve this exact issue" }),
  ).toHaveCount(0);
});
