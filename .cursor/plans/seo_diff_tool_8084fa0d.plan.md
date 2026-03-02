---
name: SEO Diff Tool
overview: Build a terminal-based SEO diff tool (5-seo-diff.py) that compares two SEO report JSON files and displays only the differences, with adaptive labeling for temporal (same site over time) and competitor (different sites) comparisons.
todos:
  - id: task1-skeleton
    content: Create script skeleton with JSON loading
    status: completed
  - id: task2-detection
    content: Add comparison type detection (temporal vs competitor)
    status: completed
  - id: task3-stats
    content: Add summary statistics calculation
    status: completed
  - id: task4-table
    content: Render summary table with adaptive labels
    status: completed
  - id: task5-text-diffs
    content: Add detailed diffs for title, meta, H1, canonical
    status: completed
  - id: task6-headings
    content: Add headings diff with added/removed/tag-changed
    status: completed
  - id: task7-links
    content: Add links diff with status changes
    status: completed
  - id: task8-keywords
    content: Add keywords ranking diff
    status: completed
  - id: task9-issues
    content: Add issues diff (new/resolved/persisting)
    status: completed
  - id: task10-assembly
    content: Final assembly and testing
    status: completed
  - id: task11-worklog
    content: Create worklog entry
    status: completed
isProject: false
---

# SEO Diff Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `5-seo-diff.py` that compares two SEO report JSON files and displays a colored terminal diff focusing only on changes.

**Architecture:** Load two JSON reports, detect comparison type (temporal vs competitor), compute diffs per category, render summary table then detailed change sections. All logic in single script following project conventions.

**Tech Stack:** Python 3.12, dataclasses, json, ANSI colors (no external deps)

---

## Task 1: Script Skeleton and JSON Loading

**Files:**

- Create: `5-seo-diff.py`

**Step 1: Create script with config and JSON loading**

```python
"""SEO Diff Tool: compares two SEO report JSON files and displays differences.

Supports temporal comparison (same site over time) and competitor comparison
(different sites). Omits identical data, focuses on changes.
"""

import json
import sys
from pathlib import Path

# Configuration
REPORT_A_PATH = "scraped/snaptik_app_archive/20230220-192556_seo_report.json"
REPORT_B_PATH = "scraped/snaptik_app_archive/20240609-175516_seo_report.json"

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def load_report(path: str) -> dict:
    """Load SEO report JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        print(f"{RED}ERROR: File not found: {path}{RESET}")
        sys.exit(1)
    return json.loads(file_path.read_text(encoding="utf-8"))


def main() -> None:
    """Main entry point."""
    report_a = load_report(REPORT_A_PATH)
    report_b = load_report(REPORT_B_PATH)
    print(f"Loaded reports: {REPORT_A_PATH}, {REPORT_B_PATH}")


if __name__ == "__main__":
    main()
```

**Step 2: Run to verify loading works**

```bash
python 5-seo-diff.py
```

Expected: "Loaded reports: ..." message

---

## Task 2: Comparison Type Detection

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add site identifier extraction and comparison type detection**

```python
from urllib.parse import urlparse


def extract_site_id(report: dict) -> str:
    """Extract site identifier from report (canonical URL or file path)."""
    if report.get("canonical") and report["canonical"].get("url"):
        parsed = urlparse(report["canonical"]["url"])
        return parsed.netloc.replace("www.", "")
    # Fallback: extract from file_path like "scraped/snaptik_app_archive/..."
    file_path = report.get("file_path", "")
    parts = file_path.split("/")
    if len(parts) >= 2:
        return parts[1].replace("_", ".")
    return "unknown"


def detect_comparison_type(report_a: dict, report_b: dict) -> str:
    """Detect if temporal (same site) or competitor (different sites)."""
    site_a = extract_site_id(report_a)
    site_b = extract_site_id(report_b)
    return "temporal" if site_a == site_b else "competitor"
```

**Step 2: Update main to use detection**

