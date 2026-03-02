"""SEO Page Checker: analyzes HTML pages for SEO best practices.

Reads a local HTML file and produces a structured JSON report
for SEO analysis and cross-page comparison.
"""

import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from models_seo import Issue, PageSEOReport
from utils_files import get_website_id
from utils_links import (
    extract_images,
    extract_links,
    lookup_internal_link_status,
    verify_external_links,
)
from utils_requests import get_session
from utils_seo import (
    extract_canonical,
    extract_faq_sections,
    extract_h1,
    extract_headings,
    extract_hreflang,
    extract_keywords,
    extract_localization,
    extract_meta_description,
    extract_open_graph,
    extract_robots_meta,
    extract_scripts,
    extract_structured_data,
    extract_title,
    extract_twitter_card,
    extract_viewport,
)

# ──────────────────────────────────────────────
# CONFIGURATION - edit these values before running
# ──────────────────────────────────────────────

# HTML_FILE_PATH = "scraped/snaptik_app_archive/20230220-192556.html"
HTML_FILE_PATH = "scraped/snaptik_app_archive/20240609-175516.html"
WEBSITE_URL = "https://snaptik.app"
SCRAPED_DIR = Path("scraped")
PARALLELISM = 10

HTTP_AUTH_USERNAME = ""
HTTP_AUTH_PASSWORD = ""

# ──────────────────────────────────────────────

# ANSI color codes for terminal output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def derive_page_url(file_path: Path, website_url: str, scraped_dir: Path) -> str:
    """Derive the page URL from the file path.

    Given: scraped/example_com/blog/200-post-1.html
    With website_url: https://example.com
    Result: https://example.com/blog/post-1

    The logic:
    1. Remove scraped/{website_id}/ prefix
    2. Parse filename: remove status code prefix (200-) and .html extension
    3. Combine with website_url

    Args:
        file_path: Path to the HTML file.
        website_url: The root website URL.
        scraped_dir: The scraped directory root.

    Returns:
        The derived page URL.
    """
    website_id = get_website_id(website_url)
    website_dir = scraped_dir / website_id

    # Get relative path from website directory
    try:
        relative = file_path.relative_to(website_dir)
    except ValueError:
        # File is not under expected website directory
        relative = file_path

    # Get parent directories (path parts excluding filename)
    parent_parts = list(relative.parent.parts)
    if parent_parts == ["."]:
        parent_parts = []

    # Parse filename: remove status code prefix and .html extension
    stem = relative.stem  # e.g., "200-post-1"
    parts = stem.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit():
        slug = parts[1]
    else:
        slug = stem

    # Handle index pages
    if slug == "index":
        if parent_parts:
            path = "/".join(parent_parts) + "/"
        else:
            path = ""
    else:
        if parent_parts:
            path = "/".join(parent_parts) + "/" + slug
        else:
            path = slug

    # Combine with website URL
    base = website_url.rstrip("/")
    if path:
        return f"{base}/{path}"
    return base


def collect_issues(report: PageSEOReport) -> list[Issue]:
    """Collect all issues from report components into the main issues list.

    Applies severity logic:
    - "error": Missing critical elements (title, H1, canonical), noindex
    - "warning": Length issues, multiple H1s, missing alt text, broken links
    - "info": Hierarchy issues, missing OG/Twitter cards

    Args:
        report: The PageSEOReport with component data.

    Returns:
        List of Issue objects with appropriate severity and category.
    """
    issues: list[Issue] = []

    # Title issues
    if report.title and report.title.issues:
        for issue_text in report.title.issues:
            if "Missing" in issue_text:
                severity = "error"
            else:
                severity = "warning"
            issues.append(Issue(severity=severity, category="title", message=issue_text))

    # Meta description issues
    if report.meta_description and report.meta_description.issues:
        for issue_text in report.meta_description.issues:
            if "Missing" in issue_text:
                severity = "warning"
            else:
                severity = "warning"
            issues.append(
                Issue(severity=severity, category="meta_description", message=issue_text)
            )

    # Canonical issues
    if report.canonical and report.canonical.issues:
        for issue_text in report.canonical.issues:
            severity = "error"
            issues.append(
                Issue(severity=severity, category="canonical", message=issue_text)
            )

    # Robots issues
    if report.robots and report.robots.issues:
        for issue_text in report.robots.issues:
            if "noindex" in issue_text.lower():
                severity = "error"
            else:
                severity = "warning"
            issues.append(Issue(severity=severity, category="robots", message=issue_text))

    # H1 issues
    if report.h1 and report.h1.issues:
        for issue_text in report.h1.issues:
            if "Missing" in issue_text:
                severity = "error"
            else:
                severity = "warning"
            issues.append(Issue(severity=severity, category="h1", message=issue_text))

    # Headings hierarchy issues
    if report.headings_hierarchy and report.headings_hierarchy.issues:
        for issue_text in report.headings_hierarchy.issues:
            issues.append(
                Issue(severity="info", category="headings", message=issue_text)
            )

    # Viewport issues
    if report.viewport and report.viewport.issues:
        for issue_text in report.viewport.issues:
            issues.append(
                Issue(severity="warning", category="viewport", message=issue_text)
            )

    # Image issues (missing alt text)
    images_without_alt = sum(
        1 for img in report.images if img.alt is None or img.alt == ""
    )
    if images_without_alt > 0:
        issues.append(
            Issue(
                severity="warning",
                category="images",
                message=f"{images_without_alt} image(s) missing alt text",
            )
        )

    # Link issues (broken internal links)
    broken_internal = sum(
        1
        for link in report.links
        if link.is_internal and link.status is not None and link.status >= 400
    )
    if broken_internal > 0:
        issues.append(
            Issue(
                severity="warning",
                category="links",
                message=f"{broken_internal} broken internal link(s)",
            )
        )

    # Link issues (broken external links)
    broken_external = sum(
        1
        for link in report.links
        if not link.is_internal and link.status is not None and link.status >= 400
    )
    if broken_external > 0:
        issues.append(
            Issue(
                severity="warning",
                category="links",
                message=f"{broken_external} broken external link(s)",
            )
        )

    # Open Graph issues
    if report.open_graph:
        og = report.open_graph
        missing_og: list[str] = []
        if not og.title:
            missing_og.append("og:title")
        if not og.description:
            missing_og.append("og:description")
        if not og.image:
            missing_og.append("og:image")
        if missing_og:
            issues.append(
                Issue(
                    severity="info",
                    category="open_graph",
                    message=f"Missing Open Graph tags: {', '.join(missing_og)}",
                )
            )

    # Twitter Card issues
    if report.twitter_card:
        tc = report.twitter_card
        if not tc.card:
            issues.append(
                Issue(
                    severity="info",
                    category="twitter_card",
                    message="Missing Twitter Card meta tags",
                )
            )

    return issues


