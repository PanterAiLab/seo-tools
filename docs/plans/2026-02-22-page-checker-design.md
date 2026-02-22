# Page Checker (Section 3) - Design Document

**Date:** 2026-02-22  
**Status:** Approved  
**Author:** AI Assistant + Leo

## Overview

A single-page SEO analyzer that reads a local HTML file and produces a structured JSON report. The report enables cross-page comparison and covers critical SEO elements, important ranking factors, and technical checks.

## Requirements Summary

### Input
- Local HTML file path (from `scraped/` folder)
- Website root URL (for domain comparison)
- Scraped directory path (for internal link status lookup)

### Output
- JSON report saved as `{filename}_seo_report.json` (same directory as input)
- Terminal summary with colored output

### Check Categories

**1. Critical (must-have)**
- Title tag: exists, length, truncation check
- Meta description: exists, length validation
- H1: exists, only one per page
- Canonical URL: exists, self-referential check
- Indexability: meta robots, X-Robots-Tag

**2. Important (strong ranking factors)**
- Heading hierarchy: H1→H2→H3→H4 structure validation
- Internal links: href, anchor text, rel attributes, status from scraped files
- External links: href, anchor text, rel (nofollow/sponsored/ugc), live status via HEAD
- Images: src, alt text, lazy loading, format, dimensions
- Open Graph: og:title, og:description, og:image, etc.
- Twitter Cards: twitter:card, twitter:title, etc.
- Structured data: JSON-LD blocks parsed

**3. Technical (selected)**
- Viewport meta: mobile-friendly check
- Hreflang: language alternates
- Localization: html lang, content-language header hints
- Scripts: JS resources with src, inline size, async/defer attributes
- FAQ sections: FAQ schema + common HTML patterns
- Keywords: top terms by frequency from body text
- Image optimization: format detection, lazy loading presence

## Architecture

### File Structure

```
seo-tools/
├── 3-page-checker.py          # Main script - orchestration, CLI, JSON output
├── models_seo.py              # Dataclasses for JSON response structure
├── utils_seo.py               # SEO check functions (new)
├── utils_links.py             # Link extraction & verification (new)
├── utils_html.py              # Extend with new extraction helpers
└── utils_requests.py          # Existing - reuse for HEAD requests
```

### JSON Response Model (`models_seo.py`)

```python
@dataclass
class PageSEOReport:
    # Meta
    file_path: str
    analyzed_at: str  # ISO timestamp
    
    # Critical checks
    title: TitleInfo           # text, length, issues
    meta_description: MetaInfo # text, length, issues  
    canonical: CanonicalInfo   # url, is_self, issues
    robots: RobotsInfo         # meta robots, x-robots, indexable
    h1: HeadingInfo            # text, count, issues
    
    # Important checks
    headings: HeadingsHierarchy    # h1-h4 with nesting validation
    internal_links: list[LinkInfo] # href, anchor, rel, status
    external_links: list[LinkInfo] # href, anchor, rel, status, nofollow
    images: list[ImageInfo]        # src, alt, lazy, format, dimensions
    open_graph: OpenGraphInfo      # og:title, og:image, etc.
    twitter_card: TwitterCardInfo  # twitter:card, twitter:title, etc.
    structured_data: list[SchemaInfo]  # JSON-LD blocks parsed
    
    # Technical checks
    viewport: ViewportInfo         # content, mobile-friendly
    hreflang: list[HreflangInfo]   # lang, url pairs
    localization: LocalizationInfo # html lang, content-language
    scripts: list[ScriptInfo]      # src, inline size, async/defer
    faq_sections: list[FAQInfo]    # question, answer, schema present
    keywords: KeywordsInfo         # top terms by frequency
    
    # Summary
    issues: list[Issue]  # severity, category, message
    scores: dict[str, int]  # per-category scores (optional)
```

### Check Functions

**utils_seo.py** - Pure extraction functions (no I/O):