```python
def main() -> None:
    report_a = load_report(REPORT_A_PATH)
    report_b = load_report(REPORT_B_PATH)
    
    site_a = extract_site_id(report_a)
    site_b = extract_site_id(report_b)
    comp_type = detect_comparison_type(report_a, report_b)
    
    print(f"Site A: {site_a}")
    print(f"Site B: {site_b}")
    print(f"Comparison type: {comp_type}")
```

**Step 3: Run to verify detection**

```bash
python 5-seo-diff.py
```

Expected: Shows site IDs and "temporal" for same-site comparison

---

## Task 3: Summary Statistics Calculation

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add dataclass for category stats**

```python
from dataclasses import dataclass


@dataclass
class CategoryStats:
    """Statistics for a single category comparison."""
    name: str
    value_a: str
    value_b: str
    has_diff: bool
    delta: str  # e.g., "+2", "-15%", "same"
```

**Step 2: Add stats extraction functions**

```python
def get_category_stats(report_a: dict, report_b: dict) -> list[CategoryStats]:
    """Calculate summary stats for all categories."""
    stats = []
    
    # Title
    title_a = report_a.get("title", {})
    title_b = report_b.get("title", {})
    len_a = title_a.get("length", 0)
    len_b = title_b.get("length", 0)
    text_a = title_a.get("text", "")
    text_b = title_b.get("text", "")
    stats.append(CategoryStats(
        name="Title",
        value_a=f"{len_a} chars",
        value_b=f"{len_b} chars",
        has_diff=text_a != text_b,
        delta="═ same" if text_a == text_b else f"changed"
    ))
    
    # Meta Description
    meta_a = report_a.get("meta_description", {})
    meta_b = report_b.get("meta_description", {})
    len_a = meta_a.get("length", 0)
    len_b = meta_b.get("length", 0)
    text_a = meta_a.get("text", "")
    text_b = meta_b.get("text", "")
    stats.append(CategoryStats(
        name="Meta Description",
        value_a=f"{len_a} chars",
        value_b=f"{len_b} chars",
        has_diff=text_a != text_b,
        delta="═ same" if text_a == text_b else f"changed"
    ))
    
    # H1
    h1_a = report_a.get("h1", {})
    h1_b = report_b.get("h1", {})
    text_a = h1_a.get("text", "")
    text_b = h1_b.get("text", "")
    stats.append(CategoryStats(
        name="H1",
        value_a="present" if text_a else "missing",
        value_b="present" if text_b else "missing",
        has_diff=text_a != text_b,
        delta="═ same" if text_a == text_b else "changed"
    ))
    
    # Headings count
    headings_a = report_a.get("headings_hierarchy", {}).get("headings", [])
    headings_b = report_b.get("headings_hierarchy", {}).get("headings", [])
    count_a, count_b = len(headings_a), len(headings_b)
    diff = count_b - count_a
    stats.append(CategoryStats(
        name="Headings",
        value_a=str(count_a),
        value_b=str(count_b),
        has_diff=count_a != count_b,
        delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}"
    ))
    
    # Internal Links
    links_a = report_a.get("links", [])
    links_b = report_b.get("links", [])
    int_a = sum(1 for l in links_a if l.get("is_internal"))
    int_b = sum(1 for l in links_b if l.get("is_internal"))
    diff = int_b - int_a
    stats.append(CategoryStats(
        name="Internal Links",
        value_a=str(int_a),
        value_b=str(int_b),
        has_diff=int_a != int_b,
        delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}"
    ))
    
    # External Links
    ext_a = sum(1 for l in links_a if not l.get("is_internal"))
    ext_b = sum(1 for l in links_b if not l.get("is_internal"))
    diff = ext_b - ext_a
    stats.append(CategoryStats(
        name="External Links",
        value_a=str(ext_a),
        value_b=str(ext_b),
        has_diff=ext_a != ext_b,
        delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}"
    ))
    
    # Images
    img_a = len(report_a.get("images", []))
    img_b = len(report_b.get("images", []))
    diff = img_b - img_a
    stats.append(CategoryStats(
        name="Images",
        value_a=str(img_a),
        value_b=str(img_b),
        has_diff=img_a != img_b,
        delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}"
    ))
    
    # Schemas
    schema_a = len(report_a.get("schemas", []))
    schema_b = len(report_b.get("schemas", []))
    diff = schema_b - schema_a
    stats.append(CategoryStats(
        name="Schemas",
        value_a=str(schema_a),
        value_b=str(schema_b),
        has_diff=schema_a != schema_b,
        delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}"
    ))
    
    # Hreflangs
    href_a = len(report_a.get("hreflangs", []))
    href_b = len(report_b.get("hreflangs", []))
    diff = href_b - href_a
    stats.append(CategoryStats(
        name="Hreflangs",
        value_a=str(href_a),
        value_b=str(href_b),
        has_diff=href_a != href_b,
        delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}"
    ))
    
    # Word Count
    kw_a = report_a.get("keywords", {})
    kw_b = report_b.get("keywords", {})
    words_a = kw_a.get("total_words", 0)
    words_b = kw_b.get("total_words", 0)
    if words_a > 0:
        pct = ((words_b - words_a) / words_a) * 100
        delta = f"△ +{pct:.1f}%" if pct > 0 else f"▽ {pct:.1f}%" if pct < 0 else "═ same"
    else:
        delta = "═ same" if words_a == words_b else "changed"
    stats.append(CategoryStats(
        name="Word Count",
        value_a=str(words_a),
        value_b=str(words_b),
        has_diff=words_a != words_b,
        delta=delta
    ))
    
    # Issues
    issues_a = len(report_a.get("issues", []))
    issues_b = len(report_b.get("issues", []))
    diff = issues_b - issues_a
    stats.append(CategoryStats(
        name="Issues",
        value_a=str(issues_a),
        value_b=str(issues_b),
        has_diff=issues_a != issues_b,
        delta="═ same" if diff == 0 else f"▼ +{diff}" if diff > 0 else f"▲ {diff}"
    ))
    
    return stats
```

