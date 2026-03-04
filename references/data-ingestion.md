# Data Ingestion Reference

## Column Mapping and Normalisation

All crawl data is normalised into a standard internal schema. This reference defines how to map columns from each supported tool.

## Internal Schema

These are the normalised column names used throughout the analysis:

| Internal Field | Type | Description |
|---|---|---|
| url | string | Full URL including protocol |
| content_type | string | MIME type (text/html, application/json, etc.) |
| status_code | integer | HTTP response code |
| status_text | string | HTTP status text (OK, Not Found, etc.) |
| indexability | string | Indexable / Non-Indexable |
| indexability_reason | string | Why non-indexable (noindex, canonicalised, etc.) |
| title | string | Page title tag content |
| title_length | integer | Character count of title |
| title_pixel_width | integer | Pixel width of title in SERPs |
| meta_description | string | Meta description content |
| meta_description_length | integer | Character count of meta description |
| meta_keywords | string | Meta keywords (legacy) |
| h1 | string | First H1 tag content |
| h1_length | integer | Character count of H1 |
| h2 | string | First H2 tag content |
| meta_robots | string | Meta robots directive |
| x_robots_tag | string | X-Robots-Tag header value |
| canonical | string | Canonical link element URL |
| rel_next | string | Pagination next URL |
| rel_prev | string | Pagination prev URL |
| word_count | integer | Number of words on page |
| text_ratio | float | Text to HTML ratio percentage |
| page_size_bytes | integer | Page size in bytes |
| transferred_bytes | integer | Transferred size in bytes |
| response_time | float | Server response time in seconds |
| crawl_depth | integer | Clicks from seed URL |
| folder_depth | integer | Number of path segments in URL |
| inlinks | integer | Total internal inlinks |
| unique_inlinks | integer | Unique internal inlinks |
| outlinks | integer | Total outlinks from page |
| external_outlinks | integer | External outlinks |
| redirect_url | string | Target URL if redirect |
| redirect_type | string | Redirect type (301, 302, meta, JS) |
| language | string | Page language detected |
| hash | string | Content hash for duplicate detection |
| last_modified | string | Last-Modified header value |
| http_version | string | HTTP/1.1 or HTTP/2 |
| co2_mg | float | CO2 emissions estimate in mg |
| readability_score | float | Flesch Reading Ease score |
| sentence_count | integer | Number of sentences |
| near_duplicate_match | string | URL of closest near-duplicate |
| near_duplicate_count | integer | Number of near-duplicates |
| spelling_errors | integer | Spelling error count |
| grammar_errors | integer | Grammar error count |
| link_score | float | Internal PageRank / link equity score |
| semantic_similarity_url | string | Most semantically similar page |
| semantic_similarity_score | float | Similarity score (0-1) |

---

## Tool-Specific Column Mappings

### Screaming Frog (internal_html.csv / internal_all.csv)

Detection signature: Headers contain "Address" AND ("Status Code" OR "Indexability")

```
Address -> url
Content Type -> content_type
Status Code -> status_code
Status -> status_text
Indexability -> indexability
Indexability Status -> indexability_reason
Title 1 -> title
Title 1 Length -> title_length
Title 1 Pixel Width -> title_pixel_width
Meta Description 1 -> meta_description
Meta Description 1 Length -> meta_description_length
Meta Description 1 Pixel Width -> (stored as meta_description_pixel_width)
Meta Keywords 1 -> meta_keywords
H1-1 -> h1
H1-1 Length -> h1_length
H2-1 -> h2
H2-1 Length -> (stored as h2_length)
Meta Robots 1 -> meta_robots
X-Robots-Tag 1 -> x_robots_tag
Canonical Link Element 1 -> canonical
rel="next" 1 -> rel_next
rel="prev" 1 -> rel_prev
Size (bytes) -> page_size_bytes
Transferred (bytes) -> transferred_bytes
Word Count -> word_count
Text Ratio -> text_ratio
Crawl Depth -> crawl_depth
Folder Depth -> folder_depth
Inlinks -> inlinks
Unique Inlinks -> unique_inlinks
Outlinks -> outlinks
External Outlinks -> external_outlinks
Redirect URL -> redirect_url
Redirect Type -> redirect_type
Response Time -> response_time
Last Modified -> last_modified
Language -> language
Hash -> hash
HTTP Version -> http_version
CO2 (mg) -> co2_mg
Flesch Reading Ease Score -> readability_score
Sentence Count -> sentence_count
Closest Near Duplicate Match -> near_duplicate_match
No. Near Duplicates -> near_duplicate_count
Spelling Errors -> spelling_errors
Grammar Errors -> grammar_errors
Link Score -> link_score
Closest Semantically Similar Address -> semantic_similarity_url
Semantic Similarity Score -> semantic_similarity_score
```

