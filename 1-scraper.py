"""SEO Scraper: crawls a website via sitemap + internal link discovery.

Downloads pages to disk following the Page ID naming convention,
supports HTTP auth, parallelization, and resumability across runs.
"""

import asyncio
from collections import Counter
from pathlib import Path

from utils_files import (
    get_website_id,
    load_existing_pages,
    save_page,
    save_raw_file,
    url_to_path_key,
)
from utils_html import (
    detect_external_page,
    extract_internal_links,
    is_same_domain,
    parse_sitemap,
)
from utils_requests import fetch_page, get_session

# ──────────────────────────────────────────────
# CONFIGURATION - edit these values before running
# ──────────────────────────────────────────────

WEBSITE_URL = "https://aipornrank.com"
MAX_PAGES = 1000
PARALLELISM = 20

HTTP_AUTH_USERNAME = ""
HTTP_AUTH_PASSWORD = ""

# ──────────────────────────────────────────────

OUTPUT_DIR = Path("scraped")


async def fetch_with_semaphore(
    semaphore: asyncio.Semaphore,
    client,
    url: str,
) -> tuple[str, int, str, str]:
    """Fetch a page while respecting the concurrency semaphore.

    Returns:
        A tuple of (original_url, status_code, redirect_url, body).
    """
    async with semaphore:
        status, redirect_url, body = await fetch_page(client, url)
        return (url, status, redirect_url, body)


async def download_batch(
    client,
    semaphore: asyncio.Semaphore,
    urls: list[str],
    base_dir: Path,
    stats: Counter,
    site_url: str,
    visited_keys: set[str],
) -> tuple[list[tuple[str, int, str]], list[str]]:
    """Download a batch of URLs in parallel with redirect handling.

    Saves each page to disk with its true HTTP status code. For 3xx
    redirects, checks whether the target is internal or external.
    For 2xx responses, checks the canonical URL for external signals.

    Args:
        client: The httpx async client.
        semaphore: Concurrency limiter.
        urls: URLs to download.
        base_dir: Output directory for saved pages.
        stats: Counter for session statistics.
        site_url: Root website URL for domain comparison.
        visited_keys: Set of already-visited path keys (for redirect targets).

    Returns:
        A tuple of:
        - downloaded: List of (url, status_code, body) for pages suitable
          for link extraction (2xx same-domain, non-external-canonical).
        - redirect_targets: List of internal redirect target URLs that
          should be fetched in subsequent batches.
    """
    tasks = [fetch_with_semaphore(semaphore, client, url) for url in urls]
    results = await asyncio.gather(*tasks)

    downloaded: list[tuple[str, int, str]] = []
    redirect_targets: list[str] = []

    for original_url, status, redirect_url, body in results:
        if status == 0:
            stats["errors"] += 1
            continue

        # Save every page with its true status code
        save_page(base_dir, original_url, status, body)
        stats[f"{status // 100}xx"] += 1
        stats["total"] += 1

        # ── Handle 3xx redirects ──
        if 300 <= status < 400:
            if redirect_url and is_same_domain(redirect_url, site_url):
                # Internal redirect: queue the target for fetching
                key = url_to_path_key(redirect_url)
                if key not in visited_keys:
                    visited_keys.add(key)
                    redirect_targets.append(redirect_url)
                stats["internal_redirects"] += 1
                print(f"  [REDIRECT {status}] {original_url} -> {redirect_url}")
            elif redirect_url:
                # External redirect: log and skip
                stats["external_redirects"] += 1
                print(
                    f"  [EXTERNAL REDIRECT {status}] {original_url} "
                    f"-> {redirect_url}"
                )
            else:
                print(f"  [REDIRECT {status}] {original_url} (no Location header)")
            continue

        # ── Handle 2xx responses ──
        if 200 <= status < 300:
            # Check canonical URL for external domain
            is_external, reason = detect_external_page(body, site_url)
            if is_external:
                stats["external_canonicals"] += 1
                print(f"  [EXTERNAL CANONICAL] {original_url} ({reason})")
                # Saved to disk but excluded from link extraction
                continue

            print(f"  [OK {status}] {original_url}")
            downloaded.append((original_url, status, body))
            continue

        # ── Handle 4xx/5xx ──
        print(f"  [HTTP {status}] {original_url}")

    return downloaded, redirect_targets


