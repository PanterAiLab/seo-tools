# 0000004 - Implement Sitemap Checker

**Date:** 2026-02-16

## Summary

Implemented the sitemap checker script (`2-sitemap.py`) that cross-references the sitemap.xml against pages downloaded by the scraper, checks image URLs, and produces a detailed report.

## Changes Made

### Enhanced: `utils_html.py`
- Added `SitemapEntry` dataclass with fields: `loc`, `lastmod`, `changefreq`, `priority`, `images`.
- Added `parse_sitemap_detailed()` function that parses sitemap XML returning full `SitemapEntry` objects with image URLs and metadata. Existing `parse_sitemap()` left untouched.

### Enhanced: `utils_requests.py`
- Added `fetch_head()` function for lightweight HEAD requests (no body download). Used by the sitemap checker to verify image URLs without transferring image data.

### Enhanced: `utils_files.py`
- Added `find_page_file()` function that locates a downloaded HTML file for a given URL regardless of HTTP status code prefix. Globs for `*-<slug>.html` pattern and extracts the status from the filename.

### New: `2-sitemap.py`
- Config block with `WEBSITE_URL`, `HTTP_AUTH_USERNAME`, `HTTP_AUTH_PASSWORD`, `PARALLELISM`.
- Step 1: Loads sitemap.xml from disk and parses with `parse_sitemap_detailed()`.
- Step 2: Checks page completeness -- matches every sitemap URL to its downloaded file. Exits immediately with error listing if any pages are missing.
- Step 3: Checks all sitemap `<image:image>` URLs via parallel HEAD requests using asyncio semaphore.
- Step 4: Prints full colorized report with per-URL status, image results, error/redirect highlights, and summary statistics.
- Tested successfully: 49/49 pages found, 29/29 images OK.
