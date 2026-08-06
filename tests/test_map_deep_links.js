const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..');

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function inlineScript(file, marker) {
  const html = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(match => match[1]);
  const script = scripts.find(candidate => candidate.includes(marker));
  assert.ok(script, `Could not find script containing ${marker}`);
  return script;
}

class ClassList {
  constructor() {
    this.values = new Set();
  }

  contains(value) {
    return this.values.has(value);
  }

  remove(value) {
    this.values.delete(value);
  }

  toggle(value, force) {
    const enabled = force === undefined ? !this.values.has(value) : force;
    if (enabled) this.values.add(value);
    else this.values.delete(value);
    return enabled;
  }
}

class Element {
  constructor(id = '', isSelect = false) {
    this.id = id;
    this.isSelect = isSelect;
    this.listeners = {};
    this.classList = new ClassList();
    this.options = [];
    this.attributes = {};
    this._innerHTML = '';
    this.value = '';
    this.textContent = '';
    this.hidden = false;
    this.disabled = false;
  }

  set innerHTML(value) {
    this._innerHTML = value;
    if (this.isSelect) {
      this.options = [{ value: '', textContent: '' }];
      this.value = '';
    }
  }

  get innerHTML() {
    return this._innerHTML;
  }

  addEventListener(type, listener) {
    this.listeners[type] = listener;
  }

  appendChild(child) {
    this.options.push(child);
  }

  contains() {
    return false;
  }

  focus() {}

  remove() {
    this.removed = true;
  }

  setAttribute(name, value) {
    this.attributes[name] = value;
  }
}

function createMapHarness(search, data) {
  const elements = new Map();
  const selectIds = new Set(['sel-region', 'sel-county', 'sel-club', 'sel-pitch']);
  const element = id => {
    if (!elements.has(id)) elements.set(id, new Element(id, selectIds.has(id)));
    return elements.get(id);
  };
  const document = {
    body: new Element('body'),
    createElement: () => new Element(),
    getElementById: element,
    addEventListener() {}
  };
  const state = {
    activeLayer: null,
    fitBounds: [],
    opened: [],
    replacedUrls: [],
    setViews: []
  };

  function layer() {
    return {
      markers: [],
      clearLayers() {
        this.markers = [];
      },
      zoomToShowLayer(marker, callback) {
        state.zoomedMarker = marker;
        callback();
      }
    };
  }

  function marker(latLng) {
    return {
      latLng,
      bindPopup() {
        return this;
      },
      addTo(targetLayer) {
        targetLayer.markers.push(this);
        return this;
      },
      openPopup() {
        state.opened.push(this);
      }
    };
  }

  const map = {
    addLayer(targetLayer) {
      if (targetLayer.markers) state.activeLayer = targetLayer;
    },
    removeLayer() {},
    fitBounds(bounds, options) {
      state.fitBounds.push({ bounds, options });
    },
    getZoom() {
      return 7;
    },
    setView(center, zoom) {
      state.setViews.push({ center, zoom });
    }
  };
  const L = {
    tileLayer: () => ({}),
    map: () => map,
    divIcon: options => options,
    marker,
    circleMarker: marker,
    markerClusterGroup: layer,
    layerGroup: layer
  };
  const location = {
    search,
    pathname: '/',
    hash: '',
    href: `https://gaapitchfinder.com/${search}`
  };
  const history = {
    replaceState(_state, _title, nextUrl) {
      state.replacedUrls.push(nextUrl);
      const parsed = new URL(nextUrl, 'https://gaapitchfinder.com');
      location.search = parsed.search;
      location.pathname = parsed.pathname;
      location.hash = parsed.hash;
      location.href = parsed.href;
    }
  };
  const requestAnimationFrame = callback => callback();
  const navigator = {};
  const window = {
    history,
    location,
    matchMedia: () => ({ matches: false }),
    requestAnimationFrame
  };
  const context = {
    URLSearchParams,
    alert() {},
    document,
    fetch: async () => ({ json: async () => data }),
    L,
    navigator,
    requestAnimationFrame,
    setTimeout,
    window
  };

  vm.runInNewContext(inlineScript('site/index.html', 'function currentFilters'), context);
  return { element, elements, map, state };
}

async function settle() {
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
}

async function renderDailyPitch(pitch) {
  const card = new Element('potd-card');
  const date = new Element('potd-date');
  const document = {
    getElementById(id) {
      return id === 'potd-card' ? card : date;
    }
  };
  const context = {
    Date,
    Intl,
    URLSearchParams,
    document,
    fetch: async () => ({ json: async () => [pitch] })
  };

  vm.runInNewContext(inlineScript('site/pitch-of-the-day.html', 'function renderPitch'), context);
  await settle();
  const match = card.innerHTML.match(/<a href="([^"]+)">Find on the map<\/a>/);
  assert.ok(match, 'Daily pitch did not render its map link');
  return match[1].replaceAll('&amp;', '&');
}

