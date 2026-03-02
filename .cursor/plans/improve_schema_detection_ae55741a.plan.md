---
name: Improve Schema Detection
overview: Enhance schema detection in 3-page-checker.py to recognize all common modern website schema types and extract their key fields into a normalized parsed dictionary, while maintaining the raw data for full access.
todos:
  - id: update-model
    content: Add `parsed` field to SchemaInfo dataclass in models_seo.py
    status: completed
  - id: handle-graph
    content: Update extract_structured_data() to handle @graph arrays
    status: completed
  - id: parser-faq
    content: Implement _parse_faq_schema() parser
    status: completed
  - id: parser-product
    content: Implement _parse_product_schema() parser
    status: completed
  - id: parser-article
    content: Implement _parse_article_schema() for Article/NewsArticle/BlogPosting
    status: completed
  - id: parser-image
    content: Implement _parse_image_schema() parser
    status: completed
  - id: parser-video
    content: Implement _parse_video_schema() parser
    status: completed
  - id: parser-org
    content: Implement _parse_organization_schema() for Organization/LocalBusiness
    status: completed
  - id: parser-breadcrumb
    content: Implement _parse_breadcrumb_schema() parser
    status: completed
  - id: parser-howto
    content: Implement _parse_howto_schema() parser
    status: completed
  - id: parser-recipe
    content: Implement _parse_recipe_schema() parser
    status: completed
  - id: parser-event
    content: Implement _parse_event_schema() parser
    status: completed
  - id: integrate-parsers
    content: Update extract_structured_data() to dispatch to parsers by type
    status: completed
  - id: worklog
    content: Create worklog entry documenting the changes
    status: completed
isProject: false
---

# Improve Schema Detection and Parsing

## Summary

Extend `extract_structured_data()` in `utils_seo.py` to:

1. Recognize all common schema.org types used in modern websites
2. Extract key fields from each schema type into a normalized `parsed` dict
3. Keep backward compatibility with existing `SchemaInfo.raw` field

## Schema Types to Support

**Content Schemas:**

- FAQPage - questions/answers
- Article, NewsArticle, BlogPosting - headline, author, datePublished, dateModified
- HowTo - name, steps, totalTime
- Recipe - name, ingredients, instructions, cookTime

**E-commerce Schemas:**

- Product - name, price, currency, availability, reviews, images
- Offer - price, availability, url

**Media Schemas:**

- ImageObject - url, caption, width, height, license
- VideoObject - name, description, thumbnailUrl, duration, uploadDate

**Business Schemas:**

- Organization, LocalBusiness - name, address, phone, url, logo
- WebSite - name, url, searchAction

**Navigation Schemas:**

- BreadcrumbList - items with position, name, url
- ItemList - itemListElement

**Events:**

- Event - name, startDate, endDate, location, offers

## Changes to [models_seo.py](models_seo.py)

Update `SchemaInfo` dataclass:

```python
@dataclass
class SchemaInfo:
    """JSON-LD structured data information."""
    type: str
    raw: dict[str, Any] = field(default_factory=dict)
    parsed: dict[str, Any] = field(default_factory=dict)  # NEW: normalized extracted fields
```

## Changes to [utils_seo.py](utils_seo.py)

1. Add schema parser functions for each type:
  - `_parse_faq_schema(data: dict) -> dict`
  - `_parse_product_schema(data: dict) -> dict`
  - `_parse_article_schema(data: dict) -> dict`
  - `_parse_image_schema(data: dict) -> dict`
  - `_parse_video_schema(data: dict) -> dict`
  - `_parse_organization_schema(data: dict) -> dict`
  - `_parse_breadcrumb_schema(data: dict) -> dict`
  - `_parse_howto_schema(data: dict) -> dict`
  - `_parse_recipe_schema(data: dict) -> dict`
  - `_parse_event_schema(data: dict) -> dict`
2. Update `extract_structured_data()` to:
  - Handle nested `@graph` arrays (common pattern)
  - Call appropriate parser based on `@type`
  - Support type aliases (e.g., Article/NewsArticle/BlogPosting)

## Parsed Field Structure by Type

**FAQPage:**

```python
{"questions": [{"question": str, "answer": str}, ...]}
```

**Product:**

```python
{"name": str, "price": float|None, "currency": str|None, "availability": str|None, "rating": float|None, "review_count": int|None, "images": [str]}
```

**Article/NewsArticle/BlogPosting:**

```python
{"headline": str, "author": str|list|None, "date_published": str|None, "date_modified": str|None, "image": str|None}
```

**ImageObject:**

```python
{"url": str, "caption": str|None, "width": int|None, "height": int|None, "license": str|None}
```

**VideoObject:**

```python
{"url": str, "name": str|None, "description": str|None, "thumbnail": str|None, "duration": str|None, "upload_date": str|None}
```

**Organization/LocalBusiness:**

```python
{"name": str, "url": str|None, "logo": str|None, "address": str|None, "phone": str|None}
```

**BreadcrumbList:**

```python
{"items": [{"position": int, "name": str, "url": str|None}, ...]}
```

**HowTo:**

```python
{"name": str, "steps": [{"name": str, "text": str}, ...], "total_time": str|None}
```

**Recipe:**

```python
{"name": str, "ingredients": [str], "instructions": [str], "cook_time": str|None, "prep_time": str|None}
```

**Event:**

```python
{"name": str, "start_date": str|None, "end_date": str|None, "location": str|None, "price": float|None}
```

## No Changes to [3-page-checker.py](3-page-checker.py)

The main script doesn't need changes - it already calls `extract_structured_data()` and stores results in the report. The enhanced `parsed` field will automatically appear in JSON output.