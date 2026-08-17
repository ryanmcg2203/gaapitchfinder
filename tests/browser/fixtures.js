const { test: base, expect } = require('@playwright/test');

const LOCAL_ORIGIN = 'http://127.0.0.1:4173';
const ANALYTICS_CONSENT_KEY = 'gaa-analytics-consent';

const test = base.extend({
  analyticsConsent: ['rejected', { option: true }],
  seedAnalyticsConsent: [async ({ page, analyticsConsent }, use) => {
    if (analyticsConsent) {
      await page.addInitScript(({ key, choice, decidedAt }) => {
        window.localStorage.setItem(key, JSON.stringify({ choice, decidedAt }));
      }, { key: ANALYTICS_CONSENT_KEY, choice: analyticsConsent, decidedAt: Date.now() });
    }
    await use();
  }, { auto: true }],
  blockedThirdPartyRequests: [async ({ page }, use) => {
    const blockedRequests = [];

    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin === LOCAL_ORIGIN) {
        await route.continue();
        return;
      }

      blockedRequests.push(url.href);
      await route.abort('blockedbyclient');
    });

    await use(blockedRequests);
  }, { auto: true }]
});

module.exports = { expect, test };
