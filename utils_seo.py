"""Utility functions for extracting SEO elements from HTML pages."""

import json
import re
from collections import Counter
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models_seo import (
    CanonicalInfo,
    FAQInfo,
    HeadingInfo,
    HeadingItem,
    HeadingsHierarchy,
    HreflangInfo,
    KeywordsInfo,
    KeywordTerm,
    LocalizationInfo,
    MetaInfo,
    OpenGraphInfo,
    RobotsInfo,
    SchemaInfo,
    ScriptInfo,
    TitleInfo,
    TwitterCardInfo,
    ViewportInfo,
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


def _get_schema_type(data: dict) -> str:
    """Get normalized schema type from JSON-LD data.

    Args:
        data: JSON-LD data dict.

    Returns:
        Schema type as string, joined by comma if multiple types.
    """
    schema_type = data.get("@type", "Unknown")
    if isinstance(schema_type, list):
        return ", ".join(schema_type)
    return schema_type


def _get_str(data: dict, key: str) -> str | None:
    """Safely extract a string value from schema data."""
    val = data.get(key)
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("@value") or val.get("name") or val.get("url")
    if isinstance(val, list) and val:
        return _get_str({"v": val[0]}, "v")
    return str(val) if val else None


def _get_int(data: dict, key: str) -> int | None:
    """Safely extract an integer value from schema data."""
    val = data.get(key)
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            return None
    return None


def _get_float(data: dict, key: str) -> float | None:
    """Safely extract a float value from schema data."""
    val = data.get(key)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(",", ""))
        except ValueError:
            return None
    return None


def _parse_faq_schema(data: dict) -> dict:
    """Parse FAQPage schema into normalized structure.

    Args:
        data: Raw FAQPage JSON-LD data.

    Returns:
        Dict with questions list containing question/answer pairs.
    """
    questions = []
    main_entity = data.get("mainEntity", [])
    if not isinstance(main_entity, list):
        main_entity = [main_entity]

    for entity in main_entity:
        if not isinstance(entity, dict):
            continue
        entity_type = entity.get("@type", "")
        if entity_type == "Question":
            question = _get_str(entity, "name")
            accepted_answer = entity.get("acceptedAnswer", {})
            answer = None
            if isinstance(accepted_answer, dict):
                answer = _get_str(accepted_answer, "text")
            if question:
                questions.append({"question": question, "answer": answer})

    return {"questions": questions}


def _parse_product_schema(data: dict) -> dict:
    """Parse Product schema into normalized structure.

    Args:
        data: Raw Product JSON-LD data.

    Returns:
        Dict with product details including price, availability, reviews.
    """
    parsed: dict = {
        "name": _get_str(data, "name"),
        "price": None,
        "currency": None,
        "availability": None,
        "rating": None,
        "review_count": None,
        "images": [],
    }

    # Extract offers (price, currency, availability)
    offers = data.get("offers")
    if offers:
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            parsed["price"] = _get_float(offers, "price")
            parsed["currency"] = _get_str(offers, "priceCurrency")
            availability = _get_str(offers, "availability")
            if availability:
                parsed["availability"] = availability.replace("https://schema.org/", "").replace("http://schema.org/", "")

    # Extract aggregate rating
    rating = data.get("aggregateRating")
    if isinstance(rating, dict):
        parsed["rating"] = _get_float(rating, "ratingValue")
        parsed["review_count"] = _get_int(rating, "reviewCount") or _get_int(rating, "ratingCount")

    # Extract images
    image = data.get("image")
    if image:
        if isinstance(image, str):
            parsed["images"] = [image]
        elif isinstance(image, list):
            parsed["images"] = [img if isinstance(img, str) else img.get("url", "") for img in image if img]
        elif isinstance(image, dict):
            url = image.get("url")
            if url:
                parsed["images"] = [url]

    return parsed


