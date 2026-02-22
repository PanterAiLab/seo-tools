"""Wayback Machine Scraper: downloads historical snapshots from web.archive.org.

Fetches the CDX index for a website, filters snapshots by frequency (daily,
weekly, monthly), and downloads the HTML for each selected snapshot.
Supports resumability across runs.
"""

import asyncio
import json
from collections import Counter
from pathlib import Path

import httpx

from utils_files import (
    get_archive_folder_id,
    get_snapshot_path,
    load_existing_snapshots,
    save_raw_file,
)
from utils_html import prettify_html
from utils_wayback import (
    FrequencyType,
    WaybackSnapshot,
    fetch_cdx_snapshots,
    fetch_snapshot_html,
    filter_snapshots_by_frequency,
)

# ──────────────────────────────────────────────
# CONFIGURATION - edit these values before running
# ──────────────────────────────────────────────

WEBSITE_URL = "https://snaptik.app"
FREQUENCY: FrequencyType = "monthly"
PARALLELISM = 5

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


async def download_snapshots_batch(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    snapshots: list[WaybackSnapshot],
    base_dir: Path,
    stats: Counter,
) -> None:
    """Download a batch of snapshots in parallel.

    Args:
        client: The httpx async client.
        semaphore: Concurrency limiter.
        snapshots: List of snapshots to download.
        base_dir: Output directory for saved HTML files.
        stats: Counter for tracking download statistics.
    """

    async def fetch_one(snapshot: WaybackSnapshot) -> tuple[WaybackSnapshot, str | None, str | None]:
        async with semaphore:
            return await fetch_snapshot_html(snapshot, client)

    tasks = [fetch_one(s) for s in snapshots]
    results = await asyncio.gather(*tasks)

    for snapshot, html, error in results:
        if error:
            stats["errors"] += 1
            print(f"  {RED}[ERROR]{RESET} {snapshot.timestamp} - {error}")
            continue

        # Prettify HTML before saving
        prettified = prettify_html(html)

        file_path = get_snapshot_path(base_dir, snapshot.timestamp)
        file_path.write_text(prettified, encoding="utf-8")
        stats["downloaded"] += 1

        date_str = snapshot.datetime.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {GREEN}[OK]{RESET} {date_str} -> {file_path.name}")


async def main() -> None:
    """Main Wayback Machine scraper entrypoint."""
    archive_id = get_archive_folder_id(WEBSITE_URL)
    base_dir = OUTPUT_DIR / archive_id
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"{BOLD}Wayback Machine Scraper{RESET}")
    print(f"  Website:   {WEBSITE_URL}")
    print(f"  Frequency: {FREQUENCY}")
    print(f"  Output:    {base_dir.resolve()}")
    print()

    # ── Step 1: Load already-downloaded snapshots ──
    existing_timestamps = load_existing_snapshots(base_dir)
    if existing_timestamps:
        print(f"Found {len(existing_timestamps)} snapshots from previous runs.")
        print()

    # ── Step 2: Fetch CDX index ──
    print("── Fetching CDX index from Wayback Machine ──")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            all_snapshots = await fetch_cdx_snapshots(WEBSITE_URL, client)
        except httpx.HTTPError as exc:
            print(f"{RED}ERROR: Failed to fetch CDX index: {exc}{RESET}")
            return

    if not all_snapshots:
        print(f"{YELLOW}No snapshots found for {WEBSITE_URL}{RESET}")
        return

    print(f"  Found {len(all_snapshots)} total snapshots")

    # Save CDX index for reference
    cdx_data = [
        {
            "timestamp": s.timestamp,
            "original_url": s.original_url,
            "status_code": s.status_code,
            "digest": s.digest,
        }
        for s in all_snapshots
    ]
    save_raw_file(base_dir, "cdx_index.json", json.dumps(cdx_data, indent=2))
    print(f"  Saved CDX index to cdx_index.json")

    # Date range
    first_date = all_snapshots[0].datetime.strftime("%Y-%m-%d")
    last_date = all_snapshots[-1].datetime.strftime("%Y-%m-%d")
    print(f"  Date range: {first_date} to {last_date}")

    # ── Step 3: Filter by frequency ──
    print()
    print(f"── Filtering to {FREQUENCY} frequency ──")
    filtered_snapshots = filter_snapshots_by_frequency(all_snapshots, FREQUENCY)
    print(f"  Selected {len(filtered_snapshots)} snapshots ({FREQUENCY})")

    # ── Step 4: Filter out already-downloaded ──
    to_download = [
        s for s in filtered_snapshots if s.timestamp not in existing_timestamps
    ]

    if not to_download:
        print()
        print(f"{GREEN}All {len(filtered_snapshots)} snapshots already downloaded.{RESET}")
        return

    print(f"  {len(to_download)} new snapshots to download")

    # ── Step 5: Download snapshots ──
    print()
    print("── Downloading snapshots ──")

    stats: Counter = Counter()
    semaphore = asyncio.Semaphore(PARALLELISM)

    async with httpx.AsyncClient(timeout=60.0) as client:
        await download_snapshots_batch(client, semaphore, to_download, base_dir, stats)

    # ── Step 6: Print statistics ──
    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}WAYBACK SCRAPER COMPLETE{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"  Website:            {WEBSITE_URL}")
    print(f"  Frequency:          {FREQUENCY}")
    print(f"  Output directory:   {base_dir.resolve()}")
    print()
    print(f"  Total snapshots:    {len(all_snapshots)}")
    print(f"  Filtered ({FREQUENCY}): {len(filtered_snapshots)}")
    print(f"  Previously saved:   {len(existing_timestamps)}")
    print(f"  Downloaded now:     {stats['downloaded']}")
    print(f"  Errors:             {stats['errors']}")
    print()

    total_on_disk = len(existing_timestamps) + stats["downloaded"]
    if stats["errors"] == 0:
        print(f"  {GREEN}{BOLD}All snapshots downloaded successfully.{RESET}")
    else:
        print(
            f"  {YELLOW}{stats['downloaded']}/{len(to_download)} snapshots "
            f"downloaded, {stats['errors']} errors.{RESET}"
        )
    print(f"  Total on disk: {total_on_disk} snapshots")
    print(f"{BOLD}{'=' * 60}{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
