"""Utility functions for extracting SEO elements from HTML pages."""

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models_seo import (
    CanonicalInfo,
    HeadingInfo,
    MetaInfo,
    RobotsInfo,
    TitleInfo,
)


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison by removing trailing slashes and fragments.

    Args:
        url: The URL to normalize.

    Returns:
        The normalized URL string.
    """
    parsed = urlparse(url)
    # Rebuild without fragment, normalize path
    path = parsed.path.rstrip("/") or "/"
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized.lower()


def extract_title(soup: BeautifulSoup) -> TitleInfo:
    """Extract the page title tag and analyze it for SEO issues.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        TitleInfo with the title text, length, and any SEO issues.
    """
    issues: list[str] = []
    title_tag = soup.find("title")

    if not title_tag or not title_tag.string:
        return TitleInfo(text=None, length=0, issues=["Missing title tag"])

    text = title_tag.string.strip()
    length = len(text)

    if length == 0:
        issues.append("Missing title tag")
    elif length < 30:
        issues.append("Title too short (<30 chars)")
    elif length > 60:
        issues.append("Title too long (>60 chars)")

    return TitleInfo(text=text if text else None, length=length, issues=issues)


def extract_meta_description(soup: BeautifulSoup) -> MetaInfo:
    """Extract the meta description tag and analyze it for SEO issues.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        MetaInfo with the description text, length, and any SEO issues.
    """
    issues: list[str] = []
    meta_tag = soup.find("meta", attrs={"name": "description"})

    if not meta_tag:
        return MetaInfo(text=None, length=0, issues=["Missing meta description"])

    content = meta_tag.get("content", "")
    if isinstance(content, list):
        content = content[0] if content else ""
    text = content.strip()
    length = len(text)

    if length == 0:
        issues.append("Missing meta description")
    elif length < 70:
        issues.append("Meta description too short (<70 chars)")
    elif length > 160:
        issues.append("Meta description too long (>160 chars)")

    return MetaInfo(text=text if text else None, length=length, issues=issues)


def extract_canonical(soup: BeautifulSoup, page_url: str) -> CanonicalInfo:
    """Extract the canonical link tag and analyze it for SEO issues.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.
        page_url: The URL of the current page for self-referencing check.

    Returns:
        CanonicalInfo with the canonical URL, self-reference status, and any issues.
    """
    issues: list[str] = []
    canonical_tag = soup.find("link", rel="canonical")

    if not canonical_tag:
        return CanonicalInfo(url=None, is_self=False, issues=["Missing canonical tag"])

    href = canonical_tag.get("href", "")
    if isinstance(href, list):
        href = href[0] if href else ""
    url = href.strip()

    if not url:
        return CanonicalInfo(url=None, is_self=False, issues=["Missing canonical tag"])

    # Check if canonical is self-referencing
    is_self = normalize_url(url) == normalize_url(page_url)

    # Check if canonical points to a different domain
    canonical_parsed = urlparse(url)
    page_parsed = urlparse(page_url)
    canonical_domain = canonical_parsed.netloc.lower()
    page_domain = page_parsed.netloc.lower()

    if canonical_domain and page_domain and canonical_domain != page_domain:
        issues.append("Canonical points to different domain")

    return CanonicalInfo(url=url, is_self=is_self, issues=issues)


def extract_robots_meta(soup: BeautifulSoup) -> RobotsInfo:
    """Extract the robots meta tag and determine indexability.

    Note: X-Robots-Tag comes from HTTP headers, not HTML, so it's set to None.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        RobotsInfo with robots directives, indexability status, and any issues.
    """
    issues: list[str] = []
    robots_tag = soup.find("meta", attrs={"name": "robots"})

    meta_robots: str | None = None
    if robots_tag:
        content = robots_tag.get("content", "")
        if isinstance(content, list):
            content = content[0] if content else ""
        meta_robots = content.strip() if content.strip() else None

    # Determine indexability - default is True unless noindex is found
    indexable = True
    if meta_robots:
        robots_lower = meta_robots.lower()
        if "noindex" in robots_lower:
            indexable = False
            issues.append("Page is set to noindex")

    return RobotsInfo(
        meta_robots=meta_robots,
        x_robots_tag=None,  # Comes from HTTP headers, not HTML
        indexable=indexable,
        issues=issues,
    )


def extract_h1(soup: BeautifulSoup) -> HeadingInfo:
    """Extract H1 heading tags and analyze them for SEO issues.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        HeadingInfo with the first H1 text, count of all H1s, and any issues.
    """
    issues: list[str] = []
    h1_tags = soup.find_all("h1")
    count = len(h1_tags)

    if count == 0:
        return HeadingInfo(text=None, count=0, issues=["Missing H1 tag"])

    # Get text of first H1
    first_h1 = h1_tags[0]
    text = first_h1.get_text(strip=True)

    if count > 1:
        issues.append(f"Multiple H1 tags found (count: {count})")

    return HeadingInfo(text=text if text else None, count=count, issues=issues)
