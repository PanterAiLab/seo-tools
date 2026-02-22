---
name: Filter internal links only
overview: Update extract_internal_links to compare against the root WEBSITE_URL domain, not just the current page URL, to ensure only true internal links are followed.
todos:
  - id: extract-links
    content: Update extract_internal_links in utils_html.py to accept site_url param and use it for domain filtering
    status: in_progress
  - id: caller-update
    content: Update extract_internal_links calls in 1-scraper.py to pass WEBSITE_URL
    status: pending
  - id: worklog
    content: Append worklog entry for this change
    status: pending
isProject: false
---

# Filter Internal Links by Root Domain

The `extract_internal_links` function in [utils_html.py](utils_html.py) currently compares link domains against `base_url` (the page URL). If a redirect lands on a different subdomain, this could leak external links. Fix: add a `site_url` parameter for the root `WEBSITE_URL` and use it for domain comparison.

Sitemap URLs are trusted and do not need additional filtering per user decision.

## 1. Update `extract_internal_links` in [utils_html.py](utils_html.py)

Add a `site_url` parameter. Use its hostname for domain filtering instead of `base_url`. `base_url` is still used for resolving relative links.

## 2. Update callers in [1-scraper.py](1-scraper.py)

Pass `WEBSITE_URL` as `site_url` to `extract_internal_links` at line 205.

## 3. Append to worklog
