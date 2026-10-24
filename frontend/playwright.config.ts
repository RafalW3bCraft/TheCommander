import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 120000,
  reporter: [
    ["list"],
    ["json", { outputFile: "../docs/evidence/browser-results.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:8010",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command:
      "cd .. && uv run uvicorn scripts.e2e_server:app --host 127.0.0.1 --port 8010",
    url: "http://127.0.0.1:8010/health/ready",
    reuseExistingServer: false,
    timeout: 30000,
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
