import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function login(page: Page) {
  await page.goto("/");
  await page
    .getByLabel("Username", { exact: true })
    .fill("upgrade-browser-owner");
  await page
    .getByLabel("Password", { exact: true })
    .fill("fictional-browser-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Project", exact: true }),
  ).toBeEnabled();
}

test("project selection scopes new runs and rejects stale project renames", async ({
  page,
}) => {
  await login(page);
  const defaultProject = await page
    .getByLabel("Project", { exact: true })
    .inputValue();
  await page.getByRole("button", { name: "New project", exact: true }).click();
  await page
    .getByLabel("Project name", { exact: true })
    .fill("Upgrade UI acceptance");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  const selector = page.getByLabel("Project", { exact: true });
  await expect(selector).not.toHaveValue(defaultProject);
  const project = await selector.inputValue();
  await expect(page.getByLabel("Mode", { exact: true })).toHaveValue("ask");
  await expect(
    page.getByRole("option", { name: "Build · sandbox unavailable" }),
  ).toHaveJSProperty("disabled", true);
  await expect(
    page.getByRole("option", { name: "Review · sandbox unavailable" }),
  ).toHaveJSProperty("disabled", true);
  await page
    .getByLabel("What needs your attention?", { exact: true })
    .fill("Project-specific question");
  const sent = page.waitForResponse(
    (r) => r.url().endsWith("/api/runs") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run task", exact: true }).click();
  const response = await sent;
  expect(response.ok()).toBeTruthy();
  expect(response.request().postDataJSON()).toMatchObject({
    project_id: project,
    mode: "ask",
  });
  const run = await response.json();
  await expect(page.getByLabel("Conversation", { exact: true })).toHaveValue(
    run.conversation_id,
  );
  await selector.selectOption(defaultProject);
  await expect(page.getByLabel("Conversation", { exact: true })).toHaveValue(
    "",
  );
  await expect(page.getByRole("region", { name: "Run details" })).toHaveCount(
    0,
  );
  await expect(
    page
      .getByLabel("Conversation", { exact: true })
      .locator("option", { hasText: "Project-specific question" }),
  ).toHaveCount(0);
  await selector.selectOption(project);
  await page
    .getByRole("button", { name: "Rename project", exact: true })
    .click();
  const me = await (await page.request.get("/api/auth/me")).json();
  const projects = await (await page.request.get("/api/projects")).json();
  const revision = projects.find(
    (p: { id: string }) => p.id === project,
  ).revision;
  expect(
    (
      await page.request.patch(`/api/projects/${project}`, {
        headers: { "X-CSRF-Token": me.csrf },
        data: { name: "Concurrent name", revision },
      })
    ).ok(),
  ).toBeTruthy();
  await page.getByLabel("Project name", { exact: true }).fill("Stale name");
  const conflict = page.waitForResponse(
    (r) =>
      r.url().endsWith(`/api/projects/${project}`) &&
      r.request().method() === "PATCH",
  );
  await page
    .getByRole("button", { name: "Save project name", exact: true })
    .click();
  expect((await conflict).status()).toBe(409);
  await expect(page.locator("#project-error")).toBeVisible();
  await expect(page.getByLabel("Project name", { exact: true })).toHaveValue(
    "Stale name",
  );
  await page.getByRole("button", { name: "Cancel project edit" }).click();
  await expect(selector.locator("option:checked")).toContainText(
    "Concurrent name",
  );
});

test("assistant renders safe Markdown without executing HTML or loading images", async ({
  page,
}) => {
  await login(page);
  const me = await (await page.request.get("/api/auth/me")).json();
  const project = await page
    .getByLabel("Project", { exact: true })
    .inputValue();
  const created = await page.request.post("/api/runs", {
    headers: { "X-CSRF-Token": me.csrf },
    data: {
      prompt: "Markdown safety sample",
      project_id: project,
      mode: "ask",
    },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const run = await created.json();
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("tracking.invalid")) requests.push(r.url());
  });
  await page.route(
    `**/api/conversations/${run.conversation_id}/messages`,
    (route) =>
      route.fulfill({
        json: [
          {
            id: "safe-markdown-fixture",
            role: "assistant",
            content:
              '# Evidence\n\n**Review** `print(1)`\n\n- One\n- Two\n\n[Docs](https://docs.python.org/3/)\n\n[unsafe](javascript:alert%281%29)\n\n![private image](https://tracking.invalid/pixel.png)\n\n<img src="https://tracking.invalid/html.png" onerror="alert(1)">\n\n```html\n<script>alert(1)</script>\n```',
          },
        ],
      }),
  );
  await page.reload();
  await page
    .getByLabel("Conversation", { exact: true })
    .selectOption(run.conversation_id);
  const message = page.locator(".message");
  await expect(
    message.getByRole("heading", { name: "Evidence", exact: true }),
  ).toBeVisible();
  await expect(message.locator("li")).toHaveCount(2);
  await expect(
    message.getByRole("link", { name: "Docs", exact: true }),
  ).toHaveAttribute("rel", "noopener noreferrer");
  await expect(message.locator("a")).toHaveCount(1);
  await expect(message.locator("img,script")).toHaveCount(0);
  await expect(message.locator("pre code")).toHaveText(
    "<script>alert(1)</script>",
  );
  expect(requests).toEqual([]);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: "../docs/evidence/upgrade-dark-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Use light theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.setViewportSize({ width: 375, height: 812 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../docs/evidence/upgrade-light-mobile.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("memory recall explains disabled and degraded index states", async ({
  page,
}) => {
  await login(page);
  const me = await (await page.request.get("/api/auth/me")).json();
  const saved = await page.request.post("/api/memory", {
    headers: { "X-CSRF-Token": me.csrf },
    data: { key: "Recall acceptance", content: "Use bounded retries." },
  });
  expect(saved.ok(), await saved.text()).toBeTruthy();
  const row = await saved.json();
  await page.getByRole("button", { name: "Memory", exact: true }).click();
  await page.getByText("Find relevant memory", { exact: true }).click();
  await expect(
    page.getByText("Semantic index is disabled.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Recall question", { exact: true }).fill("retries");
  await page.getByRole("button", { name: "Find relevant records" }).click();
  await expect(
    page.getByText("Canonical lexical matches.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator("details").getByText("Use bounded retries.", { exact: false }),
  ).toBeVisible();
  await page.route("**/api/memory/search?*", (route) =>
    route.fulfill({
      json: {
        records: [row],
        method: "lexical",
        index_status: "degraded",
      },
    }),
  );
  await page.getByRole("button", { name: "Find relevant records" }).click();
  await expect(
    page.getByText(
      "Semantic index unavailable; showing canonical lexical matches.",
    ),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: "../docs/evidence/upgrade-memory-degraded.png",
    fullPage: true,
  });
});