def _parse_article_schema(data: dict) -> dict:
    """Parse Article/NewsArticle/BlogPosting schema into normalized structure.

    Args:
        data: Raw Article JSON-LD data.

    Returns:
        Dict with article details including headline, author, dates.
    """
    parsed: dict = {
        "headline": _get_str(data, "headline") or _get_str(data, "name"),
        "author": None,
        "date_published": _get_str(data, "datePublished"),
        "date_modified": _get_str(data, "dateModified"),
        "image": None,
    }

    # Extract author (can be string, object, or array)
    author = data.get("author")
    if author:
        if isinstance(author, str):
            parsed["author"] = author
        elif isinstance(author, dict):
            parsed["author"] = _get_str(author, "name")
        elif isinstance(author, list):
            authors = []
            for a in author:
                if isinstance(a, str):
                    authors.append(a)
                elif isinstance(a, dict):
                    name = _get_str(a, "name")
                    if name:
                        authors.append(name)
            parsed["author"] = authors if len(authors) > 1 else (authors[0] if authors else None)

    # Extract image
    image = data.get("image")
    if image:
        if isinstance(image, str):
            parsed["image"] = image
        elif isinstance(image, dict):
            parsed["image"] = _get_str(image, "url")
        elif isinstance(image, list) and image:
            first = image[0]
            if isinstance(first, str):
                parsed["image"] = first
            elif isinstance(first, dict):
                parsed["image"] = _get_str(first, "url")

    return parsed


def _parse_image_schema(data: dict) -> dict:
    """Parse ImageObject schema into normalized structure.

    Args:
        data: Raw ImageObject JSON-LD data.

    Returns:
        Dict with image details including url, caption, dimensions.
    """
    return {
        "url": _get_str(data, "url") or _get_str(data, "contentUrl"),
        "caption": _get_str(data, "caption"),
        "width": _get_int(data, "width"),
        "height": _get_int(data, "height"),
        "license": _get_str(data, "license"),
    }


def _parse_video_schema(data: dict) -> dict:
    """Parse VideoObject schema into normalized structure.

    Args:
        data: Raw VideoObject JSON-LD data.

    Returns:
        Dict with video details including url, thumbnail, duration.
    """
    return {
        "url": _get_str(data, "contentUrl") or _get_str(data, "url"),
        "name": _get_str(data, "name"),
        "description": _get_str(data, "description"),
        "thumbnail": _get_str(data, "thumbnailUrl"),
        "duration": _get_str(data, "duration"),
        "upload_date": _get_str(data, "uploadDate"),
    }


def _parse_organization_schema(data: dict) -> dict:
    """Parse Organization/LocalBusiness schema into normalized structure.

    Args:
        data: Raw Organization JSON-LD data.

    Returns:
        Dict with organization details including name, address, contact.
    """
    parsed: dict = {
        "name": _get_str(data, "name"),
        "url": _get_str(data, "url"),
        "logo": None,
        "address": None,
        "phone": _get_str(data, "telephone"),
    }

    # Extract logo
    logo = data.get("logo")
    if logo:
        if isinstance(logo, str):
            parsed["logo"] = logo
        elif isinstance(logo, dict):
            parsed["logo"] = _get_str(logo, "url")

    # Extract address
    address = data.get("address")
    if address:
        if isinstance(address, str):
            parsed["address"] = address
        elif isinstance(address, dict):
            parts = []
            for field in ["streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"]:
                val = _get_str(address, field)
                if val:
                    parts.append(val)
            if parts:
                parsed["address"] = ", ".join(parts)

    return parsed