---

## Task 4: Summary Table Rendering

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add header and summary table rendering**

```python
def print_header(
    report_a: dict, 
    report_b: dict, 
    site_a: str, 
    site_b: str, 
    comp_type: str
) -> None:
    """Print the report header."""
    print()
    print(f"{BOLD}{'═' * 79}{RESET}")
    
    if comp_type == "temporal":
        print(f"{BOLD} SEO DIFF: {site_a} (over time){RESET}")
    else:
        print(f"{BOLD} SEO COMPARISON: {site_a} vs {site_b}{RESET}")
    
    print(f"{'═' * 79}")
    
    label_a = "[OLD]" if comp_type == "temporal" else "[A]"
    label_b = "[NEW]" if comp_type == "temporal" else "[B]"
    
    print(f"  {label_a} {report_a.get('file_path', 'unknown')}")
    print(f"  {label_b} {report_b.get('file_path', 'unknown')}")
    print(f"{'═' * 79}")
    print()


def print_summary_table(
    stats: list[CategoryStats], 
    site_a: str, 
    site_b: str, 
    comp_type: str
) -> None:
    """Print the summary comparison table."""
    col_a = "OLD" if comp_type == "temporal" else site_a[:12]
    col_b = "NEW" if comp_type == "temporal" else site_b[:12]
    delta_col = "Change" if comp_type == "temporal" else "Difference"
    
    # Table header
    print(f"┌{'─' * 21}┬{'─' * 14}┬{'─' * 14}┬{'─' * 14}┐")
    print(f"│ {'Category':<19} │ {col_a:<12} │ {col_b:<12} │ {delta_col:<12} │")
    print(f"├{'─' * 21}┼{'─' * 14}┼{'─' * 14}┼{'─' * 14}┤")
    
    # Table rows
    for s in stats:
        delta_color = ""
        if s.has_diff:
            if "△" in s.delta or "▲" in s.delta:
                delta_color = GREEN
            elif "▽" in s.delta or "▼" in s.delta:
                delta_color = RED
            else:
                delta_color = YELLOW
        
        delta_display = f"{delta_color}{s.delta}{RESET}" if s.has_diff else f"{DIM}{s.delta}{RESET}"
        
        print(f"│ {s.name:<19} │ {s.value_a:<12} │ {s.value_b:<12} │ {delta_display:<23} │")
    
    print(f"└{'─' * 21}┴{'─' * 14}┴{'─' * 14}┴{'─' * 14}┘")
    
    # Summary line
    diff_count = sum(1 for s in stats if s.has_diff)
    categories_with_diff = sum(1 for s in stats if s.has_diff)
    print()
    if diff_count == 0:
        print(f"{GREEN}No differences found{RESET}")
    else:
        print(f"{YELLOW}{diff_count} difference(s) found across {categories_with_diff} categories{RESET}")
    print()
```

