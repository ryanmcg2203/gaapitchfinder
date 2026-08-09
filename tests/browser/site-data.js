const fs = require('node:fs');
const path = require('node:path');

const DATA_PATH = path.resolve(__dirname, '../../site/data.json');

function loadPitches() {
  if (!fs.existsSync(DATA_PATH)) {
    throw new Error('site/data.json is missing; generate the site before running browser tests');
  }
  return JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));
}

function normalizeSearch(value) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function matchesSearch(pitch, query) {
  const searchable = normalizeSearch(`${pitch.c} ${pitch.p} ${pitch.k} ${pitch.r}`);
  return normalizeSearch(query)
    .split(/\s+/)
    .filter(Boolean)
    .every(term => searchable.includes(term));
}

function filteredPitches(pitches, filters) {
  return pitches.filter(pitch =>
    (!filters.region || pitch.r === filters.region) &&
    (!filters.county || pitch.k === filters.county) &&
    (!filters.club || pitch.c === filters.club) &&
    (!filters.pitch || pitch.p === filters.pitch) &&
    matchesSearch(pitch, filters.query || '')
  );
}

function pitchKey(pitch) {
  return JSON.stringify([
    pitch.c || '', pitch.p || '', pitch.k || '', pitch.r || '',
    Number(pitch.la), Number(pitch.lo)
  ]);
}

function countLabel(count) {
  return `${count.toLocaleString('en-US')} pitch${count === 1 ? '' : 'es'}`;
}

function worldwideSearchCase(pitches) {
  for (const target of pitches.filter(pitch => pitch.r !== 'Ireland' && pitch.c)) {
    const matches = filteredPitches(pitches, { query: target.c });
    if (matches.length && matches.every(pitch => pitch.r !== 'Ireland')) {
      return { matches, target };
    }
  }
  throw new Error('Could not find an overseas-only free-text search case');
}

function dailyOverseasCase(pitches) {
  const start = Date.UTC(2024, 0, 1, 12);
  for (let offset = 0; offset < 3660; offset += 1) {
    const now = start + offset * 24 * 60 * 60 * 1000;
    const dayKey = new Date(now).toISOString().slice(0, 10);
    const target = pitches[dayIndex(dayKey, pitches.length)];
    if (target.r !== 'Ireland') return { now, target };
  }
  throw new Error('Could not find a date with an overseas daily pitch');
}

function dayIndex(key, count) {
  let hash = 2166136261;
  for (let index = 0; index < key.length; index += 1) {
    hash ^= key.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % count;
}

module.exports = {
  countLabel,
  dailyOverseasCase,
  filteredPitches,
  loadPitches,
  pitchKey,
  worldwideSearchCase
};
