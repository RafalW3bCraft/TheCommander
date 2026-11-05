import { test as base, expect } from "@playwright/test";

// Only scripts.e2e_server recognizes this header. Production ignores it.
// Keep real, independent login sessions and the unchanged ten/minute limit.
export const test = base.extend({
  extraHTTPHeaders: async ({}, provide) => {
    await provide({ "X-E2E-Client": crypto.randomUUID() });
  },
});
export { expect };
