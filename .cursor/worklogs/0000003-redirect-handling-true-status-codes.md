# 0000003 - Redirect Handling & True HTTP Status Codes

**Date:** 2026-02-16

## Summary

Stopped following redirects automatically so pages are saved with their true HTTP status codes (301, 302, etc.). Added detection for external redirects and external canonical URLs.

## Changes Made

### `utils_requests.py`
- Changed `follow_redirects=False` in `get_session` so httpx no longer silently follows 3xx.
- Updated `fetch_page` return to `(status_code, redirect_url, body)`:
  - For 3xx: `redirect_url` is the resolved absolute URL from the `Location` header.
  - For non-3xx: `redirect_url` is empty string.

### `utils_html.py`
- Added `is_same_domain(url, site_url)` helper for domain comparison.
- Added `detect_external_page(body, site_url)` that checks `<link rel="canonical">` for external domain. Returns `(is_external, reason)`.

### `1-scraper.py`
- Rewrote `download_batch` with full redirect handling:
  - **3xx to same domain**: saved as `301-slug.html`, target URL queued for fetching.
  - **3xx to external domain**: saved as `301-slug.html`, logged as `[EXTERNAL REDIRECT]`, not followed.
  - **2xx with external canonical**: saved, logged as `[EXTERNAL CANONICAL]`, excluded from link extraction.
  - **2xx normal**: saved and used for link extraction as before.
  - **4xx/5xx**: saved with true status code.
- `download_batch` now returns `(downloaded, redirect_targets)` so callers can follow internal redirects.
- Added manual redirect following for robots.txt and sitemap fetches (up to 5 hops).
- Updated session stats to show: internal redirects, external redirects, external canonicals.
