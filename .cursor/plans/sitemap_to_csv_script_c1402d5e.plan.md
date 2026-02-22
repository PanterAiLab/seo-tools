---
name: Sitemap to CSV Script
overview: Create a simple script `3-sitemap-to-csv.py` that reads a sitemap.xml file (from a URL or local path), extracts all `<loc>` URLs using the existing `parse_sitemap` utility, and writes them to a CSV file with one URL per row -- no headers, no footers, single column.
todos:
  - id: create-script
    content: Create `3-sitemap-to-csv.py` with sitemap parsing and CSV output logic
    status: completed
  - id: worklog
    content: Add worklog entry `0000005-sitemap-to-csv.md`
    status: completed
isProject: false
---

# Sitemap to CSV Conversion Script

## Approach

Create `3-sitemap-to-csv.py` -- a simple script that:

1. Accepts a sitemap.xml source (URL or local file path) as input
2. Parses the XML using the existing `[parse_sitemap](utils_html.py)` function from `utils_html.py`
3. If the sitemap is a sitemap index (contains sub-sitemaps), fetches and parses those too
4. Writes all extracted `<loc>` URLs to a `.csv` file, one URL per line, no header row

## Key Reuse

- `**utils_html.parse_sitemap(xml_content)**` -- already parses sitemap XML and returns `(page_urls, sub_sitemap_urls)`. This handles both `<urlset>` and `<sitemapindex>` formats.
- `**utils_requests.get_session()**` / `**utils_requests.fetch_page()**` -- for fetching remote sitemaps by URL.

## Script Design

- **Configuration block** at the top (matching existing convention): `SITEMAP_SOURCE` (URL or file path) and `OUTPUT_FILE` (CSV path, defaults to `sitemap-urls.csv`).
- Uses `csv.writer` to write one URL per row (single column, no header).
- If the source is a URL (starts with `http`), fetch it with httpx. If it's a local path, read from disk.
- If the sitemap is a sitemap index, recursively fetch and parse all sub-sitemaps.
- Print a summary to stdout: total URLs found and output file path.

## Output Format

```
https://example.com/
https://example.com/about
https://example.com/blog/post-1
```

One URL per line in the CSV. No headers, no footers, single column only.