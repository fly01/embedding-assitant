import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    permissions: ["microphone"],
    launchOptions: {
      args: [
        "--use-fake-device-for-media-stream",
        "--use-fake-ui-for-media-stream",
      ],
    },
  },
  webServer: [
    {
      command:
        ".venv/bin/uvicorn framed_assistant.app:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      env: {
        FRAMED_ENV: "test",
        FRAMED_DATA_DIR: ".data/e2e",
      },
    },
    {
      command:
        "npm run dev --workspace frontend -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
      env: {
        VITE_API_BASE: "http://127.0.0.1:8000",
      },
    },
  ],
});
