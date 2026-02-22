"""Utility functions for HTML and XML parsing."""

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, formatter


def prettify_html(html: str) -> str:
    """Prettify HTML with proper formatting, indentation, and newlines.

    Parses the HTML and outputs it with consistent formatting while
    preserving the original structure and content. Uses a minimal
    formatter to avoid altering whitespace inside text nodes.

    Args:
        html: The raw HTML content to prettify.

    Returns:
        The prettified HTML string with proper indentation and newlines.
    """
    soup = BeautifulSoup(html, "lxml")
    fmt = formatter.HTMLFormatter(indent=2)
    return soup.prettify(formatter=fmt)


@dataclass
class SitemapEntry:
    """A single <url> entry from a sitemap XML with full metadata.

    Attributes:
        loc: The page URL from <loc>.
        lastmod: Last modification date from <lastmod>, or None.
        changefreq: Change frequency from <changefreq>, or None.
        priority: Priority value from <priority>, or None.
        images: List of image URLs from <image:image> > <image:loc>.
    """

    loc: str
    lastmod: str | None = None
    changefreq: str | None = None
    priority: str | None = None
    images: list[str] = field(default_factory=list)


def is_same_domain(url: str, site_url: str) -> bool:
    """Check if a URL belongs to the same domain as the site URL.

    Args:
        url: The URL to check.
        site_url: The root website URL to compare against.

    Returns:
        True if both URLs share the same hostname.
    """
    parsed = urlparse(url)
    site_parsed = urlparse(site_url)
    return (parsed.hostname or "") == (site_parsed.hostname or "")


def detect_external_page(body: str, site_url: str) -> tuple[bool, str]:
    """Check if a page's canonical URL points to an external domain.

    Looks for <link rel="canonical" href="..."> in the HTML. If the
    canonical URL's domain differs from site_url, the page is considered
    external.

    Args:
        body: The raw HTML content of the page.
        site_url: The root website URL to compare against.

    Returns:
        A tuple of (is_external, reason).
        - is_external: True if the canonical points to a different domain.
        - reason: Description string, e.g. "canonical: https://other.com/page".
          Empty string if not external.
    """
    try:
        soup = BeautifulSoup(body, "lxml")
        canonical_tag = soup.find("link", rel="canonical")
        if canonical_tag and canonical_tag.get("href"):
            canonical_url = canonical_tag["href"].strip()
            if canonical_url and not is_same_domain(canonical_url, site_url):
                return (True, f"canonical: {canonical_url}")
    except Exception:
        pass
    return (False, "")


def extract_internal_links(html: str, base_url: str, site_url: str) -> set[str]:
    """Extract all internal links from an HTML page.

    Parses the HTML, finds all <a href> elements, resolves relative URLs,
    filters to same-domain only (compared against the root site URL),
    and normalizes them (strips fragments and trailing slashes).

    Args:
        html: The raw HTML content of the page.
        base_url: The URL of the page (used for resolving relative links).
        site_url: The root website URL (used for domain filtering, so that
                  only links matching the site's domain are kept).

    Returns:
        A set of absolute internal URLs found on the page.
    """
    soup = BeautifulSoup(html, "lxml")
    site_parsed = urlparse(site_url)
    site_domain = site_parsed.hostname or site_parsed.netloc
    internal_links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        # Filter to same domain only (compared against root site URL)
        link_domain = parsed.hostname or parsed.netloc
        if link_domain != site_domain:
            continue

        # Only keep http/https links
        if parsed.scheme not in ("http", "https"):
            continue

        # Normalize: strip fragment, strip trailing slash, drop query params
        normalized = parsed._replace(fragment="", query="").geturl()
        normalized = normalized.rstrip("/")

        if normalized:
            internal_links.add(normalized)

    return internal_links


def parse_sitemap(xml_content: str) -> tuple[list[str], list[str]]:
    """Parse a sitemap XML and return page URLs and sub-sitemap URLs.

    Handles both <urlset> (leaf sitemap with <url><loc> entries) and
    <sitemapindex> (index pointing to sub-sitemaps via <sitemap><loc>).

    Args:
        xml_content: The raw XML content of the sitemap.

    Returns:
        A tuple of (page_urls, sub_sitemap_urls).
        - page_urls: List of page URLs found in <urlset> entries.
        - sub_sitemap_urls: List of sub-sitemap URLs found in <sitemapindex>.
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")

    page_urls: list[str] = []
    sub_sitemap_urls: list[str] = []

    # Check for sitemap index (contains links to other sitemaps)
    for sitemap_tag in soup.find_all("sitemap"):
        loc = sitemap_tag.find("loc")
        if loc and loc.text.strip():
            sub_sitemap_urls.append(loc.text.strip())

    # Check for urlset (contains actual page URLs)
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        if loc and loc.text.strip():
            page_urls.append(loc.text.strip())

    return page_urls, sub_sitemap_urls


def parse_sitemap_detailed(
    xml_content: str,
) -> tuple[list[SitemapEntry], list[str]]:
    """Parse a sitemap XML and return detailed entries with image/metadata info.

    Like parse_sitemap(), handles both <urlset> and <sitemapindex> formats.
    For each <url> entry, extracts the full metadata including <lastmod>,
    <changefreq>, <priority>, and all <image:image> > <image:loc> URLs.

    Args:
        xml_content: The raw XML content of the sitemap.

    Returns:
        A tuple of (entries, sub_sitemap_urls).
        - entries: List of SitemapEntry objects for each <url> in the sitemap.
        - sub_sitemap_urls: List of sub-sitemap URLs found in <sitemapindex>.
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")

    entries: list[SitemapEntry] = []
    sub_sitemap_urls: list[str] = []

    # Check for sitemap index (contains links to other sitemaps)
    for sitemap_tag in soup.find_all("sitemap"):
        loc = sitemap_tag.find("loc")
        if loc and loc.text.strip():
            sub_sitemap_urls.append(loc.text.strip())

    # Check for urlset (contains actual page URLs)
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        if not loc or not loc.text.strip():
            continue

        # Extract optional metadata
        lastmod_tag = url_tag.find("lastmod")
        changefreq_tag = url_tag.find("changefreq")
        priority_tag = url_tag.find("priority")

        # Extract image URLs from <image:image> > <image:loc>
        image_urls: list[str] = []
        for image_tag in url_tag.find_all("image"):
            image_loc = image_tag.find("loc")
            if image_loc and image_loc.text.strip():
                image_urls.append(image_loc.text.strip())

        entries.append(
            SitemapEntry(
                loc=loc.text.strip(),
                lastmod=lastmod_tag.text.strip() if lastmod_tag else None,
                changefreq=changefreq_tag.text.strip() if changefreq_tag else None,
                priority=priority_tag.text.strip() if priority_tag else None,
                images=image_urls,
            )
        )

    return entries, sub_sitemap_urls
