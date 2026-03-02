"""
Dataclasses for SEO page checker JSON response.

All classes are designed to be JSON-serializable via dataclasses.asdict().
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Issue:
    """Represents an SEO issue found during analysis."""

    severity: str  # "error", "warning", "info"
    category: str
    message: str


@dataclass
class TitleInfo:
    """Information about the page title tag."""

    text: str | None
    length: int
    issues: list[str] = field(default_factory=list)


@dataclass
class MetaInfo:
    """Information about a meta tag (description, keywords, etc.)."""

    text: str | None
    length: int
    issues: list[str] = field(default_factory=list)


@dataclass
class CanonicalInfo:
    """Information about the canonical URL."""

    url: str | None
    is_self: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class RobotsInfo:
    """Information about robots directives."""

    meta_robots: str | None
    x_robots_tag: str | None
    indexable: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class HeadingInfo:
    """Information about a specific heading level (H1, H2, etc.)."""

    text: str | None
    count: int
    issues: list[str] = field(default_factory=list)


@dataclass
class HeadingItem:
    """A single heading in the document hierarchy."""

    tag: str
    text: str
    level: int


@dataclass
class HeadingsHierarchy:
    """Information about the heading structure of the page."""

    headings: list[HeadingItem] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


@dataclass
class LinkInfo:
    """Information about a link on the page."""

    href: str
    anchor: str
    rel: list[str] = field(default_factory=list)
    is_internal: bool = False
    status: int | None = None
    content_type: str = "text"  # text, image, logo, icon, button, svg, mixed, empty


@dataclass
class ImageInfo:
    """Information about an image on the page."""

    src: str
    alt: str | None = None
    has_lazy: bool = False
    format: str | None = None
    width: int | None = None
    height: int | None = None
    issues: list[str] = field(default_factory=list)


@dataclass
class OpenGraphInfo:
    """Open Graph meta tag information."""

    title: str | None = None
    description: str | None = None
    image: str | None = None
    url: str | None = None
    type: str | None = None
    all_tags: dict[str, str] = field(default_factory=dict)


@dataclass
class TwitterCardInfo:
    """Twitter Card meta tag information."""

    card: str | None = None
    title: str | None = None
    description: str | None = None
    image: str | None = None
    all_tags: dict[str, str] = field(default_factory=dict)


@dataclass
class SchemaInfo:
    """JSON-LD structured data information."""

    type: str
    raw: dict[str, Any] = field(default_factory=dict)
    parsed: dict[str, Any] = field(default_factory=dict)


@dataclass
class ViewportInfo:
    """Viewport meta tag information."""

    content: str | None = None
    is_mobile_friendly: bool = False
    issues: list[str] = field(default_factory=list)


@dataclass
class HreflangInfo:
    """Hreflang tag information for internationalization."""

    lang: str
    url: str


@dataclass
class LocalizationInfo:
    """Page localization information."""

    html_lang: str | None = None
    content_language: str | None = None


@dataclass
class ScriptInfo:
    """Information about a script on the page."""

    src: str | None = None
    is_inline: bool = False
    inline_size: int | None = None
    has_async: bool = False
    has_defer: bool = False


@dataclass
class FAQInfo:
    """FAQ item information."""

    question: str
    answer: str
    has_schema: bool = False


@dataclass
class KeywordTerm:
    """A keyword term with its frequency."""

    term: str
    count: int


@dataclass
class KeywordsInfo:
    """Keyword analysis information."""

    top_terms: list[KeywordTerm] = field(default_factory=list)
    total_words: int = 0


@dataclass
class PageSEOReport:
    """
    Main SEO report for a page.

    Contains all extracted SEO information and identified issues.
    """

    file_path: str
    analyzed_at: str  # ISO timestamp

    # Core SEO elements
    title: TitleInfo | None = None
    meta_description: MetaInfo | None = None
    canonical: CanonicalInfo | None = None
    robots: RobotsInfo | None = None

    # Headings
    h1: HeadingInfo | None = None
    headings_hierarchy: HeadingsHierarchy | None = None

    # Links and images
    links: list[LinkInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)

    # Social meta tags
    open_graph: OpenGraphInfo | None = None
    twitter_card: TwitterCardInfo | None = None

    # Structured data
    schemas: list[SchemaInfo] = field(default_factory=list)

    # Mobile and viewport
    viewport: ViewportInfo | None = None

    # Internationalization
    hreflangs: list[HreflangInfo] = field(default_factory=list)
    localization: LocalizationInfo | None = None

    # Scripts
    scripts: list[ScriptInfo] = field(default_factory=list)

    # Content analysis
    faqs: list[FAQInfo] = field(default_factory=list)
    keywords: KeywordsInfo | None = None

    # Issues and scores
    issues: list[Issue] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