def _parse_breadcrumb_schema(data: dict) -> dict:
    """Parse BreadcrumbList schema into normalized structure.

    Args:
        data: Raw BreadcrumbList JSON-LD data.

    Returns:
        Dict with list of breadcrumb items with position, name, url.
    """
    items = []
    item_list = data.get("itemListElement", [])
    if not isinstance(item_list, list):
        item_list = [item_list]

    for element in item_list:
        if not isinstance(element, dict):
            continue
        position = _get_int(element, "position")
        name = _get_str(element, "name")
        url = None

        item = element.get("item")
        if item:
            if isinstance(item, str):
                url = item
            elif isinstance(item, dict):
                url = _get_str(item, "@id") or _get_str(item, "url")
                if not name:
                    name = _get_str(item, "name")

        if name or url:
            items.append({"position": position, "name": name, "url": url})

    items.sort(key=lambda x: x.get("position") or 0)
    return {"items": items}


def _parse_howto_schema(data: dict) -> dict:
    """Parse HowTo schema into normalized structure.

    Args:
        data: Raw HowTo JSON-LD data.

    Returns:
        Dict with name, steps list, and total time.
    """
    parsed: dict = {
        "name": _get_str(data, "name"),
        "steps": [],
        "total_time": _get_str(data, "totalTime"),
    }

    steps = data.get("step", [])
    if not isinstance(steps, list):
        steps = [steps]

    for step in steps:
        if not isinstance(step, dict):
            continue
        step_name = _get_str(step, "name")
        step_text = _get_str(step, "text")
        if step_name or step_text:
            parsed["steps"].append({"name": step_name, "text": step_text})

    return parsed


def _parse_recipe_schema(data: dict) -> dict:
    """Parse Recipe schema into normalized structure.

    Args:
        data: Raw Recipe JSON-LD data.

    Returns:
        Dict with name, ingredients, instructions, cook/prep times.
    """
    parsed: dict = {
        "name": _get_str(data, "name"),
        "ingredients": [],
        "instructions": [],
        "cook_time": _get_str(data, "cookTime"),
        "prep_time": _get_str(data, "prepTime"),
    }

    # Extract ingredients
    ingredients = data.get("recipeIngredient", [])
    if isinstance(ingredients, list):
        parsed["ingredients"] = [str(i) for i in ingredients if i]
    elif ingredients:
        parsed["ingredients"] = [str(ingredients)]

    # Extract instructions
    instructions = data.get("recipeInstructions", [])
    if not isinstance(instructions, list):
        instructions = [instructions]

    for instr in instructions:
        if isinstance(instr, str):
            parsed["instructions"].append(instr)
        elif isinstance(instr, dict):
            text = _get_str(instr, "text")
            if text:
                parsed["instructions"].append(text)

    return parsed


def _parse_event_schema(data: dict) -> dict:
    """Parse Event schema into normalized structure.

    Args:
        data: Raw Event JSON-LD data.

    Returns:
        Dict with event details including dates, location, price.
    """
    parsed: dict = {
        "name": _get_str(data, "name"),
        "start_date": _get_str(data, "startDate"),
        "end_date": _get_str(data, "endDate"),
        "location": None,
        "price": None,
    }

    # Extract location
    location = data.get("location")
    if location:
        if isinstance(location, str):
            parsed["location"] = location
        elif isinstance(location, dict):
            loc_name = _get_str(location, "name")
            loc_address = location.get("address")
            if loc_address and isinstance(loc_address, dict):
                addr_parts = []
                for field in ["streetAddress", "addressLocality", "addressRegion"]:
                    val = _get_str(loc_address, field)
                    if val:
                        addr_parts.append(val)
                if loc_name:
                    parsed["location"] = f"{loc_name}, {', '.join(addr_parts)}" if addr_parts else loc_name
                elif addr_parts:
                    parsed["location"] = ", ".join(addr_parts)
            elif loc_name:
                parsed["location"] = loc_name

    # Extract price from offers
    offers = data.get("offers")
    if offers:
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            parsed["price"] = _get_float(offers, "price")

    return parsed


