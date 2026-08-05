# Changelog

All notable changes to MUF Muncher are documented here.

## [1.4.2] - 2026-08-05
### Fixed
- Ionosonde detail charts' x-axis ticks could show a misleading hour, reported live by Andreas, DN9GU. The old code placed 7 ticks at fixed fractions (0, 4, 8, ... 24 "hours") of the *actual* data span and just truncated each interpolated timestamp to its hour - correct-looking only when that span happened to land close to exactly 24h. A shorter/longer real span (a data gap, a freshly-seeded store, stations with unevenly-pruned history) drifted the labels away from real clock time, most visibly at the right edge. Replaced with genuine calendar-aligned UTC ticks every 4h (00:00/04:00/08:00/.../20:00), positioned via the existing time-to-pixel scale rather than assumed fractions - falls back to labeling the two raw endpoints if the span is too short to contain a real 4h boundary.

## [1.4.1] - 2026-08-02
### Fixed
- `muf.css`, `mufmuncher-icon.png`, `mufmuncher-llama.png` and `mufmuncher-wave.png` are served with a 4h `Cache-Control` on Cloudflare Pages (they're normally static across runs) but were referenced by plain filename, with nothing to bust that cache on the rare run where one of them *does* change — discovered live on muf.sammet.me right after v1.4.0 shipped: the new `.hero-distance`/`.hdr-locator` CSS rules hadn't reached an already-visited browser, which rendered those elements unstyled (oversized default browser font) while the fresh HTML/payload underneath looked completely normal, since those aren't cached the same way. `render_html()` now appends `?v=<VERSION>` to all four references, so a version bump forces a fresh fetch instead of waiting out the cache window.

## [1.4.0] - 2026-08-02
### Added
- `MUF_HOME_LOCATOR` (Maidenhead grid square, 4 or 6 characters): hero stations are now the two nearest of ten curated European GIRO stations to this locator, by great-circle distance, instead of hardcoded Dourbes + Juliusruh. Defaults to Frankfurt am Main if unset, which resolves to Dourbes + Pruhonice — a real behavior change from the previous fixed default, since Pruhonice is genuinely the closer of the two. The other eight stations fall back to the ticker automatically. Falls back to the Frankfurt default (with a warning) on an unparseable locator instead of crashing. Docker: set via `docker-compose.yml`'s `environment:` — `entrypoint.sh` now regenerates `/etc/cron.d/muf-cron` with the runtime value baked in at container start, since cron doesn't inherit the container's environment and would otherwise only see it on the initial fetch.
- Concept validated first with live PSKReporter data before building: real reception-report activity for a mid-Germany locator showed substantial activity on bands the MUF(D) heuristic calls "marginal"/"closed" (15m had more real reports than the "open" bands combined) — logged in `muf-muncher-notes/ROADMAP.md` as the next candidate feature, not built yet.
- `MUF_HOME_LOCATOR` now warns instead of silently picking irrelevant hero stations when the configured locator is far outside the ten curated stations' European coverage (>1500km from the nearest one): logged to the console during the fetch/render cycle, and surfaced as a note in the dashboard's footer (`configured location is ~Xkm from the nearest covered station...`) so a self-hoster outside Europe sees it too, not just whoever reads the cron log.
- `.github/workflows/deploy.yml` now sets `MUF_HOME_LOCATOR` explicitly (Max's own grid square) so muf.sammet.me's hero stations are determined by an intentional value instead of coincidentally matching the Frankfurt default.
- The active locator is now visible in the dashboard header itself ("Your locator: ...", between the clock and the version line), not just in the footer note: shows the configured grid square, or "Frankfurt am Main (JO40ic) · default" when unset — Frankfurt's own grid square is hardcoded for display so the default reads consistently with a custom one — or a highlighted "⚠ Xkm from coverage" when it's outside the far-from-coverage threshold. Each hero tile's name now also shows its distance from that locator ("Dourbes 299km from you") instead of appending it to the "3000km" MUF(D) subtitle, which read as if both numbers were the same kind of distance. Ticker stations get the same distance as a hover tooltip rather than visible text, to keep those chips compact.

## [1.3.1] - 2026-07-30
### Fixed
- Header clock/version block could stay left-aligned instead of right-aligned on narrow screens, reported specifically on iOS when the dashboard is added to the home screen as a standalone web app - the previous fix relied on `.hdr`'s `flex-wrap` organically breaking `.hdr-right` onto its own line before `margin-left:auto` could right-align it, which depends on exact available width and can apparently compute a few px differently in standalone mode than regular Safari. Replaced with an explicit `flex-direction: column` + `align-self: flex-end` at the existing sub-480px breakpoint (every real phone falls under it) instead of relying on the wrap timing at all.

## [1.3.0] - 2026-07-30
### Added
- "Update available" indicator: `muf.py` checks GitHub's latest release tag during the cron fetch/render cycle and bakes a `latestVersion` field into `summary.json` and the HTML payload (falls back to the last known value in the store if the GitHub check fails, same pattern as the other external fetches). The dashboard header shows a small badge next to the current version number when `latestVersion` is newer — a plain client-side string compare, no runtime network call to GitHub.
- Dark mode toggle in the header: an explicit light/dark choice, persisted in `localStorage` and applied via `data-theme` (set as early as possible in `<head>`, before the stylesheet paints, so a returning visitor's choice never flashes back to the system default first). Until the user picks one, `prefers-color-scheme` keeps deciding, same as before.
- Mode filter (SSB/CW/Digimode) in Activator Activity, same filter-chip pattern as the existing network/band/entity filters. POTA/SOTA's free-text mode field is bucketed client-side (FT8/FT4/RTTY/etc. all fall into Digimode); FM/AM and blank modes match none of the three buckets, so they only disappear once a mode filter is actually active, same as any other unmatched value.

## [1.2.1] - 2026-07-29
### Fixed
- `muf.py` crashed immediately on Windows: `time.tzset()` (used to force UTC so plotext's terminal chart date axis lines up with the UTC timestamps fed into it) doesn't exist there — it's Unix-only. Guarded the call so it's a no-op on Windows instead of an `AttributeError`; the terminal chart's date labels can be off by the local UTC offset there as a result, everything else (JSON/HTML/summary output) is unaffected.
- The K-index, SFI, X-ray and solar wind NOAA fetches only caught `URLError`/`HTTPError`, not `json.JSONDecodeError` — a malformed/duplicated JSON response from NOAA (observed in practice, transient) crashed the whole run instead of just skipping that one metric for this cycle, same class of bug v1.1.1 already fixed for the GIRO station fetches.

## [1.2.0] - 2026-07-29
### Added
- An explanation (hover tooltip on the gray chip, plus a note in the README) for why only 20-10m get an open/marginal/closed color in Activator Activity — MUF(D) is an upper bound, so applying the same logic to 40m/80m would read "open" almost permanently regardless of real conditions.

### Changed
- New header identity: the flat banner image is replaced by a line-art llama + waveform logo (transparent, CSS-inverted for dark mode instead of a second asset) next to a thin, wide-tracked wordmark in a warm accent color, with a soft radial glow behind it.
- The header clock is smaller and lighter than before, so the logo reads as the primary visual anchor instead of competing with it.
- GIRO/lgdc.uml.edu requests are now spaced out (~750ms apart) instead of firing back-to-back, to make the `HTTP 429`s below less likely in the first place.

### Fixed
- GitHub Actions runs now persist the last known station history across runs (`actions/cache`) — previously, every run started from a clean checkout with no local store, so a single rate-limited fetch on CI wiped that station's entire chart instead of just skipping new points.
- The header's waveform divider was invisible in production: its width was measured while the page was still in its initial `display:none` loading state, which always computes to 0. Moved the measurement to after the page is actually revealed.
- A badly-cropped, asymmetric header screenshot in the README.
- Screenshot links in the README 404'd when viewed on Forgejo: a raw HTML `<a href="relative.png">` isn't rewritten to a working path by its markdown renderer (unlike `<img src>`, which is) — switched to standard Markdown `[![]()]()` link syntax, which resolves correctly on both GitHub and Forgejo.

## [1.1.1] - 2026-07-29
### Fixed
- Gracefully handle malformed or error responses from ionosonde station APIs (e.g. rate-limiting or maintenance blackouts) instead of crashing the entire fetch/deploy run. A single failed station now logs a warning and is skipped; the run continues normally with the remaining stations.
