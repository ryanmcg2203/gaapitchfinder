const { expect, test } = require('./fixtures');
const { countLabel, filteredPitches, loadPitches } = require('./site-data');

const pitches = loadPitches();

test('mobile navigation and filter disclosures open and close', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);

  const drawer = page.locator('#nav-drawer');
  await expect(drawer).not.toBeVisible();
  await page.getByRole('button', { name: 'Open menu' }).click();
  await expect(drawer).toBeVisible();
  await expect(drawer).toHaveClass(/open/);
  await expect(page.locator('#hamburger')).toHaveAttribute('aria-expanded', 'true');
  await expect(drawer).toHaveAttribute('aria-hidden', 'false');
  await expect(page.locator('#drawer-close')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(drawer).not.toBeVisible();
  await expect(drawer).toHaveAttribute('inert', '');
  await expect(page.locator('#hamburger')).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('#hamburger')).toBeFocused();

  await page.keyboard.press('Tab');
  await expect(page.locator('#drawer-close')).not.toBeFocused();

  const filterToggle = page.locator('#mobile-filter-toggle');
  await expect(page.locator('#sel-region')).not.toBeVisible();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(filterToggle).toHaveAttribute('aria-label', 'Show filters');
  await expect(page.locator('#sel-region')).toHaveAttribute('inert', '');
  await filterToggle.click();
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'true');
  await expect(filterToggle).toHaveAttribute('aria-label', 'Hide filters');
  await expect(filterToggle).toHaveText('Hide');
  await expect(page.locator('#sel-region')).toBeVisible();
  await expect(page.locator('#sel-pitch')).toBeVisible();
  await page.locator('#sel-region').focus();
  await page.keyboard.press('Escape');
  await expect(filterToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(filterToggle).toBeFocused();
  await expect(page.locator('#sel-region')).toHaveAttribute('inert', '');
  await expect(page.locator('#sel-region')).not.toBeVisible();
});

test('rapid mobile search keeps cached markers interactive through view changes', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);

  const map = page.locator('#map');
  const markerCount = String(pitches.length);
  await expect(map).toHaveAttribute('data-marker-creation-count', markerCount);
  const initialRenderCount = Number(await map.getAttribute('data-render-count'));

  const settledQuery = 'galway';
  const settledMatches = filteredPitches(pitches, { query: settledQuery });
  await page.locator('#search-input').fill(settledQuery);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(settledMatches.length));
  await expect(map).toHaveAttribute('data-render-count', String(initialRenderCount + 1));
  await page.getByRole('button', { name: 'Show a random visible pitch' }).click();
  await expect(page.locator('.leaflet-popup')).toBeVisible();
  await expect(map).toHaveAttribute('data-marker-creation-count', markerCount);

  const viewToggle = page.locator('#cluster-btn');
  await viewToggle.click();
  await expect(viewToggle).toHaveText('Cluster');
  await expect(page.locator('.leaflet-popup')).toHaveCount(0);
  await viewToggle.click();
  await expect(viewToggle).toHaveText('Dots');
  await expect(map).toHaveAttribute('data-render-count', String(initialRenderCount + 3));
  await expect(map).toHaveAttribute('data-rendered-pitch-count', String(settledMatches.length));
  await expect(map).toHaveAttribute('data-marker-creation-count', markerCount);

  const query = 'st brigids';
  const matches = filteredPitches(pitches, { query });
  await page.locator('#search-input').evaluate((input, values) => {
    values.forEach(value => {
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
  }, ['s', 'st', 'st b', 'st bri', query]);
  await page.getByRole('button', { name: 'Show a random visible pitch' }).click();

  await expect(page.locator('#count-badge')).toHaveText(countLabel(matches.length));
  await expect(page.locator('.leaflet-popup')).toBeVisible();
  await expect(map).toHaveAttribute('data-render-count', String(initialRenderCount + 4));
  await expect(map).toHaveAttribute('data-rendered-pitch-count', String(matches.length));
  await expect(map).toHaveAttribute('data-marker-creation-count', markerCount);
});
