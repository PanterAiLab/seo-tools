# Link Content Type Detection

## Summary
Added `content_type` field to `LinkInfo` to identify what kind of content an `<a>` element contains.

## Changes Made

### models_seo.py
- Added `content_type: str = "text"` field to `LinkInfo` dataclass
- Possible values: `text`, `image`, `logo`, `icon`, `button`, `svg`, `mixed`, `empty`

### utils_links.py
- Added helper patterns for detecting logos, icons, and buttons
- Added `_detect_link_content_type(anchor: Tag) -> str` function that analyzes:
  - Presence of `<img>` tags
  - Presence of `<svg>` elements
  - Icon elements (`<i>` with FontAwesome/Material Icons classes)
  - CSS classes indicating logos, buttons, or icons
  - Mix of text + images
- Updated `extract_links()` to call the detection function and populate `content_type`

### 5-seo-diff.py
- Updated link diff display to show specific content type (e.g., `(icon link)`, `(logo link)`) instead of generic `(no anchor - image/icon/button)`

## Detection Logic
1. Check for `<img>` tags → `image` (or `logo` if logo patterns match)
2. Check for `<svg>` elements → `svg`
3. Check for icon elements (font icons) → `icon`
4. Check for button classes → `button`
5. Mix of text + image/icon → `mixed`
6. No content → `empty`
7. Default → `text`

## Testing
Verified with test HTML containing various link types:
- Logo links correctly identified
- Icon links (FontAwesome) correctly identified
- Button links correctly identified
- Mixed content (image + text) correctly identified
- Empty links correctly identified
