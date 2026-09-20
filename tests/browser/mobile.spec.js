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

test('mobile results expand below the map without covering controls', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);

  const panel = page.locator('#results-panel');
  const map = page.locator('#map');
  const toggle = page.locator('#results-toggle');
  const collapsedMapBox = await map.boundingBox();
  await expect(panel).not.toHaveClass(/results-expanded/);
  await expect(page.locator('#results-body')).toHaveAttribute('inert', '');
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');

  await toggle.click();
  await expect(panel).toHaveClass(/results-expanded/);
  await expect(page.locator('#results-body')).not.toHaveAttribute('inert', '');
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.result-row')).toHaveCount(60);
  await expect.poll(async () => {
    const currentMapBox = await map.boundingBox();
    const currentPanelBox = await panel.boundingBox();
    return currentMapBox.y + currentMapBox.height - currentPanelBox.y;
  }).toBeLessThanOrEqual(1);

  const mapBox = await map.boundingBox();
  const panelBox = await panel.boundingBox();
  const infoBox = await page.locator('#info-btn').boundingBox();
  expect(mapBox.height).toBeGreaterThan(250);
  expect(mapBox.y + mapBox.height).toBeLessThanOrEqual(panelBox.y + 1);
  expect(infoBox.y + infoBox.height).toBeLessThanOrEqual(mapBox.y + mapBox.height);

  const firstRow = page.locator('.result-row').first();
  await firstRow.click();
  await expect(firstRow).toHaveAttribute('aria-current', 'true');
  await expect(page.locator('.leaflet-popup')).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(panel).not.toHaveClass(/results-expanded/);
  await expect(toggle).toBeFocused();
  await expect.poll(async () => (await map.boundingBox()).height).toBeGreaterThan(collapsedMapBox.height - 1);
});

test('mobile Near me reports denied location access in the results sheet', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition(_success, error) {
          setTimeout(() => error({ code: 1 }), 0);
        }
      }
    });
  });
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);

  await page.getByRole('button', { name: 'Find pitches near me' }).click();
  await expect(page.locator('#results-panel')).toHaveClass(/results-expanded/);
  await expect(page.locator('#results-notice')).toHaveAttribute('data-tone', 'error');
  await expect(page.locator('#results-notice')).toContainText('Location access was denied');
  await expect(page.locator('.result-row')).toHaveCount(60);
});

for (const target of [
  { club: 'CLG Cárna-Caiseal', pitch: '' },
  { club: 'Father Griffins/Éire Óg', pitch: 'South Park, The Claddagh' },
  { club: 'Father Griffins/Éire Óg', pitch: 'Crestwood GAA Pitch' }
]) {
  test(`rapid mobile search keeps cached markers interactive through view changes: ${target.club} ${target.pitch}`, async ({ page }) => {
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
    // Cover both the previously failing zoom transition and a shared-coordinate
    // marker that needs spiderfying, rather than relying on a random CI sample.
    const targetIndex = settledMatches.findIndex(pitch => pitch.c === target.club && pitch.p === target.pitch);
    expect(targetIndex).toBeGreaterThanOrEqual(0);
    await page.evaluate(value => { Math.random = () => value; }, (targetIndex + 0.5) / settledMatches.length);
    await page.getByRole('button', { name: 'Show a random visible pitch' }).click();
    await expect(page.locator('.leaflet-popup')).toBeVisible();
    await expect(page.locator('.leaflet-popup .pop-club')).toHaveText(target.club);
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
}
