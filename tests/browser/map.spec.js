const { expect, test } = require('./fixtures');
const {
  countLabel,
  dailyOverseasCase,
  filteredPitches,
  loadPitches,
  pitchKey,
  worldwideSearchCase
} = require('./site-data');

const pitches = loadPitches();
const irelandPitches = pitches.filter(pitch => pitch.r === 'Ireland');

function distanceKm(aLat, aLng, bLat, bLng) {
  const toRad = value => value * Math.PI / 180;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const lat1 = toRad(aLat);
  const lat2 = toRad(bLat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

async function openMap(page, path = '/') {
  await page.goto(path);
  await expect(page.locator('#loading')).toHaveCount(0);
  await expect(page.locator('#map')).toHaveClass(/leaflet-container/);
}

test('loads the generated map with Ireland selected by default', async ({
  blockedThirdPartyRequests,
  page
}) => {
  await openMap(page);

  await expect(page.locator('#sel-region')).toHaveValue('Ireland');
  await expect(page.locator('.site-nav')).toHaveCSS('height', '64px');
  await expect(page.locator('#count-badge')).toHaveText(countLabel(irelandPitches.length));
  await expect(page.locator('#results-summary')).toHaveText(`${irelandPitches.length.toLocaleString('en-US')} matching pitches`);
  await expect(page.locator('.result-row')).toHaveCount(60);
  await expect(page.locator('#results-range')).toHaveText(`1–60 of ${irelandPitches.length.toLocaleString('en-US')}`);
  const firstResult = page.locator('.result-row').first();
  await expect(firstResult).toContainText(irelandPitches[0].c);
  await expect(firstResult).toContainText(irelandPitches[0].p);
  await expect(firstResult).toContainText(irelandPitches[0].k);
  await page.getByRole('button', { name: 'Next results' }).click();
  await expect(page.locator('#results-range')).toHaveText(`61–120 of ${irelandPitches.length.toLocaleString('en-US')}`);
  await page.getByRole('button', { name: 'Previous results' }).click();
  await expect(page.locator('#results-range')).toHaveText(`1–60 of ${irelandPitches.length.toLocaleString('en-US')}`);
  expect(blockedThirdPartyRequests.some(url => url.includes('googletagmanager.com'))).toBe(true);
  expect(blockedThirdPartyRequests.some(url => url.includes('basemaps.cartocdn.com'))).toBe(true);
});

test('result rows and markers keep selection, details, and result pages synchronized', async ({ page }) => {
  await openMap(page);

  const firstRow = page.locator('.result-row').first();
  const firstIndex = Number(await firstRow.getAttribute('data-pitch-index'));
  const firstPitch = pitches[firstIndex];
  await firstRow.click();

  await expect(firstRow).toHaveAttribute('aria-current', 'true');
  await expect(page.locator('.leaflet-popup')).toBeVisible();
  await expect(page.locator('.leaflet-popup')).toContainText(firstPitch.c);
  await expect(page).toHaveURL(url => url.searchParams.get('focus') === pitchKey(firstPitch));
  await page.waitForFunction(target => {
    const center = map.getCenter();
    return Math.abs(center.lat - target.la) < 0.001 && Math.abs(center.lng - target.lo) < 0.001;
  }, firstPitch);

  const laterIndex = pitches.findIndex((pitch, index) => index > 180 && pitch.r === 'Ireland');
  const laterPitch = pitches[laterIndex];
  await page.evaluate(index => allClubs[index]._marker.fire('click'), laterIndex);
  const selectedRow = page.locator(`.result-row[data-pitch-index="${laterIndex}"]`);
  await expect(selectedRow).toHaveAttribute('aria-current', 'true');
  await expect(selectedRow).toContainText(laterPitch.c);
  await expect(page).toHaveURL(url => url.searchParams.get('focus') === pitchKey(laterPitch));
  await expect(page.locator('#results-range')).not.toHaveText(/^1–60/);
});

test('Near me shows the five nearest pitches with distances', async ({ page }) => {
  const origin = { latitude: Number(pitches[0].la), longitude: Number(pitches[0].lo) };
  const expectedIndices = pitches
    .map((pitch, index) => ({
      index,
      distance: distanceKm(origin.latitude, origin.longitude, Number(pitch.la), Number(pitch.lo))
    }))
    .sort((left, right) => left.distance - right.distance)
    .slice(0, 5)
    .map(result => result.index);
  await page.addInitScript(coords => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition(success) {
          setTimeout(() => success({ coords }), 0);
        }
      }
    });
  }, origin);
  await openMap(page);
  const workspaceBefore = await page.locator('#map-workspace').boundingBox();

  await page.getByRole('button', { name: 'Find pitches near me' }).click();
  await expect(page.locator('#count-badge')).toHaveText('5 nearby');
  await expect(page.locator('#results-summary')).toHaveText('5 nearest pitches');
  await expect(page.locator('.result-row')).toHaveCount(5);
  await expect(page.locator('.result-distance')).toHaveCount(5);
  await expect(page.locator('.result-row').first()).toHaveAttribute('data-pitch-index', String(expectedIndices[0]));
  await expect(page.locator('#results-notice')).toHaveText('Sorted by distance from your location.');
  await expect(page.locator('#map')).toHaveAttribute('data-rendered-pitch-count', '5');
  await expect.poll(async () => (await page.locator('#map-workspace').boundingBox()).y).toBe(workspaceBefore.y);
});

