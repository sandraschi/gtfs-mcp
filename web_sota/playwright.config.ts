import { defineConfig } from "@playwright/test";

const BACKEND = "http://127.0.0.1:10913";
const FRONTEND = "http://127.0.0.1:10912";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: FRONTEND,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "uv run -m gtfs_mcp --http --host 127.0.0.1 --port 10913",
      url: `${BACKEND}/health`,
      cwd: "../",
      timeout: 60000,
      reuseExistingServer: true,
    },
    {
      command: "npm run dev",
      url: FRONTEND,
      timeout: 60000,
      reuseExistingServer: true,
    },
  ],
});