**Step 2: Update main to render header and table**

```python
def main() -> None:
    report_a = load_report(REPORT_A_PATH)
    report_b = load_report(REPORT_B_PATH)
    
    site_a = extract_site_id(report_a)
    site_b = extract_site_id(report_b)
    comp_type = detect_comparison_type(report_a, report_b)
    
    print_header(report_a, report_b, site_a, site_b, comp_type)
    
    stats = get_category_stats(report_a, report_b)
    print_summary_table(stats, site_a, site_b, comp_type)
```

**Step 3: Run and verify table output**

```bash
python 5-seo-diff.py
```

---

## Task 5: Detailed Diff - Title, Meta, H1, Canonical

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add text diff helper and simple field diffs**

```python
def print_section_header(name: str) -> None:
    """Print a section header."""
    print(f"── {name} {'─' * (75 - len(name))}")


def diff_text_field(
    name: str,
    val_a: str | None,
    val_b: str | None,
    comp_type: str
) -> bool:
    """Diff a simple text field. Returns True if diff was printed."""
    if val_a == val_b:
        return False
    
    print_section_header(name.upper())
    
    label_a = "[OLD]" if comp_type == "temporal" else "[A]"
    label_b = "[NEW]" if comp_type == "temporal" else "[B]"
    
    # Truncate long text for display
    def truncate(s: str | None, max_len: int = 60) -> str:
        if not s:
            return "(empty)"
        return s[:max_len] + "..." if len(s) > max_len else s
    
    print(f"  {label_a} \"{truncate(val_a)}\"")
    print(f"  {label_b} \"{truncate(val_b)}\"")
    
    if comp_type == "temporal":
        print(f"  {YELLOW}← CHANGED{RESET}")
    
    print()
    return True


def print_detailed_diffs(report_a: dict, report_b: dict, comp_type: str) -> None:
    """Print detailed diffs for categories with changes."""
    print(f"{BOLD}{'═' * 79}{RESET}")
    print()
    
    any_diff = False
    
    # Title
    title_a = report_a.get("title", {}).get("text")
    title_b = report_b.get("title", {}).get("text")
    if diff_text_field("Title", title_a, title_b, comp_type):
        any_diff = True
    
    # Meta Description
    meta_a = report_a.get("meta_description", {}).get("text")
    meta_b = report_b.get("meta_description", {}).get("text")
    if diff_text_field("Meta Description", meta_a, meta_b, comp_type):
        any_diff = True
    
    # H1
    h1_a = report_a.get("h1", {}).get("text")
    h1_b = report_b.get("h1", {}).get("text")
    if diff_text_field("H1", h1_a, h1_b, comp_type):
        any_diff = True
    
    # Canonical
    canon_a = report_a.get("canonical", {}).get("url")
    canon_b = report_b.get("canonical", {}).get("url")
    if diff_text_field("Canonical", canon_a, canon_b, comp_type):
        any_diff = True
    
    if not any_diff:
        print(f"{DIM}No text field changes to display{RESET}")
        print()
```

**Step 2: Call from main**

```python
def main() -> None:
    # ... existing code ...
    print_summary_table(stats, site_a, site_b, comp_type)
    print_detailed_diffs(report_a, report_b, comp_type)
```

---

## Task 6: Detailed Diff - Headings

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add headings diff function**

