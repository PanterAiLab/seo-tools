"""Utility functions for extracting SEO elements from HTML pages."""

import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models_seo import (
    CanonicalInfo,
    HeadingInfo,
    HeadingItem,
    HeadingsHierarchy,
    MetaInfo,
    OpenGraphInfo,
    RobotsInfo,
    SchemaInfo,
    TitleInfo,
    TwitterCardInfo,
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


def extract_headings(soup: BeautifulSoup) -> HeadingsHierarchy:
    """Extract all headings and validate hierarchy for SEO issues.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        HeadingsHierarchy with all headings and any hierarchy issues.
    """
    issues: list[str] = []
    headings: list[HeadingItem] = []

    heading_tags = soup.find_all(["h1", "h2", "h3", "h4"])

    for tag in heading_tags:
        tag_name = tag.name
        level = int(tag_name[1])
        text = tag.get_text(strip=True)
        headings.append(HeadingItem(tag=tag_name, text=text, level=level))

    # Validate hierarchy: check for skipped levels
    prev_level = 0
    for heading in headings:
        current_level = heading.level
        # Only check for skipped levels going down (increasing level numbers)
        if current_level > prev_level + 1 and prev_level > 0:
            skipped_levels = [f"h{i}" for i in range(prev_level + 1, current_level)]
            issues.append(
                f"Heading hierarchy skip: h{prev_level} -> h{current_level} "
                f"(missing {', '.join(skipped_levels)})"
            )
        prev_level = current_level

    return HeadingsHierarchy(headings=headings, issues=issues)


def extract_open_graph(soup: BeautifulSoup) -> OpenGraphInfo:
    """Extract Open Graph meta tags for social sharing.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        OpenGraphInfo with extracted OG properties.
    """
    all_tags: dict[str, str] = {}

    og_tags = soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")})

    for tag in og_tags:
        prop = tag.get("property", "")
        content = tag.get("content", "")
        if isinstance(prop, list):
            prop = prop[0] if prop else ""
        if isinstance(content, list):
            content = content[0] if content else ""
        if prop and content:
            # Store without og: prefix in all_tags
            key = prop[3:] if prop.startswith("og:") else prop
            all_tags[key] = content

    return OpenGraphInfo(
        title=all_tags.get("title"),
        description=all_tags.get("description"),
        image=all_tags.get("image"),
        url=all_tags.get("url"),
        type=all_tags.get("type"),
        all_tags=all_tags,
    )


def extract_twitter_card(soup: BeautifulSoup) -> TwitterCardInfo:
    """Extract Twitter Card meta tags for social sharing.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        TwitterCardInfo with extracted Twitter Card properties.
    """
    all_tags: dict[str, str] = {}

    # Twitter cards can use either name or property attribute
    twitter_tags_name = soup.find_all(
        "meta", attrs={"name": lambda x: x and x.startswith("twitter:")}
    )
    twitter_tags_property = soup.find_all(
        "meta", attrs={"property": lambda x: x and x.startswith("twitter:")}
    )

    for tag in twitter_tags_name + twitter_tags_property:
        # Get the attribute that contains the twitter: prefix
        attr_name = tag.get("name") or tag.get("property") or ""
        content = tag.get("content", "")
        if isinstance(attr_name, list):
            attr_name = attr_name[0] if attr_name else ""
        if isinstance(content, list):
            content = content[0] if content else ""
        if attr_name and content:
            # Store without twitter: prefix in all_tags
            key = attr_name[8:] if attr_name.startswith("twitter:") else attr_name
            all_tags[key] = content

    return TwitterCardInfo(
        card=all_tags.get("card"),
        title=all_tags.get("title"),
        description=all_tags.get("description"),
        image=all_tags.get("image"),
        all_tags=all_tags,
    )


def extract_structured_data(soup: BeautifulSoup) -> list[SchemaInfo]:
    """Extract JSON-LD structured data from the page.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        List of SchemaInfo with type and raw data for each JSON-LD block.
    """
    schemas: list[SchemaInfo] = []

    ld_json_tags = soup.find_all("script", attrs={"type": "application/ld+json"})

    for tag in ld_json_tags:
        content = tag.string
        if not content:
            continue

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue

        # Handle both single objects and arrays of objects
        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            schema_type = item.get("@type", "Unknown")
            # Handle array of types (e.g., ["Product", "ItemList"])
            if isinstance(schema_type, list):
                schema_type = ", ".join(schema_type)

            schemas.append(SchemaInfo(type=schema_type, raw=item))

    return schemas
