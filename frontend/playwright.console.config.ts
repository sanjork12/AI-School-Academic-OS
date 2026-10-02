import { defineConfig, devices } from "@playwright/test";
process.env.P6UI_ACCEPTANCE_DIR=process.env.P6UI_ACCEPTANCE_DIR??"tmp/p6ui-console-browser";
export default defineConfig({
  testDir:"./tests/console",workers:1,fullyParallel:false,timeout:90000,
  use:{baseURL:"http://127.0.0.1:3000",...devices["Desktop Chrome"],channel:"msedge",screenshot:"only-on-failure",trace:"retain-on-failure"},
  webServer:[
    {command:"python -B -m console_api",cwd:"..",url:"http://127.0.0.1:8765/api/health",reuseExistingServer:false,timeout:60000},
    {command:"node scripts/serve-static.mjs",url:"http://127.0.0.1:3000",reuseExistingServer:false,timeout:30000}
  ],
  reporter:[["list"],["json",{outputFile:`../${process.env.P6UI_ACCEPTANCE_DIR}/frontend-e2e.json`}]],
});