def _parse_website_schema(data: dict) -> dict:
    """Parse WebSite schema into normalized structure.

    Args:
        data: Raw WebSite JSON-LD data.

    Returns:
        Dict with website details including name, url, search action.
    """
    parsed: dict = {
        "name": _get_str(data, "name"),
        "url": _get_str(data, "url"),
        "search_url_template": None,
    }

    # Extract search action
    potential_action = data.get("potentialAction")
    if potential_action:
        if isinstance(potential_action, list):
            potential_action = potential_action[0] if potential_action else {}
        if isinstance(potential_action, dict):
            action_type = potential_action.get("@type", "")
            if action_type == "SearchAction":
                target = potential_action.get("target")
                if isinstance(target, str):
                    parsed["search_url_template"] = target
                elif isinstance(target, dict):
                    parsed["search_url_template"] = _get_str(target, "urlTemplate")

    return parsed


def _parse_itemlist_schema(data: dict) -> dict:
    """Parse ItemList schema into normalized structure.

    Args:
        data: Raw ItemList JSON-LD data.

    Returns:
        Dict with list of items containing position and name/url.
    """
    items = []
    item_list = data.get("itemListElement", [])
    if not isinstance(item_list, list):
        item_list = [item_list]

    for element in item_list:
        if not isinstance(element, dict):
            continue
        position = _get_int(element, "position")
        item = element.get("item")
        name = _get_str(element, "name")
        url = _get_str(element, "url")

        if item:
            if isinstance(item, str):
                url = item
            elif isinstance(item, dict):
                if not name:
                    name = _get_str(item, "name")
                if not url:
                    url = _get_str(item, "url") or _get_str(item, "@id")

        if name or url:
            items.append({"position": position, "name": name, "url": url})

    return {"items": items, "count": len(items)}


# Map schema types to their parser functions
_SCHEMA_PARSERS: dict = {
    "FAQPage": _parse_faq_schema,
    "Product": _parse_product_schema,
    "Article": _parse_article_schema,
    "NewsArticle": _parse_article_schema,
    "BlogPosting": _parse_article_schema,
    "ImageObject": _parse_image_schema,
    "VideoObject": _parse_video_schema,
    "Organization": _parse_organization_schema,
    "LocalBusiness": _parse_organization_schema,
    "BreadcrumbList": _parse_breadcrumb_schema,
    "HowTo": _parse_howto_schema,
    "Recipe": _parse_recipe_schema,
    "Event": _parse_event_schema,
    "WebSite": _parse_website_schema,
    "ItemList": _parse_itemlist_schema,
}


