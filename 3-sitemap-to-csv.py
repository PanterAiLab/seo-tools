"""Sitemap to CSV: extracts all URLs from a sitemap.xml into a plain CSV list.

Reads a sitemap XML (from a URL or local file), parses all <loc> entries,
and writes them to a CSV file -- one URL per row, no headers, single column.
Supports sitemap index files by recursively fetching sub-sitemaps.
"""

import asyncio
import csv
import sys
from pathlib import Path

from utils_html import parse_sitemap
from utils_requests import fetch_page, get_session

# ──────────────────────────────────────────────
# CONFIGURATION - edit these values before running
# ──────────────────────────────────────────────

SITEMAP_SOURCE = "https://aipornrank.com/sitemap.xml"
OUTPUT_FILE = "sitemap-urls.csv"

HTTP_AUTH_USERNAME = ""
HTTP_AUTH_PASSWORD = ""

PARALLELISM = 10

# ──────────────────────────────────────────────

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def load_sitemap_from_file(path: str) -> str:
    """Load sitemap XML content from a local file.

    Args:
        path: Path to the sitemap XML file on disk.

    Returns:
        The raw XML content as a string.

    Raises:
        SystemExit: If the file does not exist.
    """
    file_path = Path(path)
    if not file_path.exists():
        print(f"{RED}ERROR: File not found: {file_path}{RESET}")
        sys.exit(1)
    return file_path.read_text(encoding="utf-8")


async def load_sitemap_from_url(
    client,
    url: str,
) -> str:
    """Fetch sitemap XML content from a remote URL.

    Args:
        client: The httpx async client.
        url: The sitemap URL to fetch.

    Returns:
        The raw XML content as a string.

    Raises:
        SystemExit: If the request fails or returns a non-2xx status.
    """
    status, _, body = await fetch_page(client, url)
    if status == 0 or status >= 400:
        print(f"{RED}ERROR: Failed to fetch {url} (HTTP {status}){RESET}")
        sys.exit(1)
    return body


async def collect_all_urls(
    source: str,
    client,
    semaphore: asyncio.Semaphore,
) -> list[str]:
    """Parse a sitemap source and collect all page URLs.

    If the sitemap is an index, recursively fetches and parses each
    sub-sitemap to collect all page URLs.

    Args:
        source: URL or local file path of the root sitemap.
        client: The httpx async client (used for remote fetches).
        semaphore: Concurrency limiter for sub-sitemap fetches.

    Returns:
        A flat list of all page URLs found across all sitemaps.
    """
    # Load root sitemap
    if source.startswith("http://") or source.startswith("https://"):
        xml_content = await load_sitemap_from_url(client, source)
    else:
        xml_content = load_sitemap_from_file(source)

    page_urls, sub_sitemap_urls = parse_sitemap(xml_content)
    all_urls: list[str] = list(page_urls)

    if sub_sitemap_urls:
        print(
            f"  {YELLOW}Sitemap index detected with "
            f"{len(sub_sitemap_urls)} sub-sitemaps.{RESET}"
        )

        async def _fetch_sub(url: str) -> list[str]:
            async with semaphore:
                print(f"  {DIM}Fetching {url}{RESET}")
                sub_xml = await load_sitemap_from_url(client, url)
                sub_pages, _ = parse_sitemap(sub_xml)
                return sub_pages

        tasks = [_fetch_sub(url) for url in sub_sitemap_urls]
        results = await asyncio.gather(*tasks)

        for sub_pages in results:
            all_urls.extend(sub_pages)

    return all_urls


def write_csv(urls: list[str], output_path: str) -> None:
    """Write a list of URLs to a CSV file, one per row.

    No header row, no footer, single column only.

    Args:
        urls: List of URL strings to write.
        output_path: Destination file path for the CSV.
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for url in urls:
            writer.writerow([url])


async def main() -> None:
    """Main entrypoint: parse sitemap and write URLs to CSV."""
    print(f"{BOLD}Sitemap to CSV{RESET}")
    print(f"  Source: {SITEMAP_SOURCE}")
    print(f"  Output: {OUTPUT_FILE}")
    print()

    client = get_session(HTTP_AUTH_USERNAME, HTTP_AUTH_PASSWORD)
    semaphore = asyncio.Semaphore(PARALLELISM)

    async with client:
        all_urls = await collect_all_urls(SITEMAP_SOURCE, client, semaphore)

    if not all_urls:
        print(f"{RED}ERROR: No URLs found in sitemap. Nothing to write.{RESET}")
        sys.exit(1)

    write_csv(all_urls, OUTPUT_FILE)

    print(f"{GREEN}{BOLD}Done!{RESET} {len(all_urls)} URLs written to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