def print_summary(report: PageSEOReport, output_path: Path) -> None:
    """Print a colored terminal summary of the SEO analysis.

    Args:
        report: The completed PageSEOReport.
        output_path: Path where JSON report was saved.
    """
    print()
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}SEO PAGE CHECKER REPORT{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print()

    print(f"  File:     {report.file_path}")
    print(f"  Analyzed: {report.analyzed_at}")
    print()

    # Quick stats
    error_count = sum(1 for i in report.issues if i.severity == "error")
    warning_count = sum(1 for i in report.issues if i.severity == "warning")
    info_count = sum(1 for i in report.issues if i.severity == "info")

    print(f"{BOLD}── Issue Summary ──{RESET}")
    print()
    if error_count > 0:
        print(f"  {RED}Errors:   {error_count}{RESET}")
    else:
        print(f"  {GREEN}Errors:   {error_count}{RESET}")
    if warning_count > 0:
        print(f"  {YELLOW}Warnings: {warning_count}{RESET}")
    else:
        print(f"  {GREEN}Warnings: {warning_count}{RESET}")
    print(f"  {DIM}Info:     {info_count}{RESET}")
    print()

    # Show critical issues (errors)
    errors = [i for i in report.issues if i.severity == "error"]
    if errors:
        print(f"{BOLD}{RED}── Critical Issues ──{RESET}")
        print()
        for issue in errors:
            print(f"  {RED}[ERROR] {issue.category}: {issue.message}{RESET}")
        print()

    # Show warnings
    warnings = [i for i in report.issues if i.severity == "warning"]
    if warnings:
        print(f"{BOLD}{YELLOW}── Warnings ──{RESET}")
        print()
        for issue in warnings:
            print(f"  {YELLOW}[WARN] {issue.category}: {issue.message}{RESET}")
        print()

    # Show info
    infos = [i for i in report.issues if i.severity == "info"]
    if infos:
        print(f"{BOLD}── Suggestions ──{RESET}")
        print()
        for issue in infos:
            print(f"  {DIM}[INFO] {issue.category}: {issue.message}{RESET}")
        print()

    # Content stats
    print(f"{BOLD}── Content Stats ──{RESET}")
    print()
    print(f"  Title:            {report.title.text[:50] + '...' if report.title and report.title.text and len(report.title.text) > 50 else (report.title.text if report.title and report.title.text else 'N/A')}")
    print(f"  H1:               {report.h1.text[:50] + '...' if report.h1 and report.h1.text and len(report.h1.text) > 50 else (report.h1.text if report.h1 and report.h1.text else 'N/A')}")
    print(f"  Internal links:   {sum(1 for l in report.links if l.is_internal)}")
    print(f"  External links:   {sum(1 for l in report.links if not l.is_internal)}")
    print(f"  Images:           {len(report.images)}")
    print(f"  Schemas:          {len(report.schemas)}")
    if report.keywords:
        print(f"  Word count:       {report.keywords.total_words}")
    print()

    # Final output
    print(f"{BOLD}{'=' * 70}{RESET}")
    total_issues = error_count + warning_count + info_count
    if error_count == 0 and warning_count == 0:
        print(f"  {GREEN}{BOLD}All critical checks passed!{RESET}")
    else:
        print(
            f"  {YELLOW}Found {total_issues} issue(s): "
            f"{error_count} error(s), {warning_count} warning(s), {info_count} info{RESET}"
        )
    print()
    print(f"  {CYAN}Report saved to: {output_path}{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")


async def main() -> None:
    """Main page checker entrypoint."""
    file_path = Path(HTML_FILE_PATH)

    # Validate file exists
    if not file_path.exists():
        print(f"{RED}ERROR: File not found: {file_path}{RESET}")
        sys.exit(1)

    print(f"{BOLD}SEO Page Checker{RESET}")
    print(f"  File:    {file_path}")
    print(f"  Website: {WEBSITE_URL}")
    print()

    # Step 1: Load and parse HTML
    print("── Loading HTML ──")
    html_content = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "lxml")
    print(f"  Parsed {len(html_content):,} bytes")

    # Step 2: Derive page URL from file path
    page_url = derive_page_url(file_path, WEBSITE_URL, SCRAPED_DIR)
    print(f"  Derived URL: {page_url}")

    # Step 3: Run all SEO checks
    print()
    print("── Running SEO checks ──")

    title = extract_title(soup)
    print(f"  [OK] Title")

    meta_description = extract_meta_description(soup)
    print(f"  [OK] Meta description")

    canonical = extract_canonical(soup, page_url)
    print(f"  [OK] Canonical")

    robots = extract_robots_meta(soup)
    print(f"  [OK] Robots meta")

    h1 = extract_h1(soup)
    print(f"  [OK] H1")

    headings = extract_headings(soup)
    print(f"  [OK] Headings hierarchy ({len(headings.headings)} headings)")

    open_graph = extract_open_graph(soup)
    print(f"  [OK] Open Graph")

    twitter_card = extract_twitter_card(soup)
    print(f"  [OK] Twitter Card")

    structured_data = extract_structured_data(soup)
    print(f"  [OK] Structured data ({len(structured_data)} schemas)")

    viewport = extract_viewport(soup)
    print(f"  [OK] Viewport")

    hreflangs = extract_hreflang(soup)
    print(f"  [OK] Hreflang ({len(hreflangs)} tags)")

    localization = extract_localization(soup)
    print(f"  [OK] Localization")

    scripts = extract_scripts(soup)
    print(f"  [OK] Scripts ({len(scripts)} scripts)")

    faqs = extract_faq_sections(soup)
    print(f"  [OK] FAQ sections ({len(faqs)} FAQs)")

    keywords = extract_keywords(soup)
    print(f"  [OK] Keywords ({keywords.total_words} words)")

    # Step 4: Process links
    print()
    print("── Processing links ──")

    internal_links, external_links = extract_links(soup, page_url, WEBSITE_URL)
    print(f"  Found {len(internal_links)} internal, {len(external_links)} external links")

    # Lookup internal link status from scraped files
    website_id = get_website_id(WEBSITE_URL)
    scraped_website_dir = SCRAPED_DIR / website_id

    for link in internal_links:
        link.status = lookup_internal_link_status(
            link.href, WEBSITE_URL, scraped_website_dir
        )

    internal_checked = sum(1 for l in internal_links if l.status is not None)
    print(f"  Checked {internal_checked}/{len(internal_links)} internal links from scraped files")

    # Verify external links via HEAD requests
    if external_links:
        print(f"  Verifying {len(external_links)} external links...")
        client = get_session(HTTP_AUTH_USERNAME, HTTP_AUTH_PASSWORD)
        semaphore = asyncio.Semaphore(PARALLELISM)

        async with client:
            await verify_external_links(external_links, client, semaphore)

        external_ok = sum(
            1 for l in external_links if l.status is not None and 200 <= l.status < 400
        )
        print(f"  {external_ok}/{len(external_links)} external links OK")

    # Combine all links
    all_links = internal_links + external_links

    # Step 5: Extract images
    print()
    print("── Processing images ──")
    images = extract_images(soup, page_url)
    images_with_issues = sum(1 for img in images if img.issues)
    print(f"  Found {len(images)} images, {images_with_issues} with issues")

    # Step 6: Build report
    print()
    print("── Building report ──")

    report = PageSEOReport(
        file_path=str(file_path),
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        title=title,
        meta_description=meta_description,
        canonical=canonical,
        robots=robots,
        h1=h1,
        headings_hierarchy=headings,
        links=all_links,
        images=images,
        open_graph=open_graph,
        twitter_card=twitter_card,
        schemas=structured_data,
        viewport=viewport,
        hreflangs=hreflangs,
        localization=localization,
        scripts=scripts,
        faqs=faqs,
        keywords=keywords,
    )

    # Collect all issues
    report.issues = collect_issues(report)

    # Step 7: Write JSON output
    output_path = file_path.with_name(f"{file_path.stem}_seo_report.json")
    report_dict = asdict(report)
    output_path.write_text(
        json.dumps(report_dict, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Saved report to {output_path}")

    # Step 8: Print summary
    print_summary(report, output_path)


if __name__ == "__main__":
    asyncio.run(main())
