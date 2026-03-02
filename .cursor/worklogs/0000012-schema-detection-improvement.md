# Schema Detection Improvement

**Date:** 2026-02-23

## Summary

Enhanced schema detection and parsing in `3-page-checker.py` to recognize all common modern website schema types and extract key fields into a normalized `parsed` dictionary.

## Changes Made

### models_seo.py
- Added `parsed: dict[str, Any]` field to `SchemaInfo` dataclass for normalized extracted data

### utils_seo.py
- Added helper functions for safe data extraction:
  - `_get_schema_type()` - normalize schema type from JSON-LD
  - `_get_str()`, `_get_int()`, `_get_float()` - safe type extraction

- Implemented schema parsers for all common types:
  - `_parse_faq_schema()` - FAQPage questions/answers
  - `_parse_product_schema()` - Product with price, availability, reviews
  - `_parse_article_schema()` - Article/NewsArticle/BlogPosting
  - `_parse_image_schema()` - ImageObject with dimensions, license
  - `_parse_video_schema()` - VideoObject with thumbnail, duration
  - `_parse_organization_schema()` - Organization/LocalBusiness
  - `_parse_breadcrumb_schema()` - BreadcrumbList navigation
  - `_parse_howto_schema()` - HowTo with steps
  - `_parse_recipe_schema()` - Recipe with ingredients/instructions
  - `_parse_event_schema()` - Event with dates, location, price
  - `_parse_website_schema()` - WebSite with search action
  - `_parse_itemlist_schema()` - ItemList elements

- Updated `extract_structured_data()`:
  - Handles `@graph` arrays (common in modern sites)
  - Dispatches to appropriate parser by `@type`
  - Returns `SchemaInfo` with both `raw` and `parsed` fields

## Schema Types Supported

| Category | Schema Types |
|----------|--------------|
| Content | FAQPage, Article, NewsArticle, BlogPosting, HowTo, Recipe |
| E-commerce | Product (with Offer extraction) |
| Media | ImageObject, VideoObject |
| Business | Organization, LocalBusiness, WebSite |
| Navigation | BreadcrumbList, ItemList |
| Events | Event |

## Backward Compatibility

The `raw` field is preserved unchanged. The new `parsed` field provides normalized access to key fields without breaking existing code that uses `raw`.
