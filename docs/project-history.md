# GAA Pitch Finder project history

Last reviewed: 17 August 2026

This is the maintainer's working history of GAA Pitch Finder. It preserves the
project's origin, technical changes, public impact, and unresolved questions in
one place. It is deliberately more detailed than the public About page and can
be used as source material for future articles, talks, funding applications,
and archival work.

## Evidence labels

Statements in this document use the following evidence levels:

- **Public**: supported by a public article or page that can be linked.
- **Repository**: supported by Git history, releases, source files, or generated
  metadata in this repository.
- **Owner archive**: supported by Ryan McGuinness's email, analytics, billing,
  donation, or account records. These records are not public by default.
- **Recollection**: based on Ryan's first-hand memory but not yet tied to a
  preserved contemporary record.
- **Open question**: plausible or partly supported, but not ready to state as a
  settled public fact.

These labels are about traceability, not importance. Private correspondence is
often the best evidence for a small personal project, but it should not be
presented as independently verifiable without an archived extract or capture.

## Short history

GAA Pitch Finder began in June 2017, when Ryan McGuinness spent a summer
manually researching GAA clubs and locating their grounds. Some club websites
and Google Maps listings provided useful clues, but no complete national
dataset existed. Over approximately three months, Ryan opened locations in
Google Maps, extracted their coordinates, and recorded them in a master
spreadsheet stored in his personal Google Drive. **[Recollection, Owner archive]**

The first version launched as a custom Google Map on 27 October 2017. After it
was shared on Reddit in January 2018, the project attracted approximately
21,000 map views, around 550 Reddit upvotes, and coverage from SportsJOE. Clubs
and supporters quickly began submitting missing grounds and corrections,
establishing the community-maintained model that continues today. **[Public,
Owner archive]**

GAA Pitch Finder later moved to a Squarespace website and, in December 2020,
migrated its map to Tableau Public. It expanded internationally in January
2021 and has since supported clubs, county boards, universities, researchers,
GIS teams, and public-interest projects. Maynooth University research using the
dataset was published by RTÉ Brainstorm in July 2025. **[Public, Owner archive]**

The underlying dataset was published openly on GitHub in February 2024. In
June 2026, the website was rebuilt with Codex-assisted development using
Leaflet, GitHub Pages, and GitHub Actions. The migration created an openly
licensed, automated platform and allowed the annual Squarespace website plan
to be cancelled. **[Public, Repository, Owner archive]**

As of 6 August 2026, the canonical dataset contained 1,989 pitch records across
Ireland and the wider world. **[Repository]**

## Timeline

### 2017: Building the first national dataset

- **June:** work began during the summer between university and employment.
  The idea combined an interest in maps with a recurring family problem:
  rural GAA grounds could be unexpectedly difficult to find. **[Recollection]**
- **June to October:** club and county websites, existing maps, and Google Maps
  were checked manually. Coordinates, club names, pitch names, and directions
  were assembled in a master spreadsheet in Google Drive. The initial
  compilation took roughly three months. **[Recollection, Owner archive]**