```python
def diff_headings(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff headings hierarchy. Returns True if diff printed."""
    headings_a = report_a.get("headings_hierarchy", {}).get("headings", [])
    headings_b = report_b.get("headings_hierarchy", {}).get("headings", [])
    
    # Create sets of (tag, text) tuples for comparison
    set_a = {(h["tag"], h["text"]) for h in headings_a}
    set_b = {(h["tag"], h["text"]) for h in headings_b}
    
    # Also track by text only to detect tag changes
    text_to_tag_a = {h["text"]: h["tag"] for h in headings_a}
    text_to_tag_b = {h["text"]: h["tag"] for h in headings_b}
    
    added = set_b - set_a
    removed = set_a - set_b
    
    # Find tag changes (same text, different tag)
    tag_changes = []
    texts_a = {h["text"] for h in headings_a}
    texts_b = {h["text"] for h in headings_b}
    common_texts = texts_a & texts_b
    
    for text in common_texts:
        tag_a = text_to_tag_a.get(text)
        tag_b = text_to_tag_b.get(text)
        if tag_a != tag_b:
            tag_changes.append((text, tag_a, tag_b))
            # Remove from added/removed since it's a change
            added.discard((tag_b, text))
            removed.discard((tag_a, text))
    
    if not added and not removed and not tag_changes:
        return False
    
    print_section_header("HEADINGS")
    
    label_a = "OLD" if comp_type == "temporal" else "A"
    label_b = "NEW" if comp_type == "temporal" else "B"
    
    for tag, text in sorted(removed):
        truncated = text[:50] + "..." if len(text) > 50 else text
        if comp_type == "temporal":
            print(f"  {RED}- {tag}: \"{truncated}\"{RESET}  ← REMOVED")
        else:
            print(f"  {RED}[{label_a} only] {tag}: \"{truncated}\"{RESET}")
    
    for tag, text in sorted(added):
        truncated = text[:50] + "..." if len(text) > 50 else text
        if comp_type == "temporal":
            print(f"  {GREEN}+ {tag}: \"{truncated}\"{RESET}  ← ADDED")
        else:
            print(f"  {GREEN}[{label_b} only] {tag}: \"{truncated}\"{RESET}")
    
    for text, tag_a, tag_b in tag_changes:
        truncated = text[:40] + "..." if len(text) > 40 else text
        print(f"  {YELLOW}~ {tag_b}: \"{truncated}\" (was {tag_a}){RESET}  ← TAG CHANGED")
    
    print()
    return True
```

**Step 2: Add to print_detailed_diffs**

Add after canonical diff:

```python
    # Headings
    if diff_headings(report_a, report_b, comp_type):
        any_diff = True
```

---

## Task 7: Detailed Diff - Links

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add links diff function**

```python
def diff_links(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff links. Returns True if diff printed."""
    links_a = report_a.get("links", [])
    links_b = report_b.get("links", [])
    
    # Index by href
    href_to_link_a = {l["href"]: l for l in links_a}
    href_to_link_b = {l["href"]: l for l in links_b}
    
    hrefs_a = set(href_to_link_a.keys())
    hrefs_b = set(href_to_link_b.keys())
    
    added = hrefs_b - hrefs_a
    removed = hrefs_a - hrefs_b
    common = hrefs_a & hrefs_b
    
    # Check for status changes in common links
    status_changes = []
    for href in common:
        status_a = href_to_link_a[href].get("status")
        status_b = href_to_link_b[href].get("status")
        if status_a != status_b and (status_a is not None or status_b is not None):
            status_changes.append((href, status_a, status_b))
    
    if not added and not removed and not status_changes:
        return False
    
    print_section_header("LINKS")
    
    label_a = "OLD" if comp_type == "temporal" else "A"
    label_b = "NEW" if comp_type == "temporal" else "B"
    
    # Show max 10 of each type to avoid overwhelming output
    max_show = 10
    
    removed_list = sorted(removed)[:max_show]
    for href in removed_list:
        anchor = href_to_link_a[href].get("anchor", "")[:30]
        if comp_type == "temporal":
            print(f"  {RED}- {href}{RESET}")
            if anchor:
                print(f"    {DIM}anchor: \"{anchor}\"{RESET}")
        else:
            print(f"  {RED}[{label_a} only] {href}{RESET}")
    if len(removed) > max_show:
        print(f"  {DIM}... and {len(removed) - max_show} more removed{RESET}")
    
    added_list = sorted(added)[:max_show]
    for href in added_list:
        anchor = href_to_link_b[href].get("anchor", "")[:30]
        if comp_type == "temporal":
            print(f"  {GREEN}+ {href}{RESET}")
            if anchor:
                print(f"    {DIM}anchor: \"{anchor}\"{RESET}")
        else:
            print(f"  {GREEN}[{label_b} only] {href}{RESET}")
    if len(added) > max_show:
        print(f"  {DIM}... and {len(added) - max_show} more added{RESET}")
    
    for href, status_a, status_b in status_changes[:max_show]:
        status_a_str = str(status_a) if status_a else "?"
        status_b_str = str(status_b) if status_b else "?"
        color = RED if status_b and status_b >= 400 else YELLOW
        print(f"  {color}~ {href}{RESET}")
        print(f"    {DIM}status: {status_a_str} → {status_b_str}{RESET}")
    
    print()
    return True
```