def extract_structured_data(soup: BeautifulSoup) -> list[SchemaInfo]:
    """Extract JSON-LD structured data from the page.

    Supports all common schema.org types and extracts key fields
    into a normalized parsed dict for each schema.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        List of SchemaInfo with type, raw data, and parsed fields.
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

        # Collect all schema objects to process
        items_to_process: list[dict] = []

        if isinstance(data, list):
            items_to_process.extend(data)
        elif isinstance(data, dict):
            # Handle @graph arrays (common pattern in modern websites)
            if "@graph" in data:
                graph = data["@graph"]
                if isinstance(graph, list):
                    items_to_process.extend(graph)
                elif isinstance(graph, dict):
                    items_to_process.append(graph)
            else:
                items_to_process.append(data)

        for item in items_to_process:
            if not isinstance(item, dict):
                continue

            schema_type = _get_schema_type(item)

            # Find and apply appropriate parser
            parsed: dict = {}
            primary_type = schema_type.split(",")[0].strip()
            if primary_type in _SCHEMA_PARSERS:
                parsed = _SCHEMA_PARSERS[primary_type](item)

            schemas.append(SchemaInfo(type=schema_type, raw=item, parsed=parsed))

    return schemas


def extract_viewport(soup: BeautifulSoup) -> ViewportInfo:
    """Extract viewport meta tag and check mobile-friendliness.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        ViewportInfo with content, mobile-friendly status, and any issues.
    """
    issues: list[str] = []
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})

    if not viewport_tag:
        return ViewportInfo(
            content=None, is_mobile_friendly=False, issues=["Missing viewport meta tag"]
        )

    content = viewport_tag.get("content", "")
    if isinstance(content, list):
        content = content[0] if content else ""
    content = content.strip()

    if not content:
        return ViewportInfo(
            content=None, is_mobile_friendly=False, issues=["Missing viewport meta tag"]
        )

    is_mobile_friendly = "width=device-width" in content

    if not is_mobile_friendly:
        issues.append("Viewport missing width=device-width")

    return ViewportInfo(
        content=content, is_mobile_friendly=is_mobile_friendly, issues=issues
    )


def extract_hreflang(soup: BeautifulSoup) -> list[HreflangInfo]:
    """Extract hreflang link tags for internationalization.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        List of HreflangInfo with language and URL for each tag.
    """
    hreflangs: list[HreflangInfo] = []

    hreflang_tags = soup.find_all("link", rel="alternate", hreflang=True)

    for tag in hreflang_tags:
        lang = tag.get("hreflang", "")
        href = tag.get("href", "")

        if isinstance(lang, list):
            lang = lang[0] if lang else ""
        if isinstance(href, list):
            href = href[0] if href else ""

        lang = lang.strip()
        href = href.strip()

        if lang and href:
            hreflangs.append(HreflangInfo(lang=lang, url=href))

    return hreflangs


def extract_localization(soup: BeautifulSoup) -> LocalizationInfo:
    """Extract page localization information.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        LocalizationInfo with HTML lang attribute and content-language header value.
    """
    html_tag = soup.find("html")

    html_lang: str | None = None
    if html_tag:
        lang = html_tag.get("lang", "")
        if isinstance(lang, list):
            lang = lang[0] if lang else ""
        html_lang = lang.strip() if lang.strip() else None

    return LocalizationInfo(
        html_lang=html_lang,
        content_language=None,  # Comes from HTTP headers, not HTML
    )


def extract_scripts(soup: BeautifulSoup) -> list[ScriptInfo]:
    """Extract script information from the page.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        List of ScriptInfo with src, async/defer attributes, and inline details.
    """
    scripts: list[ScriptInfo] = []

    script_tags = soup.find_all("script")

    for tag in script_tags:
        src = tag.get("src")
        if isinstance(src, list):
            src = src[0] if src else None

        if src:
            # External script
            has_async = tag.has_attr("async")
            has_defer = tag.has_attr("defer")
            scripts.append(
                ScriptInfo(
                    src=src.strip(),
                    is_inline=False,
                    inline_size=None,
                    has_async=has_async,
                    has_defer=has_defer,
                )
            )
        else:
            # Inline script
            content = tag.string or ""
            content = content.strip()
            if content:  # Skip empty inline scripts
                scripts.append(
                    ScriptInfo(
                        src=None,
                        is_inline=True,
                        inline_size=len(content),
                        has_async=False,
                        has_defer=False,
                    )
                )

    return scripts


def extract_faq_sections(soup: BeautifulSoup) -> list[FAQInfo]:
    """Extract FAQ content from JSON-LD schema and HTML patterns.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        List of FAQInfo with question, answer, and schema status.
    """
    faqs: list[FAQInfo] = []
    seen_questions: set[str] = set()

    # Source 1: JSON-LD FAQPage schema
    ld_json_tags = soup.find_all("script", attrs={"type": "application/ld+json"})

    for tag in ld_json_tags:
        content = tag.string
        if not content:
            continue

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            schema_type = item.get("@type", "")
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else ""

            if schema_type == "FAQPage":
                main_entity = item.get("mainEntity", [])
                if not isinstance(main_entity, list):
                    main_entity = [main_entity]

                for entity in main_entity:
                    if not isinstance(entity, dict):
                        continue
                    entity_type = entity.get("@type", "")
                    if entity_type == "Question":
                        question = entity.get("name", "")
                        accepted_answer = entity.get("acceptedAnswer", {})
                        if isinstance(accepted_answer, dict):
                            answer = accepted_answer.get("text", "")
                        else:
                            answer = ""

                        if question and answer:
                            question_key = question.strip().lower()
                            if question_key not in seen_questions:
                                seen_questions.add(question_key)
                                faqs.append(
                                    FAQInfo(
                                        question=question.strip(),
                                        answer=answer.strip(),
                                        has_schema=True,
                                    )
                                )

    # Source 2: HTML patterns

    # Pattern 2a: <details><summary>Question</summary>Answer</details>
    details_tags = soup.find_all("details")
    for details in details_tags:
        summary = details.find("summary")
        if summary:
            question = summary.get_text(strip=True)
            # Get answer: all text except summary
            answer_parts = []
            for child in details.children:
                if child != summary and hasattr(child, "get_text"):
                    answer_parts.append(child.get_text(strip=True))
                elif child != summary and isinstance(child, str):
                    text = child.strip()
                    if text:
                        answer_parts.append(text)
            answer = " ".join(answer_parts).strip()

            if question and answer:
                question_key = question.strip().lower()
                if question_key not in seen_questions:
                    seen_questions.add(question_key)
                    faqs.append(
                        FAQInfo(question=question, answer=answer, has_schema=False)
                    )

    # Pattern 2b: <dt>Question</dt><dd>Answer</dd>
    dt_tags = soup.find_all("dt")
    for dt in dt_tags:
        question = dt.get_text(strip=True)
        dd = dt.find_next_sibling("dd")
        if dd:
            answer = dd.get_text(strip=True)
            if question and answer:
                question_key = question.strip().lower()
                if question_key not in seen_questions:
                    seen_questions.add(question_key)
                    faqs.append(
                        FAQInfo(question=question, answer=answer, has_schema=False)
                    )

    # Pattern 2c: Elements with class/id containing "faq"
    faq_containers = soup.find_all(
        lambda tag: tag.get("class")
        and any("faq" in c.lower() for c in tag.get("class", []))
        or tag.get("id")
        and "faq" in tag.get("id", "").lower()
    )

    for container in faq_containers:
        # Look for heading + content pairs within FAQ containers
        headings = container.find_all(["h2", "h3", "h4", "h5", "h6"])
        for heading in headings:
            question = heading.get_text(strip=True)
            # Get next sibling that contains answer content
            next_elem = heading.find_next_sibling()
            if next_elem and next_elem.name in ["p", "div", "span"]:
                answer = next_elem.get_text(strip=True)
                if question and answer:
                    question_key = question.strip().lower()
                    if question_key not in seen_questions:
                        seen_questions.add(question_key)
                        faqs.append(
                            FAQInfo(question=question, answer=answer, has_schema=False)
                        )

    return faqs


# Common stop words for keyword extraction
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "and",
        "but",
        "or",
        "if",
        "because",
        "until",
        "while",
        "about",
        "against",
        "between",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "our",
        "their",
        "what",
        "which",
    }
)


def extract_keywords(soup: BeautifulSoup) -> KeywordsInfo:
    """Extract and analyze keywords from page visible text.

    Args:
        soup: A BeautifulSoup object of the parsed HTML.

    Returns:
        KeywordsInfo with top 20 terms and total word count.
    """
    # Get body element, or fall back to entire soup
    body = soup.find("body")
    if not body:
        body = soup

    # Remove script, style, and noscript elements
    for tag in body.find_all(["script", "style", "noscript"]):
        tag.decompose()

    # Get visible text
    text = body.get_text(separator=" ", strip=True)

    # Tokenize: lowercase, alphanumeric only
    words = re.findall(r"[a-z0-9]+", text.lower())

    total_words = len(words)

    # Filter out stop words
    filtered_words = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    # Count frequencies
    word_counts = Counter(filtered_words)

    # Get top 20 terms
    top_20 = word_counts.most_common(20)
    top_terms = [KeywordTerm(term=term, count=count) for term, count in top_20]

    return KeywordsInfo(top_terms=top_terms, total_words=total_words)
