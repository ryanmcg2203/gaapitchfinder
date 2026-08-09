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
  await expect(page.locator('#count-badge')).toHaveText(countLabel(irelandPitches.length));
  expect(blockedThirdPartyRequests.some(url => url.includes('googletagmanager.com'))).toBe(true);
  expect(blockedThirdPartyRequests.some(url => url.includes('basemaps.cartocdn.com'))).toBe(true);
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
