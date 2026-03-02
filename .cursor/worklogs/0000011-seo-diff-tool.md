# Worklog: SEO Diff Tool

## Summary

Built `5-seo-diff.py` - a terminal-based tool that compares two SEO report JSON files and displays only the differences.

## Changes Made

1. Created `5-seo-diff.py` with:
   - JSON report loading
   - Comparison type detection (temporal vs competitor based on canonical URL)
   - Summary statistics table with adaptive column headers
   - Detailed diff sections for: title, meta, H1, canonical, headings, links, keywords, schemas, issues

## Features

- Adaptive labeling: [OLD]/[NEW] for temporal (same site over time), [A]/[B] for competitor (different sites)
- Color-coded output: green=additions, red=removals, yellow=changes
- Summary table shows quick overview of all categories with delta indicators
- Detailed sections only show categories with actual differences
- Handles large link/heading lists with truncation (max 10 shown)
- Keyword ranking changes with percentage deltas and trend icons
- Issue diff shows new, resolved, and persisting issues

## Usage

Configure paths at top of script:
```python
REPORT_A_PATH = "path/to/first_seo_report.json"
REPORT_B_PATH = "path/to/second_seo_report.json"
```

Run: `python 5-seo-diff.py`

## Output Example

```
═══════════════════════════════════════════════════════════════════════════════
 SEO DIFF: snaptik.app (over time)
═══════════════════════════════════════════════════════════════════════════════
  [OLD] scraped/snaptik_app_archive/20230220-192556.html
  [NEW] scraped/snaptik_app_archive/20240609-175516.html
═══════════════════════════════════════════════════════════════════════════════

┌─────────────────────┬──────────────┬──────────────┬──────────────┐
│ Category            │ OLD          │ NEW          │ Change       │
├─────────────────────┼──────────────┼──────────────┼──────────────┤
│ Title               │ 69 chars     │ 69 chars     │ ═ same       │
│ Headings            │ 17           │ 21           │ △ +4         │
│ ...                 │              │              │              │
└─────────────────────┴──────────────┴──────────────┴──────────────┘

5 difference(s) found

── HEADINGS ───────────────────────────────────────────────────────────────────
  + h3: "Download SnapTik App"  ← ADDED
  ~ h3: "Key features:" (was h4)  ← TAG CHANGED
```
