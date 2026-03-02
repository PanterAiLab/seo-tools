"""SEO Diff Tool: compares two SEO report JSON files and displays differences.

Supports temporal comparison (same site over time) and competitor comparison
(different sites). Omits identical data, focuses on changes.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

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


@dataclass
class CategoryStats:
    """Statistics for a single category comparison."""

    name: str
    value_a: str
    value_b: str
    has_diff: bool
    delta: str


def extract_site_id(report: dict) -> str:
    """Extract site identifier from report (canonical URL or file path)."""
    if report.get("canonical") and report["canonical"].get("url"):
        parsed = urlparse(report["canonical"]["url"])
        return parsed.netloc.replace("www.", "")
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
    stats.append(
        CategoryStats(
            name="Title",
            value_a=f"{len_a} chars",
            value_b=f"{len_b} chars",
            has_diff=text_a != text_b,
            delta="═ same" if text_a == text_b else "changed",
        )
    )

    # Meta Description
    meta_a = report_a.get("meta_description", {})
    meta_b = report_b.get("meta_description", {})
    len_a = meta_a.get("length", 0)
    len_b = meta_b.get("length", 0)
    text_a = meta_a.get("text", "")
    text_b = meta_b.get("text", "")
    stats.append(
        CategoryStats(
            name="Meta Description",
            value_a=f"{len_a} chars",
            value_b=f"{len_b} chars",
            has_diff=text_a != text_b,
            delta="═ same" if text_a == text_b else "changed",
        )
    )

    # H1
    h1_a = report_a.get("h1", {})
    h1_b = report_b.get("h1", {})
    text_a = h1_a.get("text", "")
    text_b = h1_b.get("text", "")
    stats.append(
        CategoryStats(
            name="H1",
            value_a="present" if text_a else "missing",
            value_b="present" if text_b else "missing",
            has_diff=text_a != text_b,
            delta="═ same" if text_a == text_b else "changed",
        )
    )

    # Headings count
    headings_a = report_a.get("headings_hierarchy", {}).get("headings", [])
    headings_b = report_b.get("headings_hierarchy", {}).get("headings", [])
    count_a, count_b = len(headings_a), len(headings_b)
    diff = count_b - count_a
    stats.append(
        CategoryStats(
            name="Headings",
            value_a=str(count_a),
            value_b=str(count_b),
            has_diff=count_a != count_b,
            delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}",
        )
    )

    # Internal Links
    links_a = report_a.get("links", [])
    links_b = report_b.get("links", [])
    int_a = sum(1 for link in links_a if link.get("is_internal"))
    int_b = sum(1 for link in links_b if link.get("is_internal"))
    diff = int_b - int_a
    stats.append(
        CategoryStats(
            name="Internal Links",
            value_a=str(int_a),
            value_b=str(int_b),
            has_diff=int_a != int_b,
            delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}",
        )
    )

    # External Links
    ext_a = sum(1 for link in links_a if not link.get("is_internal"))
    ext_b = sum(1 for link in links_b if not link.get("is_internal"))
    diff = ext_b - ext_a
    stats.append(
        CategoryStats(
            name="External Links",
            value_a=str(ext_a),
            value_b=str(ext_b),
            has_diff=ext_a != ext_b,
            delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}",
        )
    )

    # Images
    img_a = len(report_a.get("images", []))
    img_b = len(report_b.get("images", []))
    diff = img_b - img_a
    stats.append(
        CategoryStats(
            name="Images",
            value_a=str(img_a),
            value_b=str(img_b),
            has_diff=img_a != img_b,
            delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}",
        )
    )

    # Schemas
    schema_a = len(report_a.get("schemas", []))
    schema_b = len(report_b.get("schemas", []))
    diff = schema_b - schema_a
    stats.append(
        CategoryStats(
            name="Schemas",
            value_a=str(schema_a),
            value_b=str(schema_b),
            has_diff=schema_a != schema_b,
            delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}",
        )
    )

    # Hreflangs
    href_a = len(report_a.get("hreflangs", []))
    href_b = len(report_b.get("hreflangs", []))
    diff = href_b - href_a
    stats.append(
        CategoryStats(
            name="Hreflangs",
            value_a=str(href_a),
            value_b=str(href_b),
            has_diff=href_a != href_b,
            delta="═ same" if diff == 0 else f"△ +{diff}" if diff > 0 else f"▽ {diff}",
        )
    )

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
    stats.append(
        CategoryStats(
            name="Word Count",
            value_a=str(words_a),
            value_b=str(words_b),
            has_diff=words_a != words_b,
            delta=delta,
        )
    )

    # Issues
    issues_a = len(report_a.get("issues", []))
    issues_b = len(report_b.get("issues", []))
    diff = issues_b - issues_a
    stats.append(
        CategoryStats(
            name="Issues",
            value_a=str(issues_a),
            value_b=str(issues_b),
            has_diff=issues_a != issues_b,
            delta="═ same" if diff == 0 else f"▼ +{diff}" if diff > 0 else f"▲ {diff}",
        )
    )

    return stats


def load_report(path: str) -> dict:
    """Load SEO report JSON file."""
    file_path = Path(path)
    if not file_path.exists():
        print(f"{RED}ERROR: File not found: {path}{RESET}")
        sys.exit(1)
    return json.loads(file_path.read_text(encoding="utf-8"))


def print_header(
    report_a: dict,
    report_b: dict,
    site_a: str,
    site_b: str,
    comp_type: str,
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
    comp_type: str,
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

        delta_display = (
            f"{delta_color}{s.delta}{RESET}" if s.has_diff else f"{DIM}{s.delta}{RESET}"
        )

        print(
            f"│ {s.name:<19} │ {s.value_a:<12} │ {s.value_b:<12} │ {delta_display:<23} │"
        )

    print(f"└{'─' * 21}┴{'─' * 14}┴{'─' * 14}┴{'─' * 14}┘")

    # Summary line
    diff_count = sum(1 for s in stats if s.has_diff)
    print()
    if diff_count == 0:
        print(f"{GREEN}No differences found{RESET}")
    else:
        print(f"{YELLOW}{diff_count} difference(s) found{RESET}")
    print()


def print_section_header(name: str) -> None:
    """Print a section header."""
    print(f"── {name} {'─' * (75 - len(name))}")


def diff_text_field(
    name: str,
    val_a: str | None,
    val_b: str | None,
    comp_type: str,
) -> bool:
    """Diff a simple text field. Returns True if diff was printed."""
    if val_a == val_b:
        return False

    print_section_header(name.upper())

    label_a = "[OLD]" if comp_type == "temporal" else "[A]"
    label_b = "[NEW]" if comp_type == "temporal" else "[B]"

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


def diff_links(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff links. Returns True if diff printed."""
    links_a = report_a.get("links", [])
    links_b = report_b.get("links", [])

    # Index by href
    href_to_link_a = {link["href"]: link for link in links_a}
    href_to_link_b = {link["href"]: link for link in links_b}

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
        link = href_to_link_a[href]
        anchor = link.get("anchor", "").strip()[:30]
        content_type = link.get("content_type", "text")
        if comp_type == "temporal":
            print(f"  {RED}- {href}{RESET}")
            if anchor:
                print(f"    {DIM}anchor: \"{anchor}\"{RESET}")
            elif content_type != "text":
                print(f"    {DIM}({content_type} link){RESET}")
            else:
                print(f"    {DIM}(empty link){RESET}")
        else:
            print(f"  {RED}[{label_a} only] {href}{RESET}")
    if len(removed) > max_show:
        print(f"  {DIM}... and {len(removed) - max_show} more removed{RESET}")

    added_list = sorted(added)[:max_show]
    for href in added_list:
        link = href_to_link_b[href]
        anchor = link.get("anchor", "").strip()[:30]
        content_type = link.get("content_type", "text")
        if comp_type == "temporal":
            print(f"  {GREEN}+ {href}{RESET}")
            if anchor:
                print(f"    {DIM}anchor: \"{anchor}\"{RESET}")
            elif content_type != "text":
                print(f"    {DIM}({content_type} link){RESET}")
            else:
                print(f"    {DIM}(empty link){RESET}")
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

    for term, change_type, count_a, count_b in changes[:10]:
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

    if len(changes) > 10:
        print(f"  {DIM}... and {len(changes) - 10} more changes{RESET}")

    print()
    return True