### Sitebulb (urls.csv)

Detection signature: Headers contain "URL" AND ("Indexable" OR "Page Title") AND NOT "Address"

```
URL -> url
Status Code -> status_code
Indexable -> indexability (convert Yes/No to Indexable/Non-Indexable)
Page Title -> title
Meta Description -> meta_description
H1 -> h1
Canonical -> canonical
Word Count -> word_count
Internal Inlinks -> inlinks
Crawl Depth -> crawl_depth
Response Time (ms) -> response_time (divide by 1000 to get seconds)
Page Size -> page_size_bytes
```

### Ahrefs Site Audit (pages.csv)

Detection signature: Headers contain "URL" AND "HTTP Code"

```
URL -> url
HTTP Code -> status_code
Title -> title
Description -> meta_description
H1 -> h1
Canonical URL -> canonical
Word Count -> word_count
Internal Links In -> inlinks
Depth -> crawl_depth
```

### Generic CSV / Unknown Tool

If no known signature is matched:
1. Search for a column containing full URLs (starts with http) — map to `url`
2. Search for a column with numeric values 200-599 — map to `status_code`
3. Match remaining columns by fuzzy header matching (e.g. "page title" -> title)
4. Report which columns were mapped and which were not
5. Ask the user to confirm or correct the mapping

---

## API-Based Crawl Data Normalisation

### Firecrawl Response Mapping

Firecrawl returns page data in this structure per page:
```
markdown: string (full page content as markdown)
html: string (raw HTML)
metadata:
  title: string
  description: string
  language: string
  sourceURL: string
  statusCode: number
links: array of URLs found on page
```

Map to internal schema:
```
metadata.sourceURL -> url
metadata.statusCode -> status_code
metadata.title -> title
metadata.description -> meta_description
metadata.language -> language
```

For fields not provided by Firecrawl (H1, canonical, word count, etc.), parse the HTML content:
- Extract H1 from first <h1> tag in HTML
- Extract canonical from <link rel="canonical"> in HTML
- Calculate word count from the markdown content
- Extract meta robots from <meta name="robots"> in HTML
- Calculate page_size_bytes from len(html.encode('utf-8'))

### DataForSEO On-Page API Mapping

If the user has DataForSEO tools available, use the `instant_pages` tool:
```
meta.title -> title
meta.description -> meta_description
meta.htags.h1[0] -> h1
page_timing.duration -> response_time
onpage_score -> (store as additional metric)
```

---

## Platform Detection Signatures

After loading data, scan URLs and metadata to detect the platform:

| Platform | URL Signatures | Other Signals |
|---|---|---|
| Shopify | `/collections/`, `/products/`, `cdn.shopify.com`, `myshopify.com` | `Shopify` in meta generator, `X-ShopId` header |
| WordPress | `/wp-content/`, `/wp-admin/`, `/wp-json/` | `WordPress` in meta generator, `X-Powered-By: PHP` |
| Wix | `wixsite.com`, `_wix_browser_sess`, `static.wixstatic.com` | Wix-specific JS bundles |
| Squarespace | `squarespace.com`, `/s/`, squarespace CDN URLs | `Squarespace` in meta generator |
| Magento | `/catalog/product/`, `/checkout/cart/`, `mage/` | `Magento` in response headers |
| Webflow | `webflow.io`, `assets.website-files.com` | Webflow meta generator |
| Next.js / Headless | `/_next/`, `__next` data attributes | React hydration markers |
| Gatsby | `/static/`, gatsby chunk patterns | Gatsby meta generator |
| Drupal | `/node/`, `/sites/default/` | Drupal meta generator, `X-Drupal-Cache` |
| Custom | None of the above match | Report as "Custom / Unknown" |

---

## Data Validation

After ingestion and normalisation, run these validation checks:

1. **URL count sanity**: Report total URLs loaded. If < 10, warn the user the crawl may be incomplete.
2. **Status code distribution**: Summarise counts by status code range (2xx, 3xx, 4xx, 5xx).
3. **Missing critical fields**: Report what percentage of rows have empty title, meta description, H1, canonical.
4. **Data freshness**: If crawl timestamp is available, report when the crawl was performed.
5. **Encoding check**: Ensure no garbled characters from encoding mismatches.

Present a quick summary table to the user before proceeding to analysis:
```
Data Source: Screaming Frog (internal_html.csv)
Total URLs: 197
Status 2xx: 185 (93.9%)
Status 3xx: 8 (4.1%)
Status 4xx: 3 (1.5%)
Status 5xx: 1 (0.5%)
Platform Detected: Shopify
Crawl Date: 2026-03-04
```
