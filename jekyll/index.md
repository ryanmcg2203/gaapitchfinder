---
layout: default
title: Blog – GAA Pitch Finder
description: Updates, data analysis and stories from GAA Pitch Finder.
permalink: /index.html
---

<div class="page-content">
  <h1>Blog</h1>
  <ul class="post-list">
    {% for post in site.posts %}
    <li>
      <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
      <div class="post-meta">{{ post.date | date: "%e %B %Y" }} &middot; {{ post.read_time | default: "3 min read" }}</div>
      <p class="post-excerpt">{{ post.description }}</p>
    </li>
    {% endfor %}
    <li>
      <a href="elevation-analysis.html">The Heights of Gaelic Games: Analysing Elevation Data of GAA Pitches Worldwide</a>
      <div class="post-meta">9 March 2025 &middot; 2 min read</div>
      <p class="post-excerpt">GAA pitches range from 3 metres below sea level in Amsterdam to 1,741 metres in Montana. An elevation analysis of nearly 2,000 pitches worldwide.</p>
    </li>
    <li>
      <a href="pitch-finder-60.html">Pitch Finder 6.0</a>
      <div class="post-meta">25 February 2024 &middot; 1 min read</div>
      <p class="post-excerpt">The underlying dataset is now published openly on GitHub. Also presented at the Q1 Dublin Data Meetup.</p>
    </li>
    <li>
      <a href="most-remote-pitches.html">Most Remote GAA Pitches in Ireland</a>
      <div class="post-meta">13 August 2023 &middot; 3 min read</div>
      <p class="post-excerpt">Which GAA pitch is the most isolated in each county? From Donegal's Pettigo at 18 km to Wexford's St. Mogue's, the most remote pitches across all 32 counties.</p>
    </li>
    <li>
      <a href="pitch-finder-50.html">Pitch Finder 5.0</a>
      <div class="post-meta">13 August 2023 &middot; 1 min read</div>
      <p class="post-excerpt">Data used by Safe Routes to School, Tufts University, Trinity College Dublin, and the ESB for GIS mapping.</p>
    </li>
    <li>
      <a href="pitch-finder-40.html">Pitch Finder 4.0</a>
      <div class="post-meta">29 January 2021 &middot; 1 min read</div>
      <p class="post-excerpt">Pitch Finder goes global — now covering pitches in Europe, Great Britain, Asia, Australasia, and South America.</p>
    </li>
    <li>
      <a href="pitch-finder-30.html">Pitch Finder 3.0</a>
      <div class="post-meta">28 December 2020 &middot; 1 min read</div>
      <p class="post-excerpt">Map migrated to Tableau Public with new filtering for clubs, pitches, and counties. Data also used to aid the Government COVID response.</p>
    </li>
    <li>
      <a href="pitch-finder-20.html">Pitch Finder 2.0</a>
      <div class="post-meta">28 January 2018 &middot; 1 min read</div>
      <p class="post-excerpt">The site went viral — 21,000 map views, a Sportsjoe.ie article, 550 Reddit upvotes, and thousands of Instagram likes.</p>
    </li>
    <li>
      <a href="pitch-finder-v11.html">Pitch Finder v1.1</a>
      <div class="post-meta">4 November 2017 &middot; 1 min read</div>
      <p class="post-excerpt">Added county grounds across Ireland and Google Maps directions to every location.</p>
    </li>
    <li>
      <a href="pitch-finder-v10.html">Pitch Finder v1.0</a>
      <div class="post-meta">27 October 2017 &middot; 1 min read</div>
      <p class="post-excerpt">First release of GAA Pitch Finder — all four provinces, club pitches across Ireland, and the site logo.</p>
    </li>
  </ul>
</div>
