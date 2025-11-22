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
    env: {
      OPENAI_API_KEY: process.env.OPENAI_API_KEY || "sk-test",
      SKIP_RUNTIME_CREDENTIALS_VERIFY: "1",
      WEBHOOK_SECRET: process.env.WEBHOOK_SECRET || "stub-secret",
      TEST_MODE: "1",
      OMNI_TEST_MODE: "1",
    },
  },
  use: {
    baseURL: "http://127.0.0.1:8001",
    headless: true,
    env: {
      OPENAI_API_KEY: process.env.OPENAI_API_KEY || "sk-test",
      SKIP_RUNTIME_CREDENTIALS_VERIFY: "1",
      WEBHOOK_SECRET: process.env.WEBHOOK_SECRET || "stub-secret",
      TEST_MODE: "1",
      OMNI_TEST_MODE: "1",
    },
  },
});