| Function | Returns | Description |
|----------|---------|-------------|
| `extract_title(soup)` | `TitleInfo` | Title tag text, length, truncation check |
| `extract_meta_description(soup)` | `MetaInfo` | Meta description, length validation |
| `extract_canonical(soup, page_url)` | `CanonicalInfo` | Canonical URL, self-referential check |
| `extract_robots_meta(soup)` | `RobotsInfo` | Meta robots + X-Robots-Tag hints |
| `extract_headings(soup)` | `HeadingsHierarchy` | H1-H4 with hierarchy validation |
| `extract_open_graph(soup)` | `OpenGraphInfo` | All og: meta tags |
| `extract_twitter_card(soup)` | `TwitterCardInfo` | All twitter: meta tags |
| `extract_structured_data(soup)` | `list[SchemaInfo]` | Parse JSON-LD blocks |
| `extract_viewport(soup)` | `ViewportInfo` | Viewport meta, mobile checks |
| `extract_hreflang(soup)` | `list[HreflangInfo]` | Language alternates |
| `extract_localization(soup)` | `LocalizationInfo` | html lang, content-language |
| `extract_scripts(soup)` | `list[ScriptInfo]` | JS resources, inline size |
| `extract_faq_sections(soup)` | `list[FAQInfo]` | FAQ schema + common FAQ patterns |
| `extract_keywords(soup)` | `KeywordsInfo` | Top terms from body text |

**utils_links.py** - Link extraction and verification:

| Function | Returns | Description |
|----------|---------|-------------|
| `extract_links(soup, base_url)` | `tuple[list[LinkInfo], list[LinkInfo]]` | Internal & external links with anchor, rel |
| `extract_images(soup, base_url)` | `list[ImageInfo]` | Images with alt, lazy, format detection |
| `lookup_internal_status(link, scraped_dir)` | `int \| None` | Check status from filename |
| `verify_external_links(links, client)` | `list[LinkInfo]` | HEAD requests for external URLs |

### Main Script Flow

```
┌─────────────────────────────────────────────────────────────┐
│  CONFIGURATION (hardcoded at top)                           │
│  - HTML_FILE_PATH: path to local HTML file                  │
│  - WEBSITE_URL: root site URL (for domain comparison)       │
│  - SCRAPED_DIR: path to scraped/ folder                     │
│  - HTTP_AUTH (optional)                                     │
│                                                             │
│  Output: derived automatically                              │
│    input:  scraped/example_com/200-blog-post.html           │
│    output: scraped/example_com/200-blog-post_seo_report.json│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. LOAD HTML                                               │
│  - Read file from disk                                      │
│  - Parse with BeautifulSoup                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. RUN ALL SEO CHECKS (sync, no I/O)                       │
│  - Call each extract_* function from utils_seo.py           │
│  - Call extract_links, extract_images from utils_links.py   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. VERIFY LINKS (async)                                    │
│  - Internal: lookup status from scraped files               │
│  - External: HEAD requests in parallel                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ASSEMBLE REPORT                                         │
│  - Build PageSEOReport dataclass                            │
│  - Collect all issues into summary list                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. OUTPUT                                                  │
│  - Write JSON to {filename}_seo_report.json                 │
│  - Print summary to terminal                                │
└─────────────────────────────────────────────────────────────┘
```

## Link Verification Strategy

- **Internal links:** Look up HTTP status from scraped file names (e.g., `200-page.html` → status 200)
- **External links:** Make live HEAD requests in parallel with concurrency limit
- All links include: href, anchor text, rel attributes (nofollow, sponsored, ugc)

## SEO Best Practices Encoded

### Title Tag
- Should exist
- Recommended length: 50-60 characters
- Flag if truncated (>60 chars)

### Meta Description
- Should exist
- Recommended length: 150-160 characters
- Flag if missing or too short (<70 chars)

### H1
- Exactly one per page
- Flag if missing or multiple

### Heading Hierarchy
- Should follow logical nesting (no H3 before H2, etc.)
- Flag skipped levels

### Canonical
- Should exist
- Self-referential canonicals are valid
- Flag if pointing to different domain

### Images
- All images should have alt text
- Prefer modern formats (webp, avif)
- Lazy loading recommended for below-fold images

### Mobile
- Viewport meta tag required
- Should include `width=device-width`

## Future Enhancements (Out of Scope)

- Live URL fetching (currently local files only)
- Batch mode across all scraped pages
- HTML report generation
- Integration with Google Search Console API
- Content quality scoring
