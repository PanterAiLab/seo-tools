# 0000001 - Implement SEO Scraper

**Date:** 2026-02-16

## Summary

Implemented the full SEO scraper script (`1-scraper.py`) and all supporting utility modules from scratch, based on the plan in `IDEA.md`.

## Changes Made

### New file: `requirements.txt`
- Added project dependencies: `httpx`, `beautifulsoup4`, `lxml`.

### Implemented: `utils_files.py`
- `get_website_id(url)` - Converts URL to filesystem-safe ID (e.g. `example_com`).
- `get_page_path(base_dir, url, status_code)` - Computes on-disk path using Page ID convention (`<status>-<slug>.html`).
- `save_page(base_dir, url, status_code, content)` - Saves HTML to disk.
- `save_raw_file(base_dir, filename, content)` - Saves raw files like robots.txt/sitemap.xml.
- `load_existing_pages(base_dir)` - Scans folder for previously downloaded pages (resumability).
- `url_to_path_key(url)` - Converts URL to path key for deduplication matching.

### Implemented: `utils_requests.py`
- `get_session(username, password)` - Creates async httpx client with browser-like headers and optional HTTP Basic Auth.
- `fetch_page(client, url)` - Fetches a URL, returns `(status_code, final_url, body)`. Handles timeouts and errors gracefully.

### Implemented: `utils_html.py`
- `extract_internal_links(html, base_url)` - Extracts and normalizes same-domain links from HTML.
- `parse_sitemap(xml_content)` - Parses sitemap XML, handles both `<urlset>` and `<sitemapindex>`.

### Implemented: `1-scraper.py`
- Config block with `WEBSITE_URL`, `MAX_PAGES`, `PARALLELISM`, HTTP auth fields.
- Full async flow: robots.txt fetch, sitemap parsing (recursive for sitemap indexes), parallel page downloads, internal link discovery loop, session stats.
- Batch-based concurrency with `asyncio.Semaphore` to avoid race conditions.
- Resumability via `load_existing_pages()` on re-run.
