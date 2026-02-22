"""Utility functions for file operations: saving, reading, and path management."""

from pathlib import Path
from urllib.parse import urlparse


def get_website_id(url: str) -> str:
    """Convert a website URL to a filesystem-safe identifier.

    Example: https://example.com -> example_com
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or parsed.netloc
    return hostname.replace(".", "_").replace("-", "_")


def get_page_path(base_dir: Path, url: str, status_code: int) -> Path:
    """Compute the on-disk file path for a page following the Page ID convention.

    Convention: <base_dir>/<nested-path-dirs>/<status_code>-<slug>.html
    Root/index page becomes <status_code>-index.html.

    Example:
        https://example.com/blog/post-1 with 200 -> base_dir/blog/200-post-1.html
        https://example.com/ with 200 -> base_dir/200-index.html
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        return base_dir / f"{status_code}-index.html"

    parts = path.split("/")
    slug = parts[-1] if parts[-1] else "index"
    directories = parts[:-1]

    filename = f"{status_code}-{slug}.html"

    if directories:
        return base_dir / Path(*directories) / filename
    return base_dir / filename


def save_page(base_dir: Path, url: str, status_code: int, content: str) -> Path:
    """Save a page's HTML content to disk using the Page ID convention.

    Creates intermediate directories as needed. Returns the path where
    the file was saved.
    """
    file_path = get_page_path(base_dir, url, status_code)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def save_raw_file(base_dir: Path, filename: str, content: str) -> Path:
    """Save a raw file (e.g. robots.txt, sitemap.xml) to the base directory."""
    file_path = base_dir / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def load_existing_pages(base_dir: Path) -> set[str]:
    """Scan an existing website folder and return the set of file stems already downloaded.

    Returns a set of strings like '200-post-1', '404-about', etc.
    These are the filenames without the .html extension, which allows
    the scraper to check if a URL's slug was already fetched regardless
    of status code changes.

    Note: We cannot perfectly reconstruct the original URLs from filenames
    (we lose the scheme, query params, etc.), so instead we return the
    relative file paths (without status prefix and extension) to use as
    a deduplication key. The scraper will use URL-based tracking for the
    current session and this set only for cross-session resumability.
    """
    existing: set[str] = set()

    if not base_dir.exists():
        return existing

    for html_file in base_dir.rglob("*.html"):
        relative = html_file.relative_to(base_dir)
        stem = relative.stem  # e.g. "200-post-1"

        # Strip the status code prefix to get just the slug
        parts = stem.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit():
            slug = parts[1]
        else:
            slug = stem

        # Reconstruct a path-like key: "blog/post-1" or "index"
        parent_parts = list(relative.parent.parts)
        if parent_parts and parent_parts != ["."]:
            key = "/".join(parent_parts) + "/" + slug
        else:
            key = slug

        existing.add(key)

    return existing


def find_page_file(base_dir: Path, url: str) -> tuple[Path | None, int | None]:
    """Find the downloaded HTML file for a URL, regardless of its HTTP status code.

    Searches the expected directory for files matching the pattern
    ``<status_code>-<slug>.html`` where the slug is derived from the URL path.

    Args:
        base_dir: Root output directory for the website (e.g. ``scraped/example_com``).
        url: The page URL to look up.

    Returns:
        A tuple of (file_path, status_code) if a matching file is found,
        or (None, None) if no file exists for this URL.
        When multiple files match (e.g. after a re-scrape changed the status),
        the first match is returned.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        slug = "index"
        search_dir = base_dir
    else:
        parts = path.split("/")
        slug = parts[-1] if parts[-1] else "index"
        directories = parts[:-1]
        search_dir = base_dir / Path(*directories) if directories else base_dir

    if not search_dir.exists():
        return (None, None)

    # Glob for any status-code prefix with this slug
    for match in search_dir.glob(f"*-{slug}.html"):
        stem = match.stem  # e.g. "200-post-1"
        prefix = stem.split("-", 1)[0]
        if prefix.isdigit():
            return (match, int(prefix))

    return (None, None)


def url_to_path_key(url: str) -> str:
    """Convert a URL to a path key matching what load_existing_pages produces.

    This enables checking if a URL was already downloaded in a previous run.

    Example:
        https://example.com/blog/post-1 -> blog/post-1
        https://example.com/ -> index
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if not path:
        return "index"

    return path


def get_archive_folder_id(url: str) -> str:
    """Convert a website URL to an archive folder identifier.

    Following the convention from IDEA.md: {WEBSITE_ID}_archive

    Example: https://example.com -> example_com_archive
    """
    return f"{get_website_id(url)}_archive"


def get_snapshot_path(base_dir: Path, timestamp: str) -> Path:
    """Compute the on-disk file path for a Wayback Machine snapshot.

    Args:
        base_dir: The archive output directory.
        timestamp: Wayback timestamp in YYYYMMDDhhmmss format.

    Returns:
        Path for the snapshot file in format YYYYMMDD-HHMMSS.html

    Example:
        timestamp "20230115120000" -> base_dir/20230115-120000.html
    """
    filename = f"{timestamp[:8]}-{timestamp[8:]}.html"
    return base_dir / filename


def load_existing_snapshots(base_dir: Path) -> set[str]:
    """Scan an archive folder and return timestamps of already downloaded snapshots.

    Returns a set of timestamps (YYYYMMDDhhmmss format) for snapshots
    that have already been downloaded, enabling resumability.

    Args:
        base_dir: The archive output directory to scan.

    Returns:
        Set of timestamp strings for existing snapshots.
    """
    existing: set[str] = set()

    if not base_dir.exists():
        return existing

    for html_file in base_dir.glob("*.html"):
        stem = html_file.stem
        if "-" in stem and len(stem) == 15:
            timestamp = stem.replace("-", "")
            existing.add(timestamp)

    return existing
