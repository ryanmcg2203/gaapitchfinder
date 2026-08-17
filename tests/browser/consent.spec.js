const AxeBuilder = require('@axe-core/playwright').default;
const { expect, test } = require('./fixtures');

const CONSENT_KEY = 'gaa-analytics-consent';

test.use({ analyticsConsent: null });

function analyticsRequests(requests) {
  return requests.filter(url => {
    const hostname = new URL(url).hostname;
    return hostname === 'www.googletagmanager.com' || hostname.endsWith('.google-analytics.com');
  });
}

function googleMapRequests(requests) {
  return requests.filter(url => new URL(url).hostname === 'maps.google.com');
}

async function expectNoSeriousAxeViolations(page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const violations = results.violations
    .filter(violation => ['serious', 'critical'].includes(violation.impact))
    .map(({ id, impact, nodes }) => ({
      id,
      impact,
      targets: nodes.map(node => node.target.join(' '))
    }));
  expect(violations).toEqual([]);
}

test('analytics stays off until a visitor makes a choice and rejection persists', async ({ page, blockedThirdPartyRequests }) => {
  await page.goto('/about.html');

  const dialog = page.getByRole('dialog', { name: 'Optional analytics' });
  const reject = page.getByRole('button', { name: 'Reject analytics' });
  const accept = page.getByRole('button', { name: 'Accept analytics' });
  const close = page.getByRole('button', { name: 'Close analytics preferences' });
  await expect(dialog).toBeVisible();
  await expect(reject).toBeVisible();
  await expect(accept).toBeVisible();
  await expect(close).toBeHidden();
  expect(analyticsRequests(blockedThirdPartyRequests)).toEqual([]);
  expect(await page.evaluate(() => typeof window.dataLayer)).toBe('undefined');
  await expectNoSeriousAxeViolations(page);
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    await page.evaluate(() => window.innerWidth)
  );

  await reject.click();
  await expect(dialog).toBeHidden();
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)).choice, CONSENT_KEY)).toBe('rejected');

  await page.goto('/dataset.html');
  await expect(dialog).toBeHidden();
  expect(analyticsRequests(blockedThirdPartyRequests)).toEqual([]);

  const preferences = page.getByRole('button', { name: 'Analytics preferences' });
  await preferences.click();
  await expect(dialog).toBeVisible();
  await expect(close).toBeVisible();
  await expect(page.getByText('Current choice: optional analytics is disabled.')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(preferences).toBeFocused();
});

test('accepting analytics loads the tag and remains effective after navigation', async ({ page, blockedThirdPartyRequests }) => {
  await page.goto('/about.html');
  await page.getByRole('button', { name: 'Accept analytics' }).click();

  await expect.poll(() => analyticsRequests(blockedThirdPartyRequests).length).toBeGreaterThan(0);
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)).choice, CONSENT_KEY)).toBe('accepted');
  expect(await page.evaluate(() => Array.isArray(window.dataLayer))).toBe(true);
  const requestCount = analyticsRequests(blockedThirdPartyRequests).length;

  await page.goto('/dataset.html');
  await expect(page.getByRole('dialog', { name: 'Optional analytics' })).toBeHidden();
  await expect.poll(() => analyticsRequests(blockedThirdPartyRequests).length).toBeGreaterThan(requestCount);
});

test('an expired preference asks again without loading analytics', async ({ page, blockedThirdPartyRequests }) => {
  await page.addInitScript(key => {
    const expiredAt = Date.now() - (181 * 24 * 60 * 60 * 1000);
    localStorage.setItem(key, JSON.stringify({ choice: 'accepted', decidedAt: expiredAt }));
  }, CONSENT_KEY);

  await page.goto('/about.html');

  await expect(page.getByRole('dialog', { name: 'Optional analytics' })).toBeVisible();
  expect(await page.evaluate(key => localStorage.getItem(key), CONSENT_KEY)).toBeNull();
  expect(analyticsRequests(blockedThirdPartyRequests)).toEqual([]);
});

test('an accepted choice can be withdrawn and analytics cookies are cleared', async ({ page, blockedThirdPartyRequests }) => {
  await page.goto('/about.html');
  await page.getByRole('button', { name: 'Accept analytics' }).click();
  await expect.poll(() => analyticsRequests(blockedThirdPartyRequests).length).toBeGreaterThan(0);
  await page.evaluate(() => { document.cookie = '_ga=test-value; path=/'; });

  await page.getByRole('button', { name: 'Analytics preferences' }).click();
  await expect(page.getByText('Current choice: optional analytics is enabled.')).toBeVisible();
  await page.getByRole('button', { name: 'Reject analytics' }).click();

  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)).choice, CONSENT_KEY)).toBe('rejected');
  expect(await page.evaluate(() => window['ga-disable-G-8R6YMPVNWH'])).toBe(true);
  expect(await page.evaluate(() => document.cookie.includes('_ga='))).toBe(false);
  const requestCount = analyticsRequests(blockedThirdPartyRequests).length;

  await page.reload();
  expect(analyticsRequests(blockedThirdPartyRequests)).toHaveLength(requestCount);
  await expect(page.getByRole('dialog', { name: 'Optional analytics' })).toBeHidden();
});

test('the Daily Pitch Google iframe loads only after its separate action', async ({ page, blockedThirdPartyRequests }) => {
  await page.goto('/pitch-of-the-day.html');
  await page.getByRole('button', { name: 'Reject analytics' }).click();
  const loadMap = page.getByRole('button', { name: 'Load Google map' });
  await expect(loadMap).toBeVisible();
  await expect(page.locator('.potd-map iframe')).toHaveCount(0);
  expect(googleMapRequests(blockedThirdPartyRequests)).toEqual([]);

  await loadMap.click();
  await expect(page.locator('.potd-map iframe')).toHaveCount(1);
  await expect.poll(() => googleMapRequests(blockedThirdPartyRequests).length).toBeGreaterThan(0);
});