test('results expose loading, empty, and data-error states', async ({ page }) => {
  let releaseData;
  await page.route('**/data.json', async route => {
    await new Promise(resolve => { releaseData = resolve; });
    await route.continue();
  });
  await page.goto('/');
  await expect(page.locator('#results-state')).toHaveAttribute('data-state', 'loading');
  await expect(page.locator('#results-state')).toContainText('Loading pitches');
  await expect.poll(() => Boolean(releaseData)).toBe(true);
  releaseData();
  await expect(page.locator('#loading')).toHaveCount(0);

  await page.locator('#search-input').fill('no pitch can possibly match this value');
  await expect(page.locator('#results-state')).toHaveAttribute('data-state', 'empty');
  await expect(page.locator('#results-state')).toContainText('No pitches match');
  await expect(page.locator('.result-row')).toHaveCount(0);
});

test('a failed data request offers a retry state', async ({ page }) => {
  await page.route('**/data.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/');

  await expect(page.locator('#loading')).toHaveText('Failed to load pitch data');
  await expect(page.locator('#results-state')).toHaveAttribute('data-state', 'error');
  await expect(page.locator('#results-state')).toContainText('could not be loaded');
  await expect(page.locator('#results-retry')).toBeVisible();
});

test('free-text search reaches worldwide pitches while explicit regions stay scoped', async ({ page }) => {
  const searchCase = worldwideSearchCase(pitches);
  await openMap(page);

  await page.locator('#search-input').fill(searchCase.target.c);
  await expect(page.locator('#sel-region')).toHaveValue('');
  await expect(page.locator('#count-badge')).toHaveText(countLabel(searchCase.matches.length));
  await expect(page).toHaveURL(url => url.searchParams.get('q') === searchCase.target.c);

  const explicitRegion = 'Great Britain';
  const regionPitches = pitches.filter(pitch => pitch.r === explicitRegion);
  await page.getByLabel('Clear search').click();
  await page.locator('#sel-region').selectOption(explicitRegion);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(regionPitches.length));
  await expect(page).toHaveURL(url => url.searchParams.get('region') === explicitRegion);

  await page.locator('#search-input').fill(searchCase.target.c);
  const scopedMatches = filteredPitches(pitches, {
    query: searchCase.target.c,
    region: explicitRegion
  });
  await expect(page.locator('#sel-region')).toHaveValue(explicitRegion);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(scopedMatches.length));
});

