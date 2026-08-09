const { test: base, expect } = require('@playwright/test');

const LOCAL_ORIGIN = 'http://127.0.0.1:4173';

const test = base.extend({
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
