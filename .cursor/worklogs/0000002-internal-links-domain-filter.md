# 0000002 - Internal Links Domain Filter

**Date:** 2026-02-16

## Summary

Updated `extract_internal_links` to compare link domains against the root `WEBSITE_URL` instead of the current page URL, ensuring only true internal links are followed during crawling.

## Changes Made

### `utils_html.py`
- Added `site_url` parameter to `extract_internal_links(html, base_url, site_url)`.
- Domain filtering now uses `site_url` hostname (the root website) instead of `base_url` (the page URL). This prevents leaking external links if a redirect lands on a different subdomain.
- `base_url` is still used for resolving relative links.

### `1-scraper.py`
- Updated the `extract_internal_links` call in the link discovery loop to pass `WEBSITE_URL` as `site_url`.
- Added clarifying comment that robots.txt is saved for reference only and its rules are intentionally ignored (from previous session).
