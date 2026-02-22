"""Utility functions for Wayback Machine (web.archive.org) interactions."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import httpx

CDX_API_URL = "http://web.archive.org/cdx/search/cdx"

FrequencyType = Literal["daily", "weekly", "monthly"]


@dataclass
class WaybackSnapshot:
    """A single snapshot record from the Wayback Machine CDX API.

    Attributes:
        timestamp: Wayback timestamp in YYYYMMDDhhmmss format.
        original_url: The original URL that was archived.
        status_code: HTTP status code when the snapshot was taken.
        digest: Content hash/digest for deduplication.
        datetime: Parsed datetime object from the timestamp.
    """

    timestamp: str
    original_url: str
    status_code: str
    digest: str
    datetime: datetime

    @property
    def wayback_url(self) -> str:
        """Build the Wayback Machine URL for fetching original HTML.

        Uses the 'id_' modifier to get the original HTML without
        Wayback Machine modifications (toolbar, rewritten links, etc).
        """
        return f"https://web.archive.org/web/{self.timestamp}id_/{self.original_url}"


def parse_wayback_timestamp(timestamp: str) -> datetime:
    """Parse a Wayback Machine timestamp into a datetime object.

    Wayback timestamps are in the format YYYYMMDDhhmmss (14 digits).

    Args:
        timestamp: The Wayback timestamp string (e.g., "20230115120000").

    Returns:
        A datetime object representing the timestamp.

    Raises:
        ValueError: If the timestamp format is invalid.
    """
    return datetime.strptime(timestamp, "%Y%m%d%H%M%S")


def format_snapshot_filename(timestamp: str) -> str:
    """Convert a Wayback timestamp to a filename-friendly format.

    Args:
        timestamp: The Wayback timestamp string (e.g., "20230115120000").

    Returns:
        A filename string in format "YYYYMMDD-HHMMSS.html".
    """
    return f"{timestamp[:8]}-{timestamp[8:]}.html"


async def fetch_cdx_snapshots(
    url: str,
    client: httpx.AsyncClient,
    status_filter: str = "200",
) -> list[WaybackSnapshot]:
    """Fetch all available snapshots for a URL from the Wayback Machine CDX API.

    The CDX API returns snapshot metadata including timestamps, status codes,
    and content digests. This function fetches all matching snapshots and
    parses them into WaybackSnapshot objects.

    Args:
        url: The URL to look up in the Wayback Machine (e.g., "example.com").
        client: An httpx async client for making requests.
        status_filter: Filter snapshots by HTTP status code (default "200").
                      Use empty string to get all status codes.

    Returns:
        A list of WaybackSnapshot objects sorted by timestamp (oldest first).

    Raises:
        httpx.HTTPError: If the CDX API request fails.
    """
    params: dict[str, str | int] = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original,statuscode,digest",
    }

    if status_filter:
        params["filter"] = f"statuscode:{status_filter}"

    response = await client.get(CDX_API_URL, params=params)
    response.raise_for_status()

    data = response.json()

    if not data or len(data) <= 1:
        return []

    snapshots: list[WaybackSnapshot] = []
    for row in data[1:]:
        timestamp, original, statuscode, digest = row
        snapshots.append(
            WaybackSnapshot(
                timestamp=timestamp,
                original_url=original,
                status_code=statuscode,
                digest=digest,
                datetime=parse_wayback_timestamp(timestamp),
            )
        )

    return sorted(snapshots, key=lambda s: s.datetime)


def _get_period_key(dt: datetime, frequency: FrequencyType) -> str:
    """Generate a grouping key for a datetime based on frequency.

    Args:
        dt: The datetime to generate a key for.
        frequency: The grouping frequency (daily, weekly, monthly).

    Returns:
        A string key that groups datetimes by the specified period.
    """
    if frequency == "daily":
        return dt.strftime("%Y-%m-%d")
    elif frequency == "weekly":
        return dt.strftime("%Y-W%W")
    else:
        return dt.strftime("%Y-%m")


def filter_snapshots_by_frequency(
    snapshots: list[WaybackSnapshot],
    frequency: FrequencyType,
) -> list[WaybackSnapshot]:
    """Filter snapshots to one per time period, selecting the middle point.

    Groups snapshots by the specified frequency (daily, weekly, monthly) and
    selects the snapshot closest to the middle of each period.

    Args:
        snapshots: List of WaybackSnapshot objects (should be sorted by date).
        frequency: The desired frequency - "daily", "weekly", or "monthly".

    Returns:
        A filtered list with one snapshot per period, sorted by date.
    """
    if not snapshots:
        return []

    grouped: dict[str, list[WaybackSnapshot]] = defaultdict(list)

    for snapshot in snapshots:
        key = _get_period_key(snapshot.datetime, frequency)
        grouped[key].append(snapshot)

    selected: list[WaybackSnapshot] = []

    for period_snapshots in grouped.values():
        if len(period_snapshots) == 1:
            selected.append(period_snapshots[0])
        else:
            mid_index = len(period_snapshots) // 2
            selected.append(period_snapshots[mid_index])

    return sorted(selected, key=lambda s: s.datetime)


async def fetch_snapshot_html(
    snapshot: WaybackSnapshot,
    client: httpx.AsyncClient,
) -> tuple[WaybackSnapshot, str | None, str | None]:
    """Fetch the HTML content for a Wayback Machine snapshot.

    Args:
        snapshot: The WaybackSnapshot to fetch.
        client: An httpx async client for making requests.

    Returns:
        A tuple of (snapshot, html_content, error_message).
        On success: (snapshot, html_string, None)
        On failure: (snapshot, None, error_description)
    """
    try:
        response = await client.get(snapshot.wayback_url, timeout=60.0)
        response.raise_for_status()
        return (snapshot, response.text, None)
    except httpx.TimeoutException:
        return (snapshot, None, "Request timed out")
    except httpx.HTTPStatusError as exc:
        return (snapshot, None, f"HTTP {exc.response.status_code}")
    except httpx.RequestError as exc:
        return (snapshot, None, str(exc))