def diff_schemas(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff structured data schemas. Returns True if diff printed."""
    schemas_a = report_a.get("schemas", [])
    schemas_b = report_b.get("schemas", [])

    # Extract schema types
    types_a = {s.get("type", "Unknown") for s in schemas_a}
    types_b = {s.get("type", "Unknown") for s in schemas_b}

    added = types_b - types_a
    removed = types_a - types_b
    common = types_a & types_b

    # For common schemas, check if content changed (by comparing raw JSON)
    content_changes = []
    for schema_type in common:
        raw_a = next(
            (s.get("raw", {}) for s in schemas_a if s.get("type") == schema_type), {}
        )
        raw_b = next(
            (s.get("raw", {}) for s in schemas_b if s.get("type") == schema_type), {}
        )
        if raw_a != raw_b:
            content_changes.append(schema_type)

    if not added and not removed and not content_changes:
        return False

    print_section_header("SCHEMAS (Structured Data)")

    label_a = "OLD" if comp_type == "temporal" else "A"
    label_b = "NEW" if comp_type == "temporal" else "B"

    for schema_type in sorted(removed):
        if comp_type == "temporal":
            print(f"  {RED}- {schema_type}{RESET}  ← REMOVED")
        else:
            print(f"  {RED}[{label_a} only] {schema_type}{RESET}")

    for schema_type in sorted(added):
        if comp_type == "temporal":
            print(f"  {GREEN}+ {schema_type}{RESET}  ← ADDED")
        else:
            print(f"  {GREEN}[{label_b} only] {schema_type}{RESET}")

    for schema_type in sorted(content_changes):
        if comp_type == "temporal":
            print(f"  {YELLOW}~ {schema_type}{RESET}  ← CONTENT CHANGED")
        else:
            print(f"  {YELLOW}~ {schema_type}{RESET}  ← different content")

    print()
    return True


def diff_issues(report_a: dict, report_b: dict, comp_type: str) -> bool:
    """Diff issues. Returns True if diff printed."""
    issues_a = report_a.get("issues", [])
    issues_b = report_b.get("issues", [])

    def issue_key(issue: dict) -> tuple:
        return (
            issue.get("severity", ""),
            issue.get("category", ""),
            issue.get("message", ""),
        )

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

    # Headings
    if diff_headings(report_a, report_b, comp_type):
        any_diff = True

    # Links
    if diff_links(report_a, report_b, comp_type):
        any_diff = True

    # Keywords
    if diff_keywords(report_a, report_b, comp_type):
        any_diff = True

    # Schemas
    if diff_schemas(report_a, report_b, comp_type):
        any_diff = True

    # Issues
    if diff_issues(report_a, report_b, comp_type):
        any_diff = True

    if not any_diff:
        print(f"{DIM}No detailed differences to display{RESET}")
        print()

    print(f"{BOLD}{'═' * 79}{RESET}")


def main() -> None:
    """Main entry point."""
    report_a = load_report(REPORT_A_PATH)
    report_b = load_report(REPORT_B_PATH)

    site_a = extract_site_id(report_a)
    site_b = extract_site_id(report_b)
    comp_type = detect_comparison_type(report_a, report_b)

    print_header(report_a, report_b, site_a, site_b, comp_type)

    stats = get_category_stats(report_a, report_b)
    print_summary_table(stats, site_a, site_b, comp_type)
    print_detailed_diffs(report_a, report_b, comp_type)


if __name__ == "__main__":
    main()
