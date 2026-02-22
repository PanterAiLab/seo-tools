"""Utility functions for extracting and verifying links and images from HTML."""

import asyncio
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from models_seo import ImageInfo, LinkInfo
from utils_files import find_page_file
from utils_html import is_same_domain
from utils_requests import fetch_head


# Image format extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg"}


def extract_links(
    soup: BeautifulSoup,
    base_url: str,
    site_url: str,
) -> tuple[list[LinkInfo], list[LinkInfo]]:
    """Extract all links from HTML and classify as internal or external.

    Finds all <a href="..."> tags, resolves relative URLs to absolute,
    and splits them into internal (same domain) and external lists.

    Args:
        soup: Parsed BeautifulSoup object of the page.
        base_url: The page URL (used for resolving relative links).
        site_url: The root website URL (used for domain comparison).

    Returns:
        A tuple of (internal_links, external_links) as lists of LinkInfo.
    """
    internal_links: list[LinkInfo] = []
    external_links: list[LinkInfo] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        # Skip empty, fragment-only, and special protocol hrefs
        if not href:
            continue
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Resolve to absolute URL
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        # Only keep http/https links
        if parsed.scheme not in ("http", "https"):
            continue

        # Extract anchor text (strip whitespace, normalize)
        anchor_text = anchor.get_text(strip=True)

        # Extract rel attributes
        rel_attr = anchor.get("rel", [])
        if isinstance(rel_attr, str):
            rel_list = rel_attr.split()
        else:
            rel_list = list(rel_attr)

        link_info = LinkInfo(
            href=absolute_url,
            anchor=anchor_text,
            rel=rel_list,
        )

        if is_same_domain(absolute_url, site_url):
            link_info.is_internal = True
            internal_links.append(link_info)
        else:
            link_info.is_internal = False
            external_links.append(link_info)

    return internal_links, external_links


def extract_images(soup: BeautifulSoup, base_url: str) -> list[ImageInfo]:
    """Extract all images from HTML with metadata.

    Finds all <img> tags and extracts src, alt text, lazy loading info,
    format, and dimensions.

    Args:
        soup: Parsed BeautifulSoup object of the page.
        base_url: The page URL (used for resolving relative src URLs).

    Returns:
        A list of ImageInfo objects with issues flagged.
    """
    images: list[ImageInfo] = []

    for img in soup.find_all("img"):
        # Get src (could be in src or data-src for lazy loading)
        src = img.get("src", "")
        if isinstance(src, list):
            src = src[0] if src else ""
        src = src.strip()

        # If no src, try data-src
        data_src = img.get("data-src", "")
        if isinstance(data_src, list):
            data_src = data_src[0] if data_src else ""
        data_src = data_src.strip()

        # Use data-src as fallback if src is empty or a placeholder
        effective_src = src
        if not effective_src or effective_src.startswith("data:"):
            effective_src = data_src

        # Skip if no usable src
        if not effective_src:
            continue

        # Resolve to absolute URL
        absolute_src = urljoin(base_url, effective_src)

        # Get alt text
        alt = img.get("alt")
        if isinstance(alt, list):
            alt = alt[0] if alt else None

        # Check for lazy loading
        has_lazy = False
        loading_attr = img.get("loading", "")
        if isinstance(loading_attr, list):
            loading_attr = loading_attr[0] if loading_attr else ""
        if loading_attr.lower() == "lazy":
            has_lazy = True
        if img.get("data-src") or img.get("data-lazy"):
            has_lazy = True

        # Detect format from URL extension
        img_format = _detect_image_format(absolute_src)

        # Extract width and height
        width = _parse_dimension(img.get("width"))
        height = _parse_dimension(img.get("height"))

        # Check for issues
        issues: list[str] = []
        if alt is None:
            issues.append("Missing alt text")
        elif alt == "":
            issues.append("Empty alt text")

        images.append(
            ImageInfo(
                src=absolute_src,
                alt=alt,
                has_lazy=has_lazy,
                format=img_format,
                width=width,
                height=height,
                issues=issues,
            )
        )

    return images


def _detect_image_format(url: str) -> str | None:
    """Detect image format from URL extension.

    Args:
        url: The image URL.

    Returns:
        Format string (jpg, png, gif, webp, avif, svg) or None if unknown.
    """
    parsed = urlparse(url)
    path = parsed.path.lower()

    for ext in IMAGE_EXTENSIONS:
        if path.endswith(ext):
            # Normalize jpeg to jpg
            fmt = ext.lstrip(".")
            return "jpg" if fmt == "jpeg" else fmt

    return None


def _parse_dimension(value: str | list | None) -> int | None:
    """Parse a width/height attribute value to int.

    Args:
        value: The attribute value (could be string, list, or None).

    Returns:
        Integer value or None if parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None

    # Strip any units (e.g., "100px" -> "100")
    value = str(value).strip().lower()
    value = value.rstrip("px").rstrip("%").strip()

    try:
        return int(value)
    except ValueError:
        return None


def lookup_internal_link_status(
    href: str,
    site_url: str,
    scraped_dir: Path,
) -> int | None:
    """Look up the HTTP status code for an internal link from scraped files.

    Uses find_page_file to locate the downloaded HTML file and extract
    the status code from its filename.

    Args:
        href: The internal link URL to look up.
        site_url: The root website URL (not used, kept for API consistency).
        scraped_dir: Path to the scraped website directory.

    Returns:
        The HTTP status code from the filename, or None if not found.
    """
    _, status_code = find_page_file(scraped_dir, href)
    return status_code


async def verify_external_links(
    links: list[LinkInfo],
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> list[LinkInfo]:
    """Verify external links by making HEAD requests.

    For each link, sends a HEAD request to check availability and
    updates the link.status field with the response code.

    Args:
        links: List of LinkInfo objects to verify.
        client: The httpx async client to use.
        semaphore: Semaphore for concurrency control.

    Returns:
        The same list with status fields updated.
    """

    async def check_link(link: LinkInfo) -> None:
        async with semaphore:
            status_code, _ = await fetch_head(client, link.href)
            link.status = status_code if status_code > 0 else None

    await asyncio.gather(*[check_link(link) for link in links])
    return links