- **27 October:** v1.0 launched with club pitches across Ireland's four
  provinces, the first logo, and a custom Google Maps/My Maps presentation.
  **[Public: [Pitch Finder v1.0](https://gaapitchfinder.com/blog/pitch-finder-v10.html)]**
- **4 November:** v1.1 added county grounds and Google Maps directions for each
  location. **[Public: [Pitch Finder v1.1](https://gaapitchfinder.com/blog/pitch-finder-v11.html)]**

The platform that hosted the website around the original embedded map is not
yet confirmed. Squarespace did not begin until December 2019.

### 2018: Public attention and community corrections

- **21 January:** the project was posted to Reddit. Surviving comments show
  immediate interest, sharing, mobile and search requests, and corrections.
  The original author and post body now appear as deleted. **[Public, Owner
  archive]**
- **21 January:** SportsJOE published
  ["Monaghan man spent months developing map of every GAA ground in Ireland and we love it"](https://www.sportsjoe.ie/sport/gaa/monaghan-man-spent-months-developing-map-every-gaa-ground-ireland-love-148052).
  It documented the motivation, the months of mapping work, the directions
  feature, and mobile search as an early limitation. **[Public]**
- **21-28 January:** missing pitches and corrections began arriving, including
  Renvyle and Inis Oirr. This established email and social feedback as the
  project's practical maintenance workflow. **[Owner archive]**
- **28 January:** the v2.0 post recorded 21,483 map views, 9,000 site views,
  roughly 550 Reddit upvotes, and 2,000 Instagram likes attributed to the
  gaafanzone page. **[Public: [Pitch Finder 2.0](https://gaapitchfinder.com/blog/pitch-finder-20.html)]**
- **February to September:** several Android and broader GAA app collaborations
  were explored. Ryan supplied mock-ups, sample spreadsheets, provincial CSVs,
  and branding. Test builds existed, and the merits of bundled data versus a
  central database were discussed. None became a fully functional public app
  attributable to those collaborations. **[Owner archive]**

#### Date discrepancy

The restored v2.0 article is dated 28 January 2018 but says the social launch
was on "21 February". The SportsJOE publication and contemporary email place the
launch and interview on 21 January. Treat "February" as a likely typo unless an
original page capture establishes otherwise.

### 2019: Provincial files and selective sharing

- The working data included provincial CSVs for Leinster, Munster, Ulster, and
  Connacht plus a county-grounds file. Publishing and sharing still involved
  manual exports, attachments, and Google Drive access. **[Owner archive]**
- **May:** the provincial and county-ground data was supplied to Imagine for a
  broadband coverage exercise, with use limited to the agreed purpose.
  **[Owner archive]**
- Corrections continued, including Rathmolyon and Oughterard. **[Owner archive]**
- **3 December:** the Squarespace Business Plan began. **[Owner archive]**

### 2020: Institutional use and Tableau

- **April:** provincial files were supplied for COVID-related community
  outreach. The public v3.0 post later described the data as helping a
  government COVID response, but the department, final product, and operational
  use are not yet documented. **[Public, Owner archive, Open question]**
- **November:** a DCU MSc Data Analytics student received county-ground data for
  an assignment. **[Owner archive]**
- **28 December:** v3.0 moved the public map from Google Maps to Tableau Public
  and introduced club, pitch, and county filters. **[Public:
  [Pitch Finder 3.0](https://gaapitchfinder.com/blog/pitch-finder-30.html)]**
- **December onward:** a county-board verification campaign requested official
  club names, grounds, addresses, Eircodes, social accounts, and corrections.
  **[Owner archive]**

Ryan reports that the Tableau dashboard eventually reached approximately
150,000 views. This should remain an owner-supplied figure until a screenshot or
export from Tableau is preserved.

### 2021: International expansion

- **29 January:** v4.0 expanded coverage to Great Britain, continental Europe,
  Asia, Australasia, North America, and South America. **[Public:
  [Pitch Finder 4.0](https://gaapitchfinder.com/blog/pitch-finder-40.html)]**
- Correspondence with international clubs and organisations exposed modelling
  questions that remain relevant: shared grounds, temporary facilities,
  seasonal locations, and merged, inactive, or defunct clubs. **[Owner archive]**
- A second Reddit verification round produced missing grounds, incorrect pins,
  and examples where a pitch-centre coordinate sent drivers to the wrong side
  of a railway or away from the usable entrance. **[Public, Owner archive]**
- A EUR 10 donation was recorded toward the nonprofit project's hosting and
  maintenance costs. **[Owner archive]**
- Data and map imagery were discussed for GIS and publication work, including
  correspondence connected with the *Atlas of the History of Irish Sport*. The
  exact final publication using the imagery remains unconfirmed. **[Owner
  archive, Open question]**

### 2022: App exploration, research, and search demand

- Another iOS application collaboration considered a database/API backend,
  TestFlight, and app-store distribution. It did not produce a confirmed public
  release. **[Owner archive]**
- A Trinity researcher requested the dataset for PhD-related analysis.
  **[Owner archive]**
- Search Console recorded 1,730 clicks and 57,900 impressions in June. These
  are period metrics, not lifetime unique visitors. **[Owner archive]**

### 2023: Research and public-interest reuse

- **January:** ESB requested the Irish dataset for internal GIS mapping.
  **[Owner archive]**
- Tufts University researchers requested the all-island dataset and later
  enriched it with historical club attributes. The final publication status is
  not confirmed. **[Owner archive, Open question]**
- An Taisce's Safe Routes to School programme requested club-location data for
  national analysis and agreed to provide credit. **[Owner archive]**
- **13 August:** v5.0 publicly recorded reuse by Safe Routes to School, Tufts,
  Trinity, and ESB. **[Public:
  [Pitch Finder 5.0](https://gaapitchfinder.com/blog/pitch-finder-50.html)]**
- **13 August:** the project published an analysis of the most isolated pitch in
  each of Ireland's 32 counties. **[Public:
  [Most Remote GAA Pitches in Ireland](https://gaapitchfinder.com/blog/most-remote-pitches.html)]**

### 2024: Open data

- **5 February:** the GitHub repository and its first dataset commit were
  created. **[Repository]**
- **25 February:** v6.0 announced that the underlying dataset was openly
  available on GitHub and noted a presentation at the Q1 Dublin Data Meetup.
  **[Public: [Pitch Finder 6.0](https://gaapitchfinder.com/blog/pitch-finder-60.html)]**
- Git made changes reviewable and gave researchers and developers direct access
  instead of requiring case-by-case attachments. **[Repository]**
- **July:** Dr Gerard McCarthy and students at Maynooth University discussed
  their use of the dataset and raised classification questions around playing
  codes, name changes, mergers, and defunct clubs. **[Owner archive]**

### 2025: Data stories and a public research outcome

- **9 March:** the elevation analysis reported pitches from 3 metres below sea
  level in Amsterdam to 1,741 metres above sea level in Butte, Montana.
  **[Public:
  [The Heights of Gaelic Games](https://gaapitchfinder.com/blog/elevation-analysis.html)]**
- Search Console recorded 3,460 clicks and 80,200 impressions in March.
  **[Owner archive]**
- **17 July:** RTÉ Brainstorm published Maynooth research that explicitly
  credited GAA Pitch Finder club locations:
  ["Where are the hurling and football strongholds in Ireland?"](https://www.rte.ie/brainstorm/2025/0717/1460508-gaa-geography-hurling-football-strongholds-clubs-county-titles/).
  **[Public]**
- Community donations and corrections continued. At least two donations and a
  EUR 24.11 Stripe payout are recorded in the owner archive. **[Owner archive]**

### 2026: Reproducible open-source publishing

- **21 June:** pull request
  [#60](https://github.com/ryanmcg2203/gaapitchfinder/pull/60) merged the Leaflet
  map and GitHub Pages deployment pipeline. **[Repository]**
- **22 June:** pull request
  [#61](https://github.com/ryanmcg2203/gaapitchfinder/pull/61) merged the
  replacement website. The exact moment the live domain switched from the old
  site is not yet independently archived. **[Repository, Open question]**
- **23-30 June:** Cloudflare account records show the domain becoming active on
  the Free plan, followed by registrar transfer initiation and completion. The
  transfer invoice was approximately USD 10.46. **[Owner archive]**
- During July and August, the repository gained generated club and county pages,
  an improved mobile map, search and discovery tools, dataset validation,
  browser and accessibility tests, stable CSV and GeoJSON downloads, opt-in
  analytics consent, a public data-quality report, and consolidated site
  generation. **[Repository]**
- Work with OpenStreetMap began producing coverage and geometry-enrichment
  tooling. Another developer's reuse of the open dataset led to a corrected
  attribution. **[Repository, Owner archive]**
- **6 August:** the canonical dataset contained 1,989 records. **[Repository]**
- **17 August:** the EUR 204 annual Squarespace Business Plan was scheduled for
  cancellation at the end of its term on 3 December 2026. GitHub Pages removed
  that future website hosting cost; domain registration remains separate.
  **[Owner archive]**

Search Console snapshots for May, June, and early August show ongoing demand,
but their date windows overlap and must not be added together:

| Measurement window | Clicks | Impressions | Evidence |
| --- | ---: | ---: | --- |
| May 2026 | 2,110 | 91,500 | Owner archive |
| June 2026 | 1,930 | 85,000 | Owner archive |
| 28 days ending 7 August 2026 | 2,500 | Not recorded here | Owner archive |

## Technical evolution

| Period | Canonical data | Public interface | Publishing model |
| --- | --- | --- | --- |
| 2017-2018 | Google Drive master spreadsheet | Google Maps/My Maps | Manual spreadsheet imports |
| 2018-2020 | Master workbook plus provincial and county CSVs | Google map and app prototypes | Drive shares and email attachments |
| 2020-2024 | Privately managed source files | Squarespace with Tableau Public | Manual data and dashboard updates |
| 2024-2026 | Public CSV in GitHub | Tableau/Squarespace plus open-data tooling | Git-based dataset maintenance |
| 2026-present | Canonical CSV plus derived datasets | Leaflet on GitHub Pages | Generated and tested with GitHub Actions |

## What maintenance has taught us

GAA geography is not a static lookup table. The recurring reports are useful
product and data-model evidence:

- clubs and second grounds are missing;
- facilities move, close, merge, or are renamed;
- a pitch-centre point may be poor driving guidance;
- directions can lead to dead ends or inaccessible entrances;
- overseas clubs may share, rent, or seasonally change grounds;
- county, province, division, and playing-code labels can be disputed;
- Irish, English, abbreviated, and historical names complicate search.

Recurring product requests have included mobile search, native apps, an API,
direct GIS downloads, contact lists, historical status, code classification,
entrance coordinates, pitch dimensions, and practical facility details.

## Evidence of impact

The most defensible public indicators are:

- SportsJOE coverage in January 2018;
- the contemporary v2.0 traffic and social figures;
- continuous public corrections since 2018;
- international expansion documented in 2021;
- open publication of the dataset in 2024;
- Maynooth research published by RTÉ in 2025;
- GitHub history showing sustained dataset and product maintenance;
- thousands of monthly search clicks in owner-account snapshots.

Other institutional use is supported by the owner archive and selected public
blog posts. A request for data is evidence of interest or supplied access, but
should not be described as a completed publication or operational deployment
unless the resulting work can be identified.

## Archive inventory

Public material worth preserving:

- [GAA Pitch Finder blog](https://gaapitchfinder.com/blog/)
- the original Reddit thread and the 2020 verification thread, if stable URLs or
  captures can be recovered;
- the [SportsJOE feature](https://www.sportsjoe.ie/sport/gaa/monaghan-man-spent-months-developing-map-every-gaa-ground-ireland-love-148052);
- the Tableau Public dashboard and a capture of its view counter;
- the [RTÉ/Maynooth article](https://www.rte.ie/brainstorm/2025/0717/1460508-gaa-geography-hurling-football-strongholds-clubs-county-titles/);
- the [GitHub repository](https://github.com/ryanmcg2203/gaapitchfinder);
- snapshots of major versions of the live site.

Important owner-archive threads include:

- `Pitch Finder piece for SportsJOE` - 21 January 2018;
- `Pitch Finder` - Trinity Android collaboration, February-July 2018;
- `Android Application Integration` - February 2018;
- `PitchFinder - Invitation to collaborate` - September 2018;
- `Inquiry` - CSV sharing, May 2019;
- `Dataset - GAA Pitches County Grounds` - November 2020;
- county-board `Request for Help` threads - December 2020-January 2021;
- international expansion correspondence - January 2021;
- `Shapefile` - February 2021;
- `Map` and `Atlas of the History of Irish Sport` - 2021;
- `GAA Pitch data` - Trinity research, 2022 onward;
- `GAA Pitchfinder Data (Ireland)` - ESB, January 2023;
- `Request for GAA data` - Tufts, January 2023 onward;
- `Location Data for GAA Clubs` - An Taisce, July 2023;
- `GAA pitch data` - Maynooth, July 2024 onward;
- `GAA Pitch Finder dataset - potentially useful for Atlas of the GAA?` - June
  2026;
- `Quick question about GAA Club Finder data` - July 2026;
- Cloudflare transfer records - June 2026;
- Squarespace cancellation record - 17 August 2026.

Private messages should be archived with personal addresses and unrelated
content redacted before any excerpt is published.

## Open historical questions

- What hosted the first website before Squarespace?
- When was `gaapitchfinder.com` first registered?
- Can the original master spreadsheet and My Map be preserved read-only?
- How many records existed at launch, at the Tableau migration, and at the
  international launch?
- Can stable captures of both Reddit threads be recovered?
- Can the original Instagram post and engagement figure be captured?
- What final output used the data supplied for COVID community outreach?
- Which publication, if any, used the 2021 map artwork?
- Are the Q1 Dublin Data Meetup slides or photographs preserved?
- Did the Tufts or Trinity projects produce a paper, thesis, or public dataset?
- Can the Tableau view counter be exported or captured?
- What deployment or DNS record establishes when the Leaflet site first served
  on the live domain?

Resolve questions here only when the supporting record is linked or described
in the same change.