test('deep links survive reload and reset to the default map state', async ({ page }) => {
  const target = pitches.find(pitch =>
    pitch.r !== 'Ireland' && pitch.k && pitch.c && pitch.p
  );
  const filters = {
    region: target.r,
    county: target.k,
    club: target.c,
    pitch: target.p,
    query: target.c
  };
  const params = new URLSearchParams({
    region: filters.region,
    county: filters.county,
    club: filters.club,
    pitch: filters.pitch,
    q: filters.query
  });
  const expectedCount = filteredPitches(pitches, filters).length;

  await openMap(page, `/?${params}`);
  await expect(page.locator('#sel-region')).toHaveValue(filters.region);
  await expect(page.locator('#sel-county')).toHaveValue(filters.county);
  await expect(page.locator('#sel-club')).toHaveValue(filters.club);
  await expect(page.locator('#sel-pitch')).toHaveValue(filters.pitch);
  await expect(page.locator('#search-input')).toHaveValue(filters.query);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(expectedCount));

  await page.reload();
  await expect(page.locator('#loading')).toHaveCount(0);
  await expect(page.locator('#sel-region')).toHaveValue(filters.region);
  await expect(page.locator('#sel-club')).toHaveValue(filters.club);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(expectedCount));

  await page.getByRole('button', { name: 'Reset filters' }).click();
  await expect(page).toHaveURL('http://127.0.0.1:4173/');
  await expect(page.locator('#sel-region')).toHaveValue('Ireland');
  await expect(page.locator('#sel-county')).toHaveValue('');
  await expect(page.locator('#sel-club')).toHaveValue('');
  await expect(page.locator('#sel-pitch')).toHaveValue('');
  await expect(page.locator('#search-input')).toHaveValue('');
  await expect(page.locator('#count-badge')).toHaveText(countLabel(irelandPitches.length));
});

test('switches between clustered and dot marker modes', async ({ page }) => {
  await openMap(page);
  const toggle = page.locator('#cluster-btn');

  await expect(toggle).toHaveText('Dots');
  await expect(toggle).toHaveAttribute('aria-label', 'Switch to dots view');
  await toggle.click();
  await expect(toggle).toHaveText('Cluster');
  await expect(toggle).toHaveClass(/dots-active/);
  await expect(toggle).toHaveAttribute('aria-label', 'Switch to cluster view');
  await expect(page.locator('#count-badge')).toHaveText(countLabel(irelandPitches.length));

  await toggle.click();
  await expect(toggle).toHaveText('Dots');
  await expect(toggle).not.toHaveClass(/dots-active/);
});

test('an overseas daily pitch opens its intended map marker', async ({
  blockedThirdPartyRequests,
  page
}) => {
  const dailyCase = dailyOverseasCase(pitches);
  await page.addInitScript(now => {
    const RealDate = Date;
    class FixedDate extends RealDate {
      constructor(...args) {
        super(...(args.length ? args : [now]));
      }

      static now() {
        return now;
      }
    }
    window.Date = FixedDate;
  }, dailyCase.now);

  await page.goto('/pitch-of-the-day.html');
  await expect(page.locator('#potd-card h2')).toHaveText(dailyCase.target.c);
  await expect(page.locator('.potd-meta')).toContainText(dailyCase.target.r);
  expect(blockedThirdPartyRequests.some(url => url.includes('maps.google.com/maps'))).toBe(true);

  await page.getByRole('link', { name: 'Find on the map' }).click();
  await expect(page.locator('#loading')).toHaveCount(0);
  await expect(page).toHaveURL(url => url.searchParams.get('focus') === pitchKey(dailyCase.target));
  await expect(page.locator('#sel-region')).toHaveValue(dailyCase.target.r);
  await expect(page.locator('#sel-county')).toHaveValue(dailyCase.target.k);
  await expect(page.locator('#sel-club')).toHaveValue(dailyCase.target.c);
  await expect(page.locator('#sel-pitch')).toHaveValue(dailyCase.target.p);
  const expectedCount = filteredPitches(pitches, {
    region: dailyCase.target.r,
    county: dailyCase.target.k,
    club: dailyCase.target.c,
    pitch: dailyCase.target.p,
    query: dailyCase.target.c
  }).length;
  await expect(page.locator('#count-badge')).toHaveText(countLabel(expectedCount));
  await page.waitForFunction(target => {
    const center = map.getCenter();
    return Math.abs(center.lat - target.la) < 0.001 && Math.abs(center.lng - target.lo) < 0.001;
  }, dailyCase.target);
});
