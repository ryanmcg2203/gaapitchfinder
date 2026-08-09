const { expect, test } = require('./fixtures');
const { countLabel, filteredPitches, loadPitches } = require('./site-data');

const pitches = loadPitches();

async function openMap(page) {
  await page.goto('/');
  await expect(page.locator('#loading')).toHaveCount(0);
}

async function dispatchRapidInput(page, values) {
  await page.locator('#search-input').evaluate((input, nextValues) => {
    nextValues.forEach(value => {
      input.value = value;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
  }, values);
}

function diagnosticNumber(value) {
  const number = Number(value);
  expect(Number.isFinite(number)).toBe(true);
  return number;
}

test('rapid search and filter changes commit only the latest render', async ({ page }, testInfo) => {
  await openMap(page);

  const map = page.locator('#map');
  const initialRenderCount = diagnosticNumber(await map.getAttribute('data-render-count'));
  const initialMarkerCount = diagnosticNumber(await map.getAttribute('data-marker-creation-count'));
  const initialRenderMs = diagnosticNumber(await map.getAttribute('data-render-duration-ms'));
  expect(initialMarkerCount).toBe(pitches.length);

  const query = 'st brigids';
  const worldwideMatches = filteredPitches(pitches, { query });
  await dispatchRapidInput(page, ['s', 'st', 'st b', 'st bri', query]);

  await expect(page).toHaveURL(url => url.searchParams.get('q') === query);
  expect(diagnosticNumber(await map.getAttribute('data-render-count'))).toBe(initialRenderCount);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(worldwideMatches.length));
  await expect(map).toHaveAttribute('data-render-count', String(initialRenderCount + 1));
  await expect(map).toHaveAttribute('data-rendered-pitch-count', String(worldwideMatches.length));
  await expect(map).toHaveAttribute('data-marker-creation-count', String(initialMarkerCount));
  const searchRenderMs = diagnosticNumber(await map.getAttribute('data-render-duration-ms'));

  await dispatchRapidInput(page, ['d', 'du', 'dub']);
  await page.locator('#sel-region').selectOption('Ireland');
  const irelandMatches = filteredPitches(pitches, { region: 'Ireland', query: 'dub' });
  const renderCountAfterFilter = initialRenderCount + 2;
  await expect(page.locator('#count-badge')).toHaveText(countLabel(irelandMatches.length));
  await expect(map).toHaveAttribute('data-render-count', String(renderCountAfterFilter));
  await page.waitForTimeout(220);
  await expect(map).toHaveAttribute('data-render-count', String(renderCountAfterFilter));
  await expect(map).toHaveAttribute('data-rendered-pitch-count', String(irelandMatches.length));
  await expect(map).toHaveAttribute('data-marker-creation-count', String(initialMarkerCount));
  testInfo.annotations.push({
    type: 'performance',
    description: JSON.stringify({ pitches: pitches.length, initialRenderMs, searchRenderMs })
  });
});

test('a doubled dataset exposes bounded render measurements', async ({ page }, testInfo) => {
  const doubled = pitches.flatMap(pitch => [
    pitch,
    {
      ...pitch,
      c: `${pitch.c} Benchmark Copy`,
      la: Number(pitch.la) + 0.0002,
      lo: Number(pitch.lo) + 0.0002,
      u: '',
      w: ''
    }
  ]);
  await page.route('**/data.json', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify(doubled)
  }));

  const initialStartedAt = Date.now();
  await openMap(page);
  const initialElapsedMs = Date.now() - initialStartedAt;
  const map = page.locator('#map');
  const initialRenderMs = diagnosticNumber(await map.getAttribute('data-render-duration-ms'));
  await expect(map).toHaveAttribute('data-marker-creation-count', String(doubled.length));
  await expect(map).toHaveAttribute('data-render-count', '1');

  const query = 'st brigids';
  const matches = filteredPitches(doubled, { query });
  const searchStartedAt = Date.now();
  await dispatchRapidInput(page, ['s', 'st', 'st b', 'st bri', query]);
  await expect(page.locator('#count-badge')).toHaveText(countLabel(matches.length));
  const searchElapsedMs = Date.now() - searchStartedAt;
  const searchRenderMs = diagnosticNumber(await map.getAttribute('data-render-duration-ms'));

  const measurements = {
    pitches: doubled.length,
    initialElapsedMs,
    initialRenderMs,
    searchElapsedMs,
    searchRenderMs
  };
  testInfo.annotations.push({ type: 'performance', description: JSON.stringify(measurements) });

  expect(initialElapsedMs).toBeLessThan(5000);
  expect(initialRenderMs).toBeLessThan(2000);
  expect(searchElapsedMs).toBeLessThan(2000);
  expect(searchRenderMs).toBeLessThan(1000);
  await expect(map).toHaveAttribute('data-render-count', '2');
  await expect(map).toHaveAttribute('data-rendered-pitch-count', String(matches.length));
  await expect(map).toHaveAttribute('data-marker-creation-count', String(doubled.length));
});
