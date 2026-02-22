# Wayback Machine Scraper Implementation

**Date:** 2026-02-22

## Summary

Implemented the Wayback Machine Scraper (step 4 from IDEA.md) that downloads historical snapshots of a website's homepage from web.archive.org.

## Changes Made

### New Files

- **`utils_wayback.py`** - Reusable utilities for Wayback Machine interactions:
  - `WaybackSnapshot` dataclass for snapshot metadata
  - `fetch_cdx_snapshots()` - Query CDX API for all available snapshots
  - `filter_snapshots_by_frequency()` - Select one snapshot per period (daily/weekly/monthly)
  - `fetch_snapshot_html()` - Download HTML for a snapshot
  - `parse_wayback_timestamp()` - Parse timestamp format
  - `format_snapshot_filename()` - Convert timestamp to filename

### Modified Files

- **`utils_files.py`** - Added archive-specific helpers:
  - `get_archive_folder_id()` - Returns `{website_id}_archive` folder name
  - `get_snapshot_path()` - Compute path for snapshot HTML file
  - `load_existing_snapshots()` - Scan for already-downloaded snapshots (resumability)

- **`4-webarchieve.py`** - Complete rewrite as async script:
  - Configuration section (WEBSITE_URL, FREQUENCY, PARALLELISM)
  - Fetches CDX index and saves as JSON
  - Filters snapshots by configurable frequency
  - Downloads HTMLs in parallel with semaphore
  - Supports resumability (skips existing snapshots)
  - Prints detailed statistics

## Features

- **Frequency filtering**: Daily, weekly, or monthly (default: monthly)
- **Middle-point selection**: Picks snapshot closest to middle of each period
- **Resumability**: Detects previously downloaded snapshots and skips them
- **CDX index saved**: Raw index saved as `cdx_index.json` for reference
- **Parallel downloads**: Uses asyncio semaphore (default 5 concurrent)
- **Clean error handling**: Reports errors per snapshot, continues downloading

## Output Structure

```
scraped/{website_id}_archive/
  cdx_index.json       # Full CDX response
  20230115-120000.html # Snapshot files
  20230215-143022.html
  ...
```

---

## Update: HTML Prettification

**Date:** 2026-02-22

Added HTML prettification step when saving snapshots.

### Changes

- **`utils_html.py`** - Added `prettify_html()` function:
  - Uses BeautifulSoup with `HTMLFormatter(indent=2)`
  - Properly formats HTML with newlines and indentation
  - Preserves original structure and content

- **`4-webarchieve.py`** - Updated to prettify HTML before saving:
  - Imports `prettify_html` from `utils_html`
  - Applies prettification to downloaded HTML before writing to disk
