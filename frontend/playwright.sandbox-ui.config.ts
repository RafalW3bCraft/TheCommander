// Offline UI contract only. The normal config still exercises the real API/DB.
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: "sandbox.spec.ts",
  projects: [{ name: "offline-ui" }],
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8011",
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: "python3 -m http.server 8011 --bind 127.0.0.1 --directory dist",
    url: "http://127.0.0.1:8011",
    reuseExistingServer: false,
  },
});
