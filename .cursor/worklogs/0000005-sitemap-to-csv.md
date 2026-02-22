# 0000005 - Sitemap to CSV Script

## Summary

Created `3-sitemap-to-csv.py` -- a script that reads a sitemap.xml (from URL or local file) and outputs a plain CSV file containing all page URLs, one per row, no headers.

## Changes

- **New file: `3-sitemap-to-csv.py`**
  - Configuration block at top: `SITEMAP_SOURCE` (URL or file path), `OUTPUT_FILE` (defaults to `sitemap-urls.csv`), optional HTTP auth, parallelism setting.
  - Reuses `utils_html.parse_sitemap()` for XML parsing and `utils_requests` for fetching remote sitemaps.
  - Supports sitemap index files: detects sub-sitemaps and fetches them in parallel.
  - Writes output via `csv.writer` -- one URL per row, single column, no header/footer.
  - Prints summary to stdout with total URL count and output file path.