async def fetch_sitemap_urls(
    client,
    semaphore: asyncio.Semaphore,
    sitemap_url: str,
    base_dir: Path,
) -> list[str]:
    """Fetch and parse the sitemap, recursively handling sitemap indexes.

    Sitemaps themselves may be behind redirects, so we follow them manually.
    Saves each sitemap XML file to the output directory.
    Returns a flat list of all page URLs discovered across all sitemaps.
    """
    all_page_urls: list[str] = []
    sitemaps_to_fetch = [sitemap_url]
    fetched_sitemaps: set[str] = set()

    while sitemaps_to_fetch:
        current_url = sitemaps_to_fetch.pop(0)
        if current_url in fetched_sitemaps:
            continue
        fetched_sitemaps.add(current_url)

        print(f"  Fetching sitemap: {current_url}")

        # Follow redirects manually for sitemaps (up to 5 hops)
        url_to_fetch = current_url
        for _ in range(5):
            async with semaphore:
                status, redirect_url, body = await fetch_page(client, url_to_fetch)
            if 300 <= status < 400 and redirect_url:
                print(f"    Sitemap redirect {status}: {url_to_fetch} -> {redirect_url}")
                url_to_fetch = redirect_url
                continue
            break

        if status == 0 or status >= 400:
            print(f"  [WARN] Could not fetch sitemap: {current_url} (HTTP {status})")
            continue

        # Save the sitemap XML
        sitemap_filename = current_url.split("/")[-1] or "sitemap.xml"
        save_raw_file(base_dir, sitemap_filename, body)

        page_urls, sub_sitemaps = parse_sitemap(body)
        all_page_urls.extend(page_urls)
        sitemaps_to_fetch.extend(sub_sitemaps)

        print(f"    Found {len(page_urls)} page URLs, {len(sub_sitemaps)} sub-sitemaps")

    return all_page_urls