**Step 2: Add to print_detailed_diffs**

---

## Task 8: Detailed Diff - Keywords

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add keywords diff function**

```python
def diff_keywords(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff keyword rankings. Returns True if diff printed."""
    kw_a = report_a.get("keywords", {})
    kw_b = report_b.get("keywords", {})
    
    terms_a = {t["term"]: t["count"] for t in kw_a.get("top_terms", [])}
    terms_b = {t["term"]: t["count"] for t in kw_b.get("top_terms", [])}
    
    all_terms = set(terms_a.keys()) | set(terms_b.keys())
    
    changes = []
    for term in all_terms:
        count_a = terms_a.get(term, 0)
        count_b = terms_b.get(term, 0)
        
        if count_a == 0 and count_b > 0:
            changes.append((term, "added", 0, count_b))
        elif count_b == 0 and count_a > 0:
            changes.append((term, "removed", count_a, 0))
        elif count_a != count_b:
            changes.append((term, "changed", count_a, count_b))
    
    if not changes:
        return False
    
    print_section_header("KEYWORDS (Top Terms)")
    
    # Sort by absolute change magnitude
    changes.sort(key=lambda x: abs(x[3] - x[2]), reverse=True)
    
    for term, change_type, count_a, count_b in changes[:15]:
        if change_type == "added":
            print(f"  {GREEN}+ \"{term}\" ({count_b}){RESET}  ← new in top terms")
        elif change_type == "removed":
            print(f"  {RED}- \"{term}\" ({count_a}){RESET}  ← dropped from top terms")
        else:
            diff = count_b - count_a
            if count_a > 0:
                pct = (diff / count_a) * 100
                pct_str = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
            else:
                pct_str = "new"
            
            icon = "📈" if diff > 0 else "📉"
            color = GREEN if diff > 0 else RED
            print(f"  {icon} {color}\"{term}\"  {count_a} → {count_b} ({pct_str}){RESET}")
    
    if len(changes) > 15:
        print(f"  {DIM}... and {len(changes) - 15} more changes{RESET}")
    
    print()
    return True
```

---

## Task 9: Detailed Diff - Issues

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Add issues diff function**

```python
def diff_issues(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff issues. Returns True if diff printed."""
    issues_a = report_a.get("issues", [])
    issues_b = report_b.get("issues", [])
    
    # Create comparable keys
    def issue_key(issue: dict) -> tuple:
        return (issue.get("severity", ""), issue.get("category", ""), issue.get("message", ""))
    
    set_a = {issue_key(i) for i in issues_a}
    set_b = {issue_key(i) for i in issues_b}
    
    resolved = set_a - set_b
    new_issues = set_b - set_a
    persisting = set_a & set_b
    
    if not resolved and not new_issues:
        return False
    
    print_section_header("ISSUES")
    
    label_a = "OLD" if comp_type == "temporal" else "A"
    label_b = "NEW" if comp_type == "temporal" else "B"
    
    for sev, cat, msg in sorted(new_issues):
        if comp_type == "temporal":
            print(f"  {RED}+ [{sev}] {cat}: {msg}{RESET}  ← NEW ISSUE")
        else:
            print(f"  {RED}[{label_b} only] [{sev}] {cat}: {msg}{RESET}")
    
    for sev, cat, msg in sorted(resolved):
        if comp_type == "temporal":
            print(f"  {GREEN}- [{sev}] {cat}: {msg}{RESET}  ← RESOLVED")
        else:
            print(f"  {GREEN}[{label_a} only] [{sev}] {cat}: {msg}{RESET}")
    
    if persisting and comp_type == "temporal":
        print()
        print(f"  {DIM}Persisting issues ({len(persisting)}):{RESET}")
        for sev, cat, msg in sorted(persisting)[:5]:
            print(f"  {DIM}═ [{sev}] {cat}: {msg}{RESET}")
        if len(persisting) > 5:
            print(f"  {DIM}... and {len(persisting) - 5} more{RESET}")
    
    print()
    return True
```