test('free-text search ignores only the implicit Ireland region', async () => {
  const data = [
    { c: 'Home Club', p: 'Main Pitch', k: 'Galway', r: 'Ireland', la: 53.2, lo: -9.1 },
    { c: 'London Club', p: 'Overseas Ground', k: 'England', r: 'Britain', la: 51.5, lo: -0.1 }
  ];
  const implicit = createMapHarness('?q=London', data);
  await settle();

  assert.equal(implicit.element('sel-region').value, '');
  assert.deepEqual(implicit.element('sel-county').options.map(option => option.value), ['', 'England', 'Galway']);
  assert.deepEqual(implicit.element('sel-club').options.map(option => option.value), ['', 'Home Club', 'London Club']);
  assert.deepEqual(implicit.element('sel-pitch').options.map(option => option.value), ['', 'Main Pitch', 'Overseas Ground']);
  assert.equal(implicit.element('count-badge').textContent, '1 pitch');
  assert.deepEqual(plain(implicit.state.activeLayer.markers.map(item => item.latLng)), [[51.5, -0.1]]);
  assert.deepEqual(plain(implicit.state.fitBounds.at(-1).bounds), [[51.5, -0.1]]);
  assert.equal(implicit.state.replacedUrls.at(-1), '/?q=London');

  implicit.element('search-clear').listeners.click();
  assert.equal(implicit.element('sel-region').value, 'Ireland');
  assert.deepEqual(implicit.element('sel-county').options.map(option => option.value), ['', 'Galway']);
  assert.deepEqual(implicit.element('sel-club').options.map(option => option.value), ['', 'Home Club']);
  assert.deepEqual(implicit.element('sel-pitch').options.map(option => option.value), ['', 'Main Pitch']);
  assert.equal(implicit.element('count-badge').textContent, '1 pitch');
  assert.deepEqual(plain(implicit.state.activeLayer.markers.map(item => item.latLng)), [[53.2, -9.1]]);
  assert.equal(implicit.state.replacedUrls.at(-1), '/');

  implicit.element('search-input').value = 'London';
  implicit.element('search-input').listeners.input();
  assert.equal(implicit.element('sel-region').value, '');
  assert.equal(implicit.element('count-badge').textContent, '1 pitch');
  implicit.element('reset-btn').listeners.click();
  assert.equal(implicit.element('sel-region').value, 'Ireland');
  assert.equal(implicit.element('count-badge').textContent, '1 pitch');
  assert.deepEqual(plain(implicit.state.activeLayer.markers.map(item => item.latLng)), [[53.2, -9.1]]);
  assert.equal(implicit.state.replacedUrls.at(-1), '/');
  assert.deepEqual(plain(implicit.state.setViews.at(-1)), { center: [53.5, -8], zoom: 7 });

  const explicit = createMapHarness('?region=Ireland&q=London', data);
  await settle();
  assert.equal(explicit.element('sel-region').value, 'Ireland');
  assert.deepEqual(explicit.element('sel-county').options.map(option => option.value), ['', 'Galway']);
  assert.equal(explicit.element('count-badge').textContent, '0 pitches');
  assert.equal(explicit.state.replacedUrls.at(-1), '/?region=Ireland&q=London');
});

test('Daily Pitch links open the intended marker and retain exact filters', async () => {
  const target = {
    c: "London Eire Og",
    p: 'Main Ground',
    k: 'England',
    r: 'Britain',
    la: 51.501,
    lo: -0.101
  };
  const link = await renderDailyPitch(target);
  const deepLink = new URL(link, 'https://gaapitchfinder.com');

  assert.equal(deepLink.searchParams.get('region'), target.r);
  assert.equal(deepLink.searchParams.get('county'), target.k);
  assert.equal(deepLink.searchParams.get('club'), target.c);
  assert.equal(deepLink.searchParams.get('pitch'), target.p);
  assert.equal(deepLink.searchParams.get('q'), target.c);
  assert.ok(deepLink.searchParams.get('focus'));

  const sameFilters = { ...target, la: 51.6, lo: -0.2 };
  const ireland = { c: 'Home Club', p: 'Main Pitch', k: 'Galway', r: 'Ireland', la: 53.2, lo: -9.1 };
  const mapPage = createMapHarness(deepLink.search, [sameFilters, target, ireland]);
  await settle();

  assert.equal(mapPage.element('count-badge').textContent, '2 pitches');
  assert.deepEqual(plain(mapPage.state.opened.map(item => item.latLng)), [[target.la, target.lo]]);
  assert.deepEqual(plain(mapPage.state.fitBounds.at(-1).bounds), [
    [sameFilters.la, sameFilters.lo],
    [target.la, target.lo]
  ]);
  const roundTripped = new URL(mapPage.state.replacedUrls.at(-1), 'https://gaapitchfinder.com');
  assert.equal(roundTripped.searchParams.get('focus'), deepLink.searchParams.get('focus'));
  assert.equal(roundTripped.searchParams.get('region'), target.r);
});
