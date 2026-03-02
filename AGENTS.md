## Learned User Preferences

- Prefers structured JSON output for tools that enables cross-page comparison
- Prefers modular architecture: reusable functions in utils modules, dataclasses as separate models
- Output files should be co-located with source files (same directory)
- Use underscore separator in derived filenames (e.g., `_seo_report.json` not `.seo_report.json`)
- Prefers terminal output optimized for showing differences, not all data
- Top 10 is the preferred limit for keyword displays in diff/comparison output

## Learned Workspace Facts

- This is a Python 3.12 SEO tools project
- Project uses worklogs in `.cursor/worklogs/` to track changes
- Uses BeautifulSoup with lxml parser for HTML parsing
- Uses `dataclasses.asdict()` for JSON serialization
- Scripts follow numbered naming convention: `1-scraper.py`, `2-sitemap.py`, `3-page-checker.py`, `3-sitemap-to-csv.py`, `4-webarchieve.py`, `5-seo-diff.py`
- Utils modules: `utils_html.py`, `utils_files.py`, `utils_requests.py`, `utils_seo.py`, `utils_links.py`, `utils_wayback.py`
- Models in separate files: `models_seo.py`
- `5-seo-diff.py` supports temporal (same site over time) and competitor (different sites) comparison modes with adaptive labeling
