# Blog roadmap

Last reviewed: 17 August 2026

This roadmap turns the project history and current engineering work into a
small number of useful public stories. It is an editorial queue, not a promise
to publish on a fixed schedule.

The detailed source record lives in [project-history.md](project-history.md).

## Editorial approach

- Give each article one clear reader question rather than listing every change.
- Prefer first-hand detail, maps, screenshots, and reproducible analysis over a
  generic project update.
- Link to the dataset, methodology, and correction route where relevant.
- Describe data requests as requests unless a resulting publication or product
  can be shown.
- Label account metrics with their exact measurement window. Do not add
  overlapping Search Console periods or equate views with unique people.
- Redact personal details from email excerpts and obtain permission before
  quoting correspondents by name.
- Use an agent to research and draft, but require human review before publishing.

Daily analytics can feed a private report or issue comment, but daily public
posts would be repetitive and produce weak search pages. A monthly or quarterly
insight post, supplemented by genuine project milestones, is the stronger
public cadence. Issue
[#122](https://github.com/ryanmcg2203/gaapitchfinder/issues/122) can provide the
privacy-safe analytics source for that series.

## Recommended publishing order

| Priority | Working title | Reader promise | Evidence readiness | Effort |
| --- | --- | --- | --- | --- |
| 1 | From a Summer Spreadsheet to Nearly 2,000 GAA Pitches | The human and technical story from 2017 to the open site | High, with a few labelled gaps | Medium |
| 2 | How a Missing GAA Pitch Gets Fixed | What happens after a club or supporter sends an email | High | Small |
| 3 | What Does "Good" GAA Pitch Data Mean? | Why entrances, second grounds, names, and provenance matter | High | Medium |
| 4 | Rebuilding GAA Pitch Finder for Mobile | How search, map results, and marker interactions evolved | High in Git and screenshots | Medium |
| 5 | Opening the Dataset Properly | Why CSV alone was not enough, and what schema, GeoJSON, licensing, and quality reports add | High | Medium |
| 6 | The Quiet Work Behind a Small Public Website | Costs, consent, accessibility, tests, deploys, and maintenance | High | Medium |
| 7 | Mapping GAA's Football and Hurling Strongholds | How open club locations supported the Maynooth/RTÉ work | Public outcome ready; collaboration detail needs review | Medium |
| 8 | Where OpenStreetMap Still Misses GAA Pitches | A reproducible coverage report and invitation to improve OSM | Tooling ready; national coverage incomplete | Medium |
| 9 | GAA Pitch Finder by the Numbers | A periodic, privacy-safe search and usage report | Depends on #122 | Small per edition |
| 10 | The App Versions That Never Shipped | What the 2018 and 2022 prototypes taught the project | Private archive ready; needs careful framing | Medium |

The first six form a coherent initial series. Later posts can be published when
their analysis or source material is genuinely ready.

## Article briefs

### 1. From a Summer Spreadsheet to Nearly 2,000 GAA Pitches

**Angle:** a personal problem became a durable open geospatial resource over
nearly a decade.

**Include:**

- the June 2017 origin and manual coordinate-by-coordinate research;
- v1.0, the January 2018 Reddit/SportsJOE moment, and early corrections;
- the Google Maps, Tableau, and Leaflet phases;
- international expansion and the move to open data;
- the 2026 migration and current 1,989-record snapshot;
- an honest note that maintenance, not initial collection, is the enduring job.

**Assets:** one image from each public interface, an early spreadsheet crop with
personal metadata removed, and a current world map.

**Verify first:** original host, stable Reddit capture, and whether an original
My Map screenshot exists. The story can publish without these if they are named
as gaps.

### 2. How a Missing GAA Pitch Gets Fixed

**Angle:** email is a feature, not a temporary workaround. It meets contributors
where they already are and keeps the correction process approachable.

**Include:**

- anonymised examples of a missing second ground, a moved entrance, a renamed
  club, and a defunct or shared facility;
- the checks used before changing the canonical CSV;
- how validation, pull requests, and deployment now carry a correction safely
  to the live map;
- what details make an email actionable: club, pitch, map link, and a short
  explanation;
- the distinction between a pitch centre and a usable arrival point.

**Call to action:** report a correction by email. A structured web form can
remain optional rather than replacing the workflow that already works.

### 3. What Does "Good" GAA Pitch Data Mean?

**Angle:** coordinates are only the beginning of a trustworthy sports dataset.

**Include:**

- completeness, validity, uniqueness, freshness, provenance, and accessibility;
- examples of second grounds, shared overseas facilities, aliases, entrances,
  and club status;
- what the public data-quality dashboard checks today;
- what it cannot yet verify automatically;
- the next foundational fields: stable pitch IDs and verification metadata.

**Assets:** compact screenshots from the data-quality page and one anonymised
data diff.

### 4. Rebuilding GAA Pitch Finder for Mobile

**Angle:** mobile search was identified as a limitation in 2018; the 2026 rebuild
finally made it a first-class workflow.

**Include:**

- the original SportsJOE observation;
- why a map alone is awkward after repeated taps on a phone;
- search, filters, Near me, deep links, the results drawer, and marker clusters;
- accessibility and browser-regression work;
- before-and-after screenshots at the same viewport.

**Avoid:** a commit-by-commit changelog. Frame technical decisions through a
person trying to get directions before a match.

### 5. Opening the Dataset Properly

**Angle:** publishing a CSV was the turning point, but a genuinely reusable
dataset also needs stable URLs, documented fields, licensing, machine-readable
formats, and reproducible releases.

**Include:**

- the change from selective email attachments to the 2024 GitHub repository;
- the canonical CSV and derived-data boundary;
- CSV, GeoJSON, and schema downloads;
- CC BY 4.0 attribution;
- deterministic builds and the data-quality report;
- one small example using the GeoJSON in a GIS tool or notebook.

### 6. The Quiet Work Behind a Small Public Website

**Angle:** the features people notice depend on unglamorous operational work.

**Include:**

- replacing a EUR 204 annual website plan with GitHub Pages while retaining
  separate domain costs;
- consent-first analytics and why optional embeds differ;
- accessibility, link auditing, browser tests, and deployment checks;
- the August 2026 GitHub Actions outage as a reminder that hosted automation is
  useful but not infallible;
- how a static architecture keeps the ongoing burden low.

**Verify first:** use billing screenshots only if amounts and dates are legible
and unrelated account details are removed.

### 7. Mapping GAA's Football and Hurling Strongholds

**Angle:** open location data becomes more valuable when another dataset gives
it historical or sporting context.

**Include:**

- the 2024 Maynooth contact;
- the challenge of club names, mergers, and playing-code classification;
- the July 2025 RTÉ Brainstorm outcome;
- what GAA Pitch Finder supplied and what the researchers created.

**Dependency:** ask the researchers whether they are comfortable with the
collaboration story and whether maps or methods can be reproduced or embedded.
Link prominently to their article rather than retelling its analysis.

### 8. Where OpenStreetMap Still Misses GAA Pitches

**Angle:** compare a community-maintained point dataset with community-maintained
ground geometry, then make the gaps actionable.

**Include:**

- how nearby OSM candidates are matched;
- coverage by county and the meaning of each status;
- false-positive and false-negative caveats;
- how adding pitch outlines can support dimensions and orientation later;
- a clear contribution route that respects OSM's own editing practices.

**Dependency:** complete enough county coverage to avoid presenting a partial
snapshot as a national league table.

### 9. GAA Pitch Finder by the Numbers

**Angle:** a periodic report about what people look for, what data is improving,
and where the project needs help.

**Cadence:** monthly while the insights pipeline is being evaluated, then move
to quarterly unless each month produces a genuinely different story.

**Possible sections:**

- non-identifying search and page trends;
- top-level dataset growth and correction counts;
- counties or regions with the largest quality gaps;
- one completed improvement;
- one concrete call for verification help.

**Guardrails:** never expose individual user paths, precise low-volume
locations, identifiers, or raw analytics exports. Keep generated drafts as
drafts until reviewed.

### 10. The App Versions That Never Shipped

**Angle:** several sincere prototypes explored the right product questions even
though they never became public apps.

**Include:**

- the Android builds and later iOS exploration;
- bundled spreadsheet versus central database debates;
- why corrections and freshness pushed toward a shared source of truth;
- why a responsive web app ultimately matched the project's maintenance budget;
- lessons without naming or blaming collaborators.

## Data-story reserve

These can become strong posts after the underlying analysis is rerun and the
method is documented:

- rainfall patterns across GAA pitches;
- the highest and lowest grounds, revisiting the 2025 elevation article;
- island and remote pitches, revisiting the 2023 distance methodology;
- shared, temporary, and seasonal grounds in international GAA;
- the point in Ireland furthest from any mapped GAA pitch;
- changes in the dataset over time once stable `pitch_id` values exist;
- Irish-language names, aliases, and what they teach us about map search.

## Reusable article structure

1. Open with the practical question or moment that made the work necessary.
2. Show the evidence or map before explaining the implementation.
3. Explain the method and its limitations in plain language.
4. Link to the relevant data, code, or outside research.
5. End with one useful action: find a pitch, download data, report a correction,
   or help verify a gap.

## Publication checklist

- Confirm names, dates, record counts, and metric windows against the project
  history and source material.
- Rerun data analysis against a named dataset revision.
- Add descriptive alt text and check mobile image crops.
- Link to primary sources and mark inference as inference.
- Obtain permission for named correspondence or private screenshots.
- Remove email addresses, order IDs, account IDs, and unrelated personal data.
- Add article metadata, canonical URL, social image, and previous/next links.
- Run the repository unit, site-audit, accessibility, and browser checks.
- Review the final generated page, not only the source template.
