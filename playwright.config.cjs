// @ts-check
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  retries: process.env.CI ? 1 : 0,
  webServer: {
    command: "python scripts/stub_server.py",
    port: 8001,
    reuseExistingServer: !process.env.CI,
  },
  use: {
    baseURL: "http://127.0.0.1:8001",
    headless: true,
  },
});