---

## Task 10: Final Assembly and Testing

**Files:**

- Modify: `5-seo-diff.py`

**Step 1: Complete print_detailed_diffs with all sections**

```python
def print_detailed_diffs(report_a: dict, report_b: dict, comp_type: str) -> None:
    """Print detailed diffs for categories with changes."""
    print(f"{BOLD}{'═' * 79}{RESET}")
    print()
    
    any_diff = False
    
    # Text fields
    title_a = report_a.get("title", {}).get("text")
    title_b = report_b.get("title", {}).get("text")
    if diff_text_field("Title", title_a, title_b, comp_type):
        any_diff = True
    
    meta_a = report_a.get("meta_description", {}).get("text")
    meta_b = report_b.get("meta_description", {}).get("text")
    if diff_text_field("Meta Description", meta_a, meta_b, comp_type):
        any_diff = True
    
    h1_a = report_a.get("h1", {}).get("text")
    h1_b = report_b.get("h1", {}).get("text")
    if diff_text_field("H1", h1_a, h1_b, comp_type):
        any_diff = True
    
    canon_a = report_a.get("canonical", {}).get("url")
    canon_b = report_b.get("canonical", {}).get("url")
    if diff_text_field("Canonical", canon_a, canon_b, comp_type):
        any_diff = True
    
    # Structured diffs
    if diff_headings(report_a, report_b, comp_type):
        any_diff = True
    
    if diff_links(report_a, report_b, comp_type):
        any_diff = True
    
    if diff_keywords(report_a, report_b, comp_type):
        any_diff = True
    
    if diff_issues(report_a, report_b, comp_type):
        any_diff = True
    
    if not any_diff:
        print(f"{GREEN}Reports are identical - no detailed differences to show{RESET}")
    
    print(f"{BOLD}{'═' * 79}{RESET}")
```

**Step 2: Run full test with both temporal reports**

```bash
python 5-seo-diff.py
```

**Step 3: Test with competitor comparison (change config)**

Update config to compare two different sites:

```python
REPORT_A_PATH = "scraped/aipornrank_com/200-index_seo_report.json"
REPORT_B_PATH = "scraped/aipornrank_com/200-ai-hentai-generators_seo_report.json"
```

Run and verify competitor mode labels appear.

---

## Task 11: Worklog Entry

**Files:**

- Create: `.cursor/worklogs/0000009-seo-diff-tool.md`

**Content:**

```markdown
# Worklog: SEO Diff Tool

## Summary

Built `5-seo-diff.py` - a terminal-based tool that compares two SEO report JSON files and displays only the differences.

## Changes Made

1. Created `5-seo-diff.py` with:
   - JSON report loading
   - Comparison type detection (temporal vs competitor)
   - Summary statistics table
   - Detailed diff sections for: title, meta, H1, canonical, headings, links, keywords, issues

## Features

- Adaptive labeling: [OLD]/[NEW] for temporal, [A]/[B] for competitor
- Color-coded output: green=additions, red=removals, yellow=changes
- Summary table shows quick overview of all categories
- Detailed sections only show categories with actual differences
- Handles large link/heading lists with truncation

## Usage

Configure paths at top of script:
```python
REPORT_A_PATH = "path/to/first_seo_report.json"
REPORT_B_PATH = "path/to/second_seo_report.json"
```

Run: `python 5-seo-diff.py`

```

```

