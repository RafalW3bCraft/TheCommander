import type { Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "./fixtures";

const password = "fictional-private-account-password";

async function signIn(page: Page, username: string, credential: string) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(credential);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Assistant", exact: true }),
  ).toBeVisible();
}

test("operator invitation creates a private account with revocable independent sessions", async ({
  page,
  browser,
}) => {
  await signIn(page, "browser-owner", "fictional-browser-password");
  const operatorProjects = await (
    await page.request.get("/api/projects")
  ).json();
  await page.getByRole("button", { name: "Account", exact: true }).click();
  await page
    .getByLabel("Verify operator password")
    .fill("fictional-browser-password");
  await page
    .getByRole("button", { name: "Verify password and load access controls" })
    .click();
  await expect(page.getByRole("status")).toContainText("Password verified");
  await page
    .getByRole("button", { name: "Create invitation", exact: true })
    .click();
  const tokenField = page.getByLabel("One-time invitation token");
  await expect(tokenField).toBeVisible();
  const token = await tokenField.inputValue();
  expect(token.length).toBeGreaterThan(32);
  await page.getByRole("button", { name: "Hide token" }).click();
  await expect(tokenField).toHaveCount(0);

  const first = await browser.newContext({
    extraHTTPHeaders: { "X-E2E-Client": crypto.randomUUID() },
  });
  const second = await browser.newContext({
    extraHTTPHeaders: { "X-E2E-Client": crypto.randomUUID() },
  });
  try {
    const personal = await first.newPage();
    const username = "private-" + crypto.randomUUID().slice(0, 12);
    await personal.goto("/");
    await personal
      .getByRole("button", { name: "Register with invitation" })
      .click();
    await personal.getByLabel("Username", { exact: true }).fill(username);
    await personal.getByLabel("Password", { exact: true }).fill(password);
    await personal
      .getByLabel("Invitation token", { exact: true })
      .fill("invalid-".repeat(6));
    await personal
      .getByRole("button", { name: "Create private account" })
      .click();
    await expect(personal.getByRole("alert")).toContainText(
      "Invitation is invalid or unavailable",
    );
    await expect(
      personal.getByRole("heading", { name: "Create your private account" }),
    ).toBeVisible();
    await personal.getByLabel("Invitation token", { exact: true }).fill(token);
    const registration = personal.waitForResponse(
      (r) =>
        r.url().endsWith("/api/auth/register") &&
        r.request().method() === "POST",
    );
    await personal
      .getByRole("button", { name: "Create private account" })
      .click();
    expect((await registration).status()).toBe(200);
    await expect(
      personal.getByRole("heading", { name: "Assistant", exact: true }),
    ).toBeVisible();
    const projects = await (await personal.request.get("/api/projects")).json();
    expect(projects).toHaveLength(1);
    expect(
      operatorProjects.some((p: { id: string }) => p.id === projects[0].id),
    ).toBe(false);
    expect(
      (
        await personal.request.get(
          `/api/runs?project_id=${operatorProjects[0].id}`,
        )
      ).status(),
    ).toBe(404);
    expect((await personal.request.get("/api/admin/accounts")).status()).toBe(
      403,
    );
    await personal
      .getByRole("button", { name: "Settings", exact: true })
      .click();
    await expect(
      personal.getByRole("button", { name: /Import.*environment/i }),
    ).toHaveCount(0);

    await personal
      .getByRole("button", { name: "Account", exact: true })
      .click();
    await expect(
      personal.getByText("Personal account", { exact: false }).first(),
    ).toBeVisible();
    await expect(
      personal.getByRole("heading", { name: "Invitations and account access" }),
    ).toHaveCount(0);
    await personal
      .getByLabel("Display name", { exact: true })
      .fill("Fictional private profile");
    await personal.getByRole("button", { name: "Save profile" }).click();
    await expect(personal.getByRole("status")).toContainText("Profile saved");

    const other = await second.newPage();
    await signIn(other, username, password);
    await personal
      .getByRole("button", { name: "Assistant", exact: true })
      .click();
    await personal
      .getByRole("button", { name: "Account", exact: true })
      .click();
    await expect(
      personal.getByText("Other session", { exact: true }),
    ).toBeVisible();
    await personal
      .getByRole("button", { name: "Sign out other sessions", exact: true })
      .click();
    await expect(personal.getByRole("status")).toContainText(
      "Other sessions signed out",
    );
    expect((await other.request.get("/api/auth/me")).status()).toBe(401);
    await other.reload();
    await expect(
      other.getByRole("button", { name: "Sign in", exact: true }),
    ).toBeVisible();

    await signIn(other, username, password);
    const beforeRotation = await (
      await personal.request.get("/api/auth/me")
    ).json();
    await personal
      .getByLabel("Current password", { exact: true })
      .fill(password);
    await personal
      .getByLabel("New password", { exact: true })
      .fill(password + "-changed");
    await personal
      .getByRole("button", {
        name: "Change password and sign out other sessions",
      })
      .click();
    await expect(personal.getByRole("status")).toContainText(
      "Password changed",
    );
    const afterRotation = await (
      await personal.request.get("/api/auth/me")
    ).json();
    expect(afterRotation.csrf).not.toBe(beforeRotation.csrf);
    expect((await other.request.get("/api/auth/me")).status()).toBe(401);
    await personal
      .getByLabel("Display name", { exact: true })
      .fill("Profile after session rotation");
    await personal.getByRole("button", { name: "Save profile" }).click();
    await expect(personal.getByRole("status")).toContainText("Profile saved");

    expect(
      (await new AxeBuilder({ page: personal }).analyze()).violations,
    ).toEqual([]);
    await personal.setViewportSize({ width: 375, height: 812 });
    expect(
      await personal.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await personal.keyboard.press("Tab");
    expect(
      await personal.evaluate(() => document.activeElement?.tagName),
    ).not.toBe("BODY");
    expect(
      (await new AxeBuilder({ page: personal }).analyze()).violations,
    ).toEqual([]);
    await personal
      .getByRole("button", { name: "Sign out", exact: true })
      .click();
    await expect(
      personal.getByRole("button", { name: "Sign in", exact: true }),
    ).toBeVisible();
    expect((await personal.request.get("/api/auth/me")).status()).toBe(401);
  } finally {
    await first.close();
    await second.close();
  }
});
