"""SEO Sitemap Checker: validates sitemap URLs against downloaded pages.

Cross-references sitemap.xml entries with pages previously scraped by
1-scraper.py. Checks HTTP status codes from filenames, validates sitemap
image URLs via HEAD requests, and produces a detailed report.
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

from utils_files import find_page_file, get_website_id
from utils_html import SitemapEntry, parse_sitemap_detailed
from utils_requests import fetch_head, get_session

# ──────────────────────────────────────────────
# CONFIGURATION - edit these values before running
# ──────────────────────────────────────────────

WEBSITE_URL = "https://aipornrank.com"
PARALLELISM = 20

HTTP_AUTH_USERNAME = ""
HTTP_AUTH_PASSWORD = ""

# ──────────────────────────────────────────────

OUTPUT_DIR = Path("scraped")

# ANSI color codes for terminal output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _status_color(status: int | None) -> str:
    """Return the ANSI color code appropriate for an HTTP status code."""
    if status is None:
        return RED
    if 200 <= status < 300:
        return GREEN
    if 300 <= status < 400:
        return YELLOW
    return RED


def _status_label(status: int | None) -> str:
    """Return a human-readable label for an HTTP status code."""
    if status is None:
        return "MISSING"
    if 200 <= status < 300:
        return f"OK {status}"
    if 300 <= status < 400:
        return f"REDIRECT {status}"
    if 400 <= status < 500:
        return f"CLIENT ERROR {status}"
    if 500 <= status < 600:
        return f"SERVER ERROR {status}"
    return f"HTTP {status}"


def load_sitemap(base_dir: Path) -> str:
    """Load the sitemap XML from disk.

    Looks for sitemap.xml in the website output directory. Returns the
    raw XML content as a string.

    Raises:
        SystemExit: If the sitemap file does not exist.
    """
    sitemap_path = base_dir / "sitemap.xml"
    if not sitemap_path.exists():
        print(f"{RED}ERROR: sitemap.xml not found at {sitemap_path}{RESET}")
        print("Run 1-scraper.py first to download the sitemap.")
        sys.exit(1)
    return sitemap_path.read_text(encoding="utf-8")


def check_page_completeness(
    entries: list[SitemapEntry],
    base_dir: Path,
) -> tuple[dict[str, tuple[Path | None, int | None]], list[str]]:
    """Match every sitemap URL to its downloaded file on disk.

    Args:
        entries: Parsed sitemap entries.
        base_dir: Website output directory.

    Returns:
        A tuple of (page_map, missing_urls).
        - page_map: Dict mapping URL -> (file_path, status_code).
        - missing_urls: List of sitemap URLs with no matching file on disk.
    """
    page_map: dict[str, tuple[Path | None, int | None]] = {}
    missing_urls: list[str] = []

    for entry in entries:
        file_path, status_code = find_page_file(base_dir, entry.loc)
        page_map[entry.loc] = (file_path, status_code)
        if file_path is None:
            missing_urls.append(entry.loc)

    return page_map, missing_urls


async def check_images(
    entries: list[SitemapEntry],
    client,
    semaphore: asyncio.Semaphore,
) -> dict[str, int]:
    """Check all sitemap image URLs via HEAD requests.

    Fetches each unique image URL in parallel and records its HTTP status.

    Args:
        entries: Parsed sitemap entries (images extracted from each).
        client: The httpx async client.
        semaphore: Concurrency limiter.

    Returns:
        Dict mapping image URL -> HTTP status code (0 for errors/timeouts).
    """
    # Collect unique image URLs
    unique_images: set[str] = set()
    for entry in entries:
        unique_images.update(entry.images)

    if not unique_images:
        return {}

    image_results: dict[str, int] = {}

    async def _check_one(url: str) -> tuple[str, int]:
        async with semaphore:
            status, _ = await fetch_head(client, url)
            return url, status

    tasks = [_check_one(url) for url in unique_images]
    results = await asyncio.gather(*tasks)

    for url, status in results:
        image_results[url] = status

    return image_results


def print_report(
    entries: list[SitemapEntry],
    page_map: dict[str, tuple[Path | None, int | None]],
    image_results: dict[str, int],
) -> None:
    """Print the full sitemap checker report with statistics.

    Outputs:
    - Per-URL details with status code, lastmod, and image info
    - Highlighted sections for errors and redirects
    - Image statistics
    - Overall summary
    """
    page_stats: Counter = Counter()
    image_stats: Counter = Counter()

    errors: list[tuple[str, int | None]] = []
    redirects: list[tuple[str, int | None]] = []
    broken_images: list[tuple[str, int]] = []

    # ── Per-URL details ──
    print()
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}SITEMAP CHECKER REPORT{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print()

    print(f"{BOLD}── Page Details ({len(entries)} URLs in sitemap) ──{RESET}")
    print()

    for entry in entries:
        _, status = page_map[entry.loc]
        color = _status_color(status)
        label = _status_label(status)

        # Count page status
        if status is not None:
            page_stats[f"{status // 100}xx"] += 1
        else:
            page_stats["missing"] += 1

        # Track problems
        if status is None or status >= 400:
            errors.append((entry.loc, status))
        elif 300 <= status < 400:
            redirects.append((entry.loc, status))

        # Build detail line
        meta_parts: list[str] = []
        if entry.lastmod:
            meta_parts.append(f"lastmod={entry.lastmod}")
        if entry.changefreq:
            meta_parts.append(f"freq={entry.changefreq}")
        if entry.priority:
            meta_parts.append(f"pri={entry.priority}")

        meta_str = f" {DIM}({', '.join(meta_parts)}){RESET}" if meta_parts else ""

        print(f"  {color}[{label}]{RESET} {entry.loc}{meta_str}")

        # Image details for this URL
        if entry.images:
            for img_url in entry.images:
                img_status = image_results.get(img_url)
                if img_status is not None:
                    img_color = _status_color(img_status)
                    img_label = _status_label(img_status)
                    print(f"    {img_color}[IMG {img_label}]{RESET} {img_url}")

                    if img_status > 0:
                        image_stats[f"{img_status // 100}xx"] += 1
                    else:
                        image_stats["errors"] += 1

                    if img_status == 0 or img_status >= 400:
                        broken_images.append((img_url, img_status))
                    elif 300 <= img_status < 400:
                        broken_images.append((img_url, img_status))

    # ── Errors section ──
    if errors:
        print()
        print(f"{BOLD}{RED}── Errors & Missing Pages ({len(errors)}) ──{RESET}")
        print()
        for url, status in errors:
            label = _status_label(status)
            print(f"  {RED}[{label}]{RESET} {url}")

    # ── Redirects section ──
    if redirects:
        print()
        print(
            f"{BOLD}{YELLOW}── Redirects ({len(redirects)}) ──{RESET}"
        )
        print()
        for url, status in redirects:
            label = _status_label(status)
            print(f"  {YELLOW}[{label}]{RESET} {url}")

    # ── Broken images section ──
    if broken_images:
        print()
        print(
            f"{BOLD}{RED}── Broken/Redirected Images "
            f"({len(broken_images)}) ──{RESET}"
        )
        print()
        for url, status in broken_images:
            color = _status_color(status)
            label = _status_label(status)
            print(f"  {color}[{label}]{RESET} {url}")

    # ── Image statistics ──
    total_images = sum(len(e.images) for e in entries)
    unique_images = len(image_results)

    print()
    print(f"{BOLD}── Image Statistics ──{RESET}")
    print()
    if total_images == 0:
        print("  No images found in sitemap.")
    else:
        print(f"  Total image references:  {total_images}")
        print(f"  Unique image URLs:       {unique_images}")
        for key in sorted(image_stats):
            count = image_stats[key]
            color = GREEN if key == "2xx" else (YELLOW if key == "3xx" else RED)
            print(f"    {color}{key}: {count}{RESET}")

    # ── Overall summary ──
    print()
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}SUMMARY{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"  Website:          {WEBSITE_URL}")
    print(f"  Sitemap URLs:     {len(entries)}")
    print()
    print("  Page status breakdown:")
    for key in sorted(page_stats):
        count = page_stats[key]
        if key == "missing":
            color = RED
        elif key == "2xx":
            color = GREEN
        elif key == "3xx":
            color = YELLOW
        else:
            color = RED
        print(f"    {color}{key}: {count}{RESET}")
    print()

    ok_count = page_stats.get("2xx", 0)
    problem_count = len(entries) - ok_count
    if problem_count == 0:
        print(f"  {GREEN}{BOLD}All {len(entries)} sitemap pages are OK (2xx).{RESET}")
    else:
        print(
            f"  {YELLOW}{ok_count}/{len(entries)} pages OK, "
            f"{problem_count} with issues.{RESET}"
        )

    if total_images > 0:
        ok_images = image_stats.get("2xx", 0)
        if ok_images == unique_images:
            print(
                f"  {GREEN}{BOLD}All {unique_images} sitemap images "
                f"are OK (2xx).{RESET}"
            )
        else:
            print(
                f"  {YELLOW}{ok_images}/{unique_images} images OK, "
                f"{unique_images - ok_images} with issues.{RESET}"
            )

    print(f"{BOLD}{'=' * 70}{RESET}")


async def main() -> None:
    """Main sitemap checker entrypoint."""
    website_id = get_website_id(WEBSITE_URL)
    base_dir = OUTPUT_DIR / website_id

    print(f"{BOLD}Sitemap Checker{RESET}")
    print(f"  Website: {WEBSITE_URL}")
    print(f"  Data:    {base_dir.resolve()}")
    print()

    # ── Step 1: Load and parse sitemap ──
    print("── Loading sitemap ──")
    xml_content = load_sitemap(base_dir)
    entries, sub_sitemaps = parse_sitemap_detailed(xml_content)

    if sub_sitemaps:
        print(
            f"  {YELLOW}WARNING: Sitemap index found with "
            f"{len(sub_sitemaps)} sub-sitemaps.{RESET}"
        )
        print("  Only the root sitemap entries are checked in this version.")

    print(f"  Found {len(entries)} URLs in sitemap")
    total_images = sum(len(e.images) for e in entries)
    print(f"  Found {total_images} image references in sitemap")

    if not entries:
        print(f"{RED}ERROR: No URLs found in sitemap. Nothing to check.{RESET}")
        sys.exit(1)

    # ── Step 2: Check page completeness ──
    print()
    print("── Checking downloaded pages ──")
    page_map, missing_urls = check_page_completeness(entries, base_dir)

    found_count = len(entries) - len(missing_urls)
    print(f"  {found_count}/{len(entries)} pages found on disk")

    if missing_urls:
        print()
        print(
            f"{RED}{BOLD}ERROR: {len(missing_urls)} sitemap URL(s) "
            f"were NOT downloaded!{RESET}"
        )
        print(f"{RED}Run 1-scraper.py first to download all pages.{RESET}")
        print()
        for url in missing_urls:
            print(f"  {RED}MISSING: {url}{RESET}")
        print()
        print(f"{RED}Exiting. Fix missing pages before running the checker.{RESET}")
        sys.exit(1)

    print(f"  {GREEN}All sitemap pages are downloaded.{RESET}")

    # ── Step 3: Check image URLs ──
    image_results: dict[str, int] = {}
    if total_images > 0:
        print()
        print(f"── Checking {total_images} sitemap image URLs ──")

        client = get_session(HTTP_AUTH_USERNAME, HTTP_AUTH_PASSWORD)
        semaphore = asyncio.Semaphore(PARALLELISM)

        async with client:
            image_results = await check_images(entries, client, semaphore)

        ok_images = sum(1 for s in image_results.values() if 200 <= s < 300)
        print(f"  Checked {len(image_results)} unique images: {ok_images} OK")

    # ── Step 4: Print report ──
    print_report(entries, page_map, image_results)


if __name__ == "__main__":
    asyncio.run(main())
