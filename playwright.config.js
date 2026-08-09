const { defineConfig, devices } = require('@playwright/test');

const baseURL = 'http://127.0.0.1:4173';

module.exports = defineConfig({
  testDir: './tests/browser',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL,
    screenshot: 'only-on-failure',
    serviceWorkers: 'block',
    timezoneId: 'UTC',
    trace: 'retain-on-failure',
    video: 'off'
  },
  projects: [
    {
      name: 'desktop-chromium',
      testMatch: /(map|accessibility|performance)\.spec\.js/,
      use: {
        browserName: 'chromium',
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 }
      }
    },
    {
      name: 'mobile-chromium',
      testMatch: /mobile\.spec\.js/,
      use: {
        browserName: 'chromium',
        ...devices['Pixel 7']
      }
    }
  ],
  webServer: {
    command: 'python3 -m http.server 4173 --bind 127.0.0.1 --directory site',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
    stderr: 'ignore'
  }
});
