---
name: Detect external redirects
overview: Stop following redirects automatically. Save pages with their true HTTP status codes (301, 302, etc.). For internal redirects, follow manually and save the target too. For external redirects, save the redirect but skip the target. Add canonical URL checking as a secondary signal.
todos:
  - id: fetch-page
    content: "Update fetch_page in utils_requests.py: disable follow_redirects, return (status, location_header, body) for 3xx responses"
    status: completed
  - id: detect-helper
    content: Add detect_external_page(body, final_url, site_url) to utils_html.py for canonical URL checking
    status: completed
  - id: download-batch
    content: "Rewrite download_batch in 1-scraper.py to handle redirects: save with true status code, follow internal redirects, skip external ones, check canonical"
    status: completed
  - id: stats
    content: Update session stats to show internal redirects, external redirects, and canonical mismatches
    status: completed
  - id: worklog
    content: Create worklog entry for this change
    status: completed
isProject: false
---

# Detect External Redirects and Preserve True HTTP Codes

## Problem

`httpx` is configured with `follow_redirects=True`, which silently follows 301/302/etc. We lose the original redirect status code (everything looks like 200) and pages that redirect to external domains get saved as normal internal pages.

## Solution

### 1. Update `fetch_page` in [utils_requests.py](utils_requests.py)

- Change the httpx client to `follow_redirects=False` in `get_session`.
- Update `fetch_page` to return the raw response as-is (the true 301/302/etc status code, the `Location` header as `redirect_url`, and the response body).
- Change return type to `tuple[int, str, str, str]`: `(status_code, final_url, redirect_url, body)`.
  - For non-redirect responses: `redirect_url` is empty string.
  - For 3xx responses: `redirect_url` is the value of the `Location` header (resolved to absolute).

### 2. Add `detect_external_page` to [utils_html.py](utils_html.py)

Check the HTML `<link rel="canonical">` tag. If the canonical URL points to a different domain than `site_url`, return `(True, "canonical: https://other.com/...")`. This catches pages that respond 200 but actually belong to another site.

### 3. Rewrite `download_batch` in [1-scraper.py](1-scraper.py)

New logic for each fetched page:

- **Status 200-299**: Save with true status code. Check canonical URL via `detect_external_page`. If canonical is external, print `[EXTERNAL CANONICAL]` warning, still save the page but exclude from link extraction.
- **Status 301/302/3xx**: Save the redirect page with its true status code (e.g. `301-slug.html`). Then check the `Location` target:
  - If target is **same domain**: add it to the queue of URLs to fetch (it will be downloaded in the next batch or current batch).
  - If target is **external domain**: print `[EXTERNAL REDIRECT]` with target URL, increment `stats["external_redirects"]`, do not follow.
- **Status 4xx/5xx**: Save with true status code as before.

The `download_batch` function gains a `site_url` parameter and returns redirect targets that need following.

### 4. Update stats in [1-scraper.py](1-scraper.py)

Add to the session summary:

- `Internal redirects: N`
- `External redirects: N`
- `External canonicals: N`

### 5. Worklog entry