async def main() -> None:
    """Main scraper entrypoint: orchestrates the full crawling flow."""
    website_id = get_website_id(WEBSITE_URL)
    base_dir = OUTPUT_DIR / website_id
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Scraping: {WEBSITE_URL}")
    print(f"Output:   {base_dir.resolve()}")
    print(f"Max pages: {MAX_PAGES}, Parallelism: {PARALLELISM}")
    print()

    # ── Step 1: Load already-downloaded pages ──
    existing_keys = load_existing_pages(base_dir)
    print(f"Found {len(existing_keys)} pages from previous runs.")

    # Track all visited URLs (by path key) to avoid duplicates
    visited_keys: set[str] = set(existing_keys)
    # Track URLs visited in this session (for stats)
    session_downloaded: list[tuple[str, int]] = []

    client = get_session(HTTP_AUTH_USERNAME, HTTP_AUTH_PASSWORD)
    semaphore = asyncio.Semaphore(PARALLELISM)
    stats: Counter = Counter()

    async with client:
        # ── Step 2: Fetch robots.txt ──
        # NOTE: robots.txt is downloaded and saved for reference only.
        # Its rules (Disallow, Crawl-delay, etc.) are intentionally ignored.
        print("\n── Fetching robots.txt ──")
        robots_url = WEBSITE_URL.rstrip("/") + "/robots.txt"
        # Follow redirects manually for robots.txt
        robots_fetch_url = robots_url
        for _ in range(5):
            async with semaphore:
                robots_status, robots_redirect, robots_body = await fetch_page(
                    client, robots_fetch_url
                )
            if 300 <= robots_status < 400 and robots_redirect:
                robots_fetch_url = robots_redirect
                continue
            break
        if robots_status == 200:
            save_raw_file(base_dir, "robots.txt", robots_body)
            print("  Saved robots.txt")
        else:
            print(f"  robots.txt not available (HTTP {robots_status})")

        # ── Step 3: Fetch and parse sitemap ──
        print("\n── Fetching sitemap ──")
        sitemap_url = WEBSITE_URL.rstrip("/") + "/sitemap.xml"
        sitemap_page_urls = await fetch_sitemap_urls(
            client, semaphore, sitemap_url, base_dir
        )
        print(f"\nTotal URLs from sitemap: {len(sitemap_page_urls)}")

        # ── Step 4: Download pages from sitemap ──
        print("\n── Downloading sitemap pages ──")
        urls_to_fetch = []
        for url in sitemap_page_urls:
            key = url_to_path_key(url)
            if key not in visited_keys and len(visited_keys) < MAX_PAGES + len(existing_keys):
                visited_keys.add(key)
                urls_to_fetch.append(url)

        all_bodies: list[tuple[str, str]] = []

        if urls_to_fetch:
            print(f"  {len(urls_to_fetch)} new pages to download from sitemap")
            results, redirect_targets = await download_batch(
                client, semaphore, urls_to_fetch, base_dir, stats,
                WEBSITE_URL, visited_keys,
            )
            session_downloaded.extend((url, status) for url, status, _ in results)
            all_bodies = [(url, body) for url, _, body in results]

            # Follow internal redirects discovered during sitemap download
            while redirect_targets:
                print(f"  Following {len(redirect_targets)} internal redirects...")
                results, redirect_targets = await download_batch(
                    client, semaphore, redirect_targets, base_dir, stats,
                    WEBSITE_URL, visited_keys,
                )
                session_downloaded.extend((url, status) for url, status, _ in results)
                all_bodies.extend((url, body) for url, _, body in results)
        else:
            print("  No new pages from sitemap.")

        # ── Step 5: Internal link discovery loop ──
        print("\n── Discovering internal links ──")
        iteration = 0
        pages_remaining = MAX_PAGES + len(existing_keys) - len(visited_keys)

        while pages_remaining > 0:
            iteration += 1
            # Extract internal links from all newly downloaded pages
            new_urls: list[str] = []
            for page_url, body in all_bodies:
                links = extract_internal_links(body, page_url, WEBSITE_URL)
                for link in links:
                    key = url_to_path_key(link)
                    if key not in visited_keys:
                        visited_keys.add(key)
                        new_urls.append(link)

            # Cap to remaining budget
            if len(new_urls) > pages_remaining:
                new_urls = new_urls[:pages_remaining]

            if not new_urls:
                print(f"  Iteration {iteration}: no new internal links found. Done.")
                break

            print(f"  Iteration {iteration}: found {len(new_urls)} new internal links")
            results, redirect_targets = await download_batch(
                client, semaphore, new_urls, base_dir, stats,
                WEBSITE_URL, visited_keys,
            )
            session_downloaded.extend((url, status) for url, status, _ in results)

            # Prepare bodies for next iteration's link extraction
            all_bodies = [(url, body) for url, _, body in results]

            # Follow internal redirects discovered in this batch
            while redirect_targets:
                print(f"  Following {len(redirect_targets)} internal redirects...")
                results, redirect_targets = await download_batch(
                    client, semaphore, redirect_targets, base_dir, stats,
                    WEBSITE_URL, visited_keys,
                )
                session_downloaded.extend((url, status) for url, status, _ in results)
                all_bodies.extend((url, body) for url, _, body in results)

            pages_remaining = MAX_PAGES + len(existing_keys) - len(visited_keys)

    # ── Step 6: Print session stats ──
    print("\n" + "=" * 60)
    print("SCRAPING SESSION COMPLETE")
    print("=" * 60)
    print(f"  Website:            {WEBSITE_URL}")
    print(f"  Output directory:   {base_dir.resolve()}")
    print(f"  Previously saved:   {len(existing_keys)} pages")
    print(f"  Downloaded now:     {stats['total']} pages")
    print(f"  Errors/timeouts:    {stats['errors']}")
    print(f"  Internal redirects: {stats['internal_redirects']}")
    print(f"  External redirects: {stats['external_redirects']}")
    print(f"  External canonicals:{stats['external_canonicals']}")
    print(f"  Total on disk:      {len(existing_keys) + stats['total']} pages")
    print()
    print("  Status code breakdown (this session):")
    for key in sorted(stats):
        if key.endswith("xx"):
            print(f"    {key}: {stats[key]}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
