# Changelog

All notable changes to MUF Muncher are documented here.

## [1.3.0] - 2026-07-30
### Added
- "Update available" indicator: `muf.py` checks GitHub's latest release tag during the cron fetch/render cycle and bakes a `latestVersion` field into `summary.json` and the HTML payload (falls back to the last known value in the store if the GitHub check fails, same pattern as the other external fetches). The dashboard header shows a small badge next to the current version number when `latestVersion` is newer — a plain client-side string compare, no runtime network call to GitHub.
- Dark mode toggle in the header: an explicit light/dark choice, persisted in `localStorage` and applied via `data-theme` (set as early as possible in `<head>`, before the stylesheet paints, so a returning visitor's choice never flashes back to the system default first). Until the user picks one, `prefers-color-scheme` keeps deciding, same as before.

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
