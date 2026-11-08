import { test, expect } from "./fixtures";
import AxeBuilder from "@axe-core/playwright";

test("sandbox displays evidence and requires deliberate exact approval", async ({
  page,
}, testInfo) => {
  if (testInfo.project.name === "offline-ui") {
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/status")
        return route.fulfill({ json: { bootstrap_required: false } });
      if (path === "/api/auth/me")
        return route.fulfill({
          status: 401,
          json: { error: { message: "Fixture sign-in" } },
        });
      if (path === "/api/auth/login")
        return route.fulfill({
          json: {
            owner_id: "fixture-owner",
            username: "browser-owner",
            csrf: "fixture-csrf",
          },
        });
      if (path === "/api/auth/reauthenticate")
        return route.fulfill({ json: { status: "reauthenticated" } });
      if (path === "/api/projects")
        return route.fulfill({
          json: [
            {
              id: "fixture-project",
              name: "Public demo",
              is_default: true,
              revision: 1,
            },
          ],
        });
      if (path === "/api/worker")
        return route.fulfill({ json: { online: false, last_seen: null } });
      if (path === "/api/budgets")
        return route.fulfill({
          json: {
            max_steps: 5,
            max_run_seconds: 180,
            max_daily_runs: 50,
            max_daily_tokens: 100000,
            daily_spend_limit_usd: null,
            usage: [],
          },
        });
      if (path.startsWith("/api/sandbox/")) return route.fallback();
      return route.fulfill({ json: [] });
    });
  }
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const job = {
    id: "3fc233dc-e7dd-4851-b8c1-e972a4f3d5ef",
    project_id: "fixture-project",
    kind: "browser",
    goal: "Fill the controlled public demo form",
    url: "https://example.com/",
    status: "waiting_approval",
    created_at: "2026-11-04T09:00:00Z",
    approval_digest: "a".repeat(64),
    approval_expires_at: "2026-11-08T23:00:00Z",
    plan: {
      explanation: "Inspect before acting",
      steps: [{ action: "fill", selector: "#name", value: "Demo" }],
    },
    evidence: {
      verification: {
        verified: true,
        explanation: "Controlled vision fixture",
      },
    },
    receipt: { destroyed: true, evidence_type: "test_fixture" },
    events: [{ kind: "approval_required" }],
    error: null,
  };
  let approvals = 0;
  await page.route("**/api/sandbox/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/status")) {
      await route.fulfill({
        json: {
          enabled: true,
          worker_online: true,
          model: "fixture-text",
          vision_model: "fixture-vision",
          domains: ["example.com"],
          runtime: "runsc",
        },
      });
    } else if (url.pathname.endsWith("/decision")) {
      expect(route.request().postDataJSON()).toEqual({
        digest: job.approval_digest,
        approve: true,
      });
      approvals += 1;
      job.status = "approved";
      await route.fulfill({ json: job });
    } else {
      await route.fulfill({
        json: url.pathname.endsWith("/jobs") ? [job] : job,
      });
    }
  });
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill("browser-owner");
  await page
    .getByLabel("Password", { exact: true })
    .fill("fictional-browser-password");
  const loginResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/auth/login") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  expect((await loginResponse).status(), "real sign-in must succeed").toBe(200);
  await page.getByRole("button", { name: "Sandbox", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sandbox", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Fill the controlled public demo form/ })
    .click();
  await expect(page.getByText("Inspect before acting")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve exact plan" }),
  ).toBeDisabled();
  expect(approvals).toBe(0);
  await page.getByRole("checkbox").check();
  await expect(
    page.getByRole("button", { name: "Approve exact plan" }),
  ).toBeDisabled();
  await page
    .getByLabel("Confirm owner password")
    .fill("fictional-browser-password");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export evidence" }).click();
  expect((await download).suggestedFilename()).toBe(`sandbox-${job.id}.json`);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("sandbox-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(
    page.getByRole("button", { name: "Approve exact plan" }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("sandbox-mobile.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Approve exact plan" }).click();
  await expect.poll(() => approvals).toBe(1);
  await expect(
    page.getByRole("button", { name: "Approve exact plan" }),
  ).toHaveCount(0);
  expect(errors).toEqual([]);
});
