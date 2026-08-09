const fs = require('node:fs');
const path = require('node:path');
const AxeBuilder = require('@axe-core/playwright').default;
const { expect, test } = require('./fixtures');

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

function firstGeneratedPath(directory) {
  const root = path.resolve(__dirname, `../../site/${directory}`);
  const name = fs.readdirSync(root).find(file => file.endsWith('.html') && file !== 'index.html');
  if (!name) throw new Error(`No generated ${directory} page found`);
  return `/${directory}/${name}`;
}

for (const [name, url] of [
  ['map', '/'],
  ['club directory', '/clubs/'],
  ['county', () => firstGeneratedPath('counties')],
  ['generated club', () => firstGeneratedPath('clubs')],
  ['directions', '/directions.html'],
  ['dataset', '/dataset.html'],
  ['privacy', '/privacy.html']
]) {
  test(`${name} has no serious or critical axe violations`, async ({ page }) => {
    await page.goto(typeof url === 'function' ? url() : url);
    if (name === 'map') await expect(page.locator('#loading')).toHaveCount(0);
    if (name === 'directions') await expect(page.locator('#dir-loading')).toHaveCount(0);
    await expectNoSeriousAxeViolations(page);
  });
}

test('map popup passes axe in dark and light themes', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);
  await page.locator('#cluster-btn').click();
  await page.locator('#random-btn').click();
  await expect(page.locator('.leaflet-popup')).toBeVisible();
  await expectNoSeriousAxeViolations(page);

  await page.locator('#theme-btn').click();
  await expect(page.locator('body')).toHaveClass(/light/);
  await expect(page.locator('#random-btn')).toHaveCSS('color', 'rgb(102, 102, 102)');
  await expect(page.locator('#cluster-btn')).toHaveCSS('color', 'rgb(102, 102, 0)');
  await expectNoSeriousAxeViolations(page);
});

test('keyboard focus remains visible and the club list is reachable without the map', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);
  await page.keyboard.press('Tab');
  const logo = page.locator('.nav-logo');
  await expect(logo).toBeFocused();
  await expect(logo).toHaveCSS('outline-style', 'solid');

  const clubList = page.getByRole('link', { name: 'Club list' });
  await clubList.focus();
  await expect(clubList).toBeFocused();
  await expect(clubList).toHaveCSS('outline-style', 'solid');

  const firstResult = page.locator('.result-row').first();
  await firstResult.focus();
  await expect(firstResult).toBeFocused();
  await expect(firstResult).toHaveCSS('outline-style', 'solid');
  await page.keyboard.press('Enter');
  await expect(firstResult).toHaveAttribute('aria-current', 'true');
  await expect(page.locator('.leaflet-popup')).toBeVisible();
});

test('dataset page exposes stable direct downloads and schema metadata', async ({ page }) => {
  await page.goto('/dataset.html');

  const csv = page.getByRole('link', { name: /Download CSV/ });
  const geojson = page.getByRole('link', { name: /Download GeoJSON/ });
  const schema = page.getByRole('link', { name: /View schema/ });
  await expect(csv).toHaveAttribute('href', '/downloads/gaapitchfinder.csv');
  await expect(csv).toHaveAttribute('download', '');
  await expect(geojson).toHaveAttribute('href', '/downloads/gaapitchfinder.geojson');
  await expect(geojson).toHaveAttribute('download', '');
  await expect(schema).toHaveAttribute('href', '/downloads/schema.json');
  await expect(page.locator('.dataset-facts dt', { hasText: 'Records' })).toBeVisible();
  await expect(page.getByRole('table', { name: 'Dataset field reference table' })).toBeVisible();

  const geojsonResponse = await page.request.get('/downloads/gaapitchfinder.geojson');
  expect(geojsonResponse.ok()).toBe(true);
  const geojsonBody = await geojsonResponse.json();
  expect(geojsonBody.type).toBe('FeatureCollection');
  expect(geojsonBody.features).toHaveLength(1989);

  await page.setViewportSize({ width: 320, height: 800 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await expect(csv).toBeVisible();
  await expect(geojson).toBeVisible();
  await expect(schema).toBeVisible();
});

test('zoom-equivalent and narrow layouts do not overflow or clip controls', async ({ page }) => {
  for (const width of [640, 320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto('/');
    await expect(page.locator('#loading')).toHaveCount(0);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    const selectors = ['#search-input', '#reset-btn', '#mobile-filter-toggle', '#count-badge', '#theme-btn', '#results-toggle'];
    const boxes = [];
    for (const selector of selectors) {
      const locator = page.locator(selector);
      const box = await locator.boundingBox();
      expect(box, `${selector} should be visible at ${width}px`).not.toBeNull();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
      expect(await locator.evaluate(element =>
        element.scrollWidth <= element.clientWidth + 1 && element.scrollHeight <= element.clientHeight + 1
      ), `${selector} should not clip at ${width}px`).toBe(true);
      boxes.push({ box, selector });
    }
    for (let left = 0; left < boxes.length; left += 1) {
      for (let right = left + 1; right < boxes.length; right += 1) {
        const a = boxes[left].box;
        const b = boxes[right].box;
        const overlaps = a.x < b.x + b.width && a.x + a.width > b.x &&
          a.y < b.y + b.height && a.y + a.height > b.y;
        expect(overlaps, `${boxes[left].selector} and ${boxes[right].selector} overlap at ${width}px`).toBe(false);
      }
    }
  }
});
