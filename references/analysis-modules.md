# Analysis Modules Reference

This document specifies every individual check within each of the 10 audit categories. Each check includes what to look for, severity thresholds, and how to report findings.

---

## Category 1: Crawlability & Accessibility

### 1.1 HTTP Status Code Distribution
**What to check**: Group all URLs by status code range.
**Thresholds**:
- 4xx errors on internal pages = Critical if > 0 (especially on important pages)
- 5xx errors = Critical (server problems)
- High 3xx ratio (> 15% of pages are redirects) = High priority
- Soft 404s (200 status but thin/error content, word count < 50) = High priority

**Report format**: Table with status code breakdown + list of affected URLs for non-2xx.

### 1.2 Redirect Analysis
**What to check**: All pages with status 3xx or redirect_url populated.
- **Redirect chains**: Follow redirects to find chains (A -> B -> C). Any chain > 2 hops is an issue.
- **Redirect loops**: Detect circular redirects (A -> B -> A).
- **Temporary redirects**: 302/307 redirects that should be 301s (especially if > 6 months old).
- **Redirect targets**: Where do redirects land? Check for redirects to 4xx, external domains, or non-canonical URLs.
- **HTTP to HTTPS redirects**: Should exist for all HTTP URLs.

**Thresholds**:
- Redirect chains (3+ hops) = Critical
- Redirect loops = Critical
- 302 on permanent moves = High
- Redirects to 4xx = Critical

### 1.3 Crawl Depth Analysis
**What to check**: Distribution of crawl_depth values across all URLs.
- Pages at depth 0 = Homepage
- Pages at depth 1-2 = Good, easily crawlable
- Pages at depth 3 = Acceptable for large sites
- Pages at depth 4+ = Potential crawl budget issue

**Thresholds**:
- Revenue/key pages at depth 3+ = Critical
- > 20% of indexable pages at depth 4+ = High
- Any page at depth 6+ = Medium (likely orphaned or poorly linked)

**Special handling by site type**:
- Ecommerce: Product pages should be depth 2-3 max (home > category > product)
- Blog: Articles should be depth 1-3 (home > blog > article)
- SaaS: Core pages (pricing, features) should be depth 1

### 1.4 Orphan Pages
**What to check**: Pages with zero or very few internal inlinks (unique_inlinks <= 1, excluding self-links).
**Context matters**: Navigation links count. A page linked only from the sitemap but not from any navigation or content is effectively orphaned for users.

**Thresholds**:
- Indexable page with 0 inlinks = Critical
- Indexable page with only 1 inlink = High (fragile)

### 1.5 URL Structure Quality
**What to check**:
- URLs with parameters (contains `?`) that create duplicate content
- URLs with uppercase characters
- URLs with special characters or encoded spaces
- URLs exceeding 200 characters
- URLs with session IDs or tracking parameters
- URLs with double slashes (excluding protocol)
- Non-descriptive URLs (numeric IDs only, no keywords)

**Thresholds**:
- Parameter URLs creating duplicates = High
- Session IDs in URLs = Critical
- Others = Low to Medium depending on scale

### 1.6 Response Time Analysis
**What to check**: Distribution of response_time values.
- Mean and median response time
- Pages with response time > 1 second
- Pages with response time > 3 seconds
- Patterns (e.g. all product pages slow, all blog pages fast)

**Thresholds**:
- Average response time > 1s = High
- Any page > 3s = Critical for that page
- > 20% of pages > 1s = High (server performance issue)

### 1.7 Robots.txt Analysis
**What to check** (if robots.txt content available):
- Disallow rules blocking important pages or resources
- Sitemap reference present
- Crawl-delay directive (can slow indexing)
- Wildcard rules that may be too broad
- Different rules for different user agents

**Thresholds**:
- Blocking CSS/JS resources = High (rendering issues)
- Blocking important page sections = Critical
- No sitemap reference = Low

### 1.8 XML Sitemap Validation
**What to check** (if sitemap data available):
- Sitemap exists and is accessible
- Sitemap is referenced in robots.txt
- All indexable pages are in the sitemap
- No non-indexable pages in the sitemap (noindex, 4xx, redirects)
- Sitemap is not stale (lastmod dates)
- Sitemap size within limits (< 50MB, < 50,000 URLs per file)

**Thresholds**:
- No sitemap = High
- Sitemap contains noindex/4xx URLs = Medium
- Key pages missing from sitemap = High

---

## Category 2: Indexability & Index Management

### 2.1 Indexability Distribution
**What to check**: Count of Indexable vs Non-Indexable pages and reasons.
- Group non-indexable by reason: noindex, canonicalised, blocked by robots, 3xx, 4xx/5xx
- Check if any pages are unintentionally non-indexable

**Report format**: Pie chart data + breakdown table.

### 2.2 Canonical Tag Audit
**What to check**:
- **Missing canonicals**: Indexable pages without a canonical tag
- **Self-referencing canonicals**: Present and correct (good practice)
- **Non-self-referencing canonicals**: Page points canonical to a different URL (intentional? or error?)
- **Canonical to non-indexable**: Canonical target is noindex, 4xx, or redirects (broken chain)
- **Canonical mismatch**: Canonical URL differs from the actual URL only by trailing slash, www, or protocol
- **Cross-domain canonicals**: Pointing to external domains (rare, verify intentional)
- **Canonical chains**: Page A canonicals to B, B canonicals to C

**Thresholds**:
- Missing canonical on indexable page = Medium
- Canonical to 4xx/noindex = Critical
- Canonical chains = High

### 2.3 Meta Robots & Directives
**What to check**:
- Pages with noindex that should be indexed (assess by page type and importance)
- Pages with nofollow that block link equity flow
- Pages with both noindex and a canonical to another page (conflicting signals)
- X-Robots-Tag overriding meta robots

**Thresholds**:
- Revenue pages with noindex = Critical
- Noindex + canonical conflict = High

### 2.4 Pagination
**What to check**:
- Pages with rel=next/prev attributes
- Paginated series that are not self-canonicalised (each page should canonical to itself)
- Paginated pages that are noindex (Google still recommends indexing paginated pages)
- Missing pagination for large content sets
- "View All" page availability

**Thresholds**:
- Paginated pages canonicalised to page 1 = High (loses deep content)
- Noindex on paginated pages = Medium

### 2.5 Duplicate Content Detection
**What to check**:
- **Exact duplicates**: Pages with identical content hash
- **Near duplicates**: Pages with near_duplicate_count > 0 or semantic_similarity_score > 0.85
- **Thin content clusters**: Groups of pages with very similar content (common in ecommerce with colour/size variants)
- **Parameter duplicates**: Same page accessible via different URL parameters

**Thresholds**:
- Exact duplicates without canonical handling = Critical
- Near duplicates on competing keywords = High
- Thin content clusters = Medium (consolidation opportunity)

---

## Category 3: On-Page SEO Elements

### 3.1 Title Tag Analysis
**What to check**:
- **Missing titles**: No title tag
- **Empty titles**: Title tag exists but empty
- **Duplicate titles**: Multiple pages with identical titles
- **Title too short**: < 30 characters (under-optimised)
- **Title too long**: > 60 characters (may be truncated in SERPs)
- **Title pixel width**: > 580 pixels (will be truncated in SERPs)
- **Title matches H1**: Good signal (or flag if they are identical for every page — might be templated)
- **Brand in title**: Consistent brand format (e.g. "Page Title | Brand")

**Thresholds**:
- Missing title on indexable page = Critical
- Duplicate titles = High
- Too long/short = Medium

### 3.2 Meta Description Analysis
**What to check**:
- **Missing meta descriptions**: Indexable pages without one
- **Empty meta descriptions**: Tag exists but empty
- **Duplicate meta descriptions**: Multiple pages with identical descriptions
- **Too short**: < 70 characters
- **Too long**: > 160 characters (may be truncated)
- **Pixel width**: > 920 pixels

**Thresholds**:
- Missing on key/revenue pages = High
- Missing on other pages = Medium
- Duplicate descriptions = Medium

### 3.3 Heading Analysis
**What to check**:
- **Missing H1**: Indexable page has no H1
- **Multiple H1s**: Page has more than one H1
- **Empty H1**: H1 tag exists but is empty
- **H1 length**: Very short (< 10 chars) or very long (> 70 chars)
- **H1 matches title**: Good practice check
- **Heading hierarchy**: H2s present, logical structure

**Thresholds**:
- Missing H1 on indexable page = High
- Multiple H1s = Medium (less of an issue in HTML5 but still a signal)

### 3.4 Content Quality Signals
**What to check**:
- **Thin content**: Pages with word_count < 300 (threshold varies by page type)
  - Product pages: < 100 words is thin
  - Blog posts: < 300 words is thin
  - Category pages: < 50 words is thin (expected to be lighter)
- **Word count distribution**: Histogram showing content depth across site
- **Readability scores**: Average and outliers
- **Text-to-HTML ratio**: Pages below 10% may be too template-heavy

**Thresholds**:
- Blog post < 300 words = High
- Product page < 100 words = Medium
- Very low text ratio (< 5%) = Medium

### 3.5 Keyword Cannibalisation Detection
**What to check**: Multiple indexable pages with very similar titles or H1s that could compete for the same search queries.
- Group pages by similar title patterns (fuzzy matching)
- Group pages by identical or near-identical H1s
- Flag pages in the same subfolder targeting the same apparent topic

This is a heuristic analysis from crawl data alone. Note: for definitive cannibalisation analysis, GSC data (which pages rank for the same queries) is needed.

**Thresholds**:
- 2+ indexable pages with near-identical titles = High
- Multiple collection/category pages with overlapping terms = Medium

### 3.6 Image Optimisation (if data available)
**What to check**:
- Images missing alt text
- Oversized images (> 200KB)
- Non-modern formats (no WebP/AVIF alternatives)
- Broken image links

---

## Category 4: Site Architecture & Internal Linking

### 4.1 Internal Link Distribution
**What to check**:
- Pages with highest inlinks (navigation hubs)
- Pages with lowest inlinks (under-linked, may be orphaned)
- Average inlinks per page
- Inlink distribution by page type (products vs blog vs categories)

### 4.2 Link Equity Flow
**What to check**:
- Link score distribution (if available)
- Pages with high link score but low inlinks (efficiently linked)
- Pages with low link score despite many inlinks (diluted)
- Nofollow on internal links (leaking equity)

### 4.3 Content Silo Analysis
**What to check**:
- Group pages by URL folder structure
- Identify topical clusters
- Check cross-linking between silos
- Identify pages that break the silo structure

### 4.4 Navigation & Breadcrumbs
**What to check**:
- Consistent navigation link pattern (inferred from inlink counts)
- Breadcrumb presence (from structured data if available)
- Faceted navigation creating parameter URLs (ecommerce)

---

## Category 5: Performance & Core Web Vitals

### 5.1 Page Weight Analysis
**What to check**:
- Page size distribution (page_size_bytes)
- Total transferred bytes distribution
- Pages exceeding 3MB total transferred
- Heaviest pages and their types

**Thresholds**:
- Page > 3MB = High
- Page > 5MB = Critical
- Average page > 2MB = High (site-wide issue)

### 5.2 Response Time Performance
**What to check**:
- Already covered in 1.6, but here focus on patterns:
- Slow page types (which templates are slowest?)
- Server vs content issues (large pages vs slow server)

### 5.3 Core Web Vitals Guidance
**Note**: Crawl data alone cannot measure CWV (needs real user data or lab data). However, provide:
- **LCP risks**: Large pages, slow response times, heavy above-the-fold content
- **INP risks**: Heavy JavaScript (detected from SPA/framework signatures)
- **CLS risks**: Missing image dimensions (if detectable), dynamic content injection
- Platform-specific CWV advice (e.g. Shopify theme optimisation, WordPress plugin bloat)

### 5.4 Sustainability Metrics
**What to check** (if CO2 data available):
- CO2 per page distribution
- Carbon rating distribution
- Worst offending pages
- Estimated total site carbon footprint

---

## Category 6: Mobile & Rendering

### 6.1 Mobile Signals
**What to check**:
- Mobile alternate links present
- Responsive design indicators
- AMP implementation (if any)

### 6.2 JavaScript Rendering Concerns
**What to check**:
- Platform is SPA/headless (Next.js, React, Angular, Vue)
- Content dependent on JavaScript rendering
- If Firecrawl was used with JS rendering, compare rendered vs raw content

---

## Category 7: Structured Data & Schema

### 7.1 Schema Presence
**What to check** (if structured data columns available or parsed from HTML):
- Which pages have structured data
- Which schema types are present (Product, Article, FAQ, Organization, BreadcrumbList, etc.)
- Schema validation issues

### 7.2 Missing Schema Opportunities
**Platform and page-type specific recommendations**:
- **Ecommerce product pages**: Product, Offer, AggregateRating, Review, BreadcrumbList
- **Blog/article pages**: Article, Author, BreadcrumbList, FAQ, HowTo
- **Homepage**: Organization, WebSite with SearchAction
- **Local business**: LocalBusiness, OpeningHours
- **FAQ pages**: FAQ schema
- **Category pages**: CollectionPage, ItemList

### 7.3 Deprecated Schema Warnings
Flag use of schema types Google no longer supports for rich results (as of 2025-2026):
- HowTo (reduced rich result support)
- FAQ (limited to authoritative sources)

---

## Category 8: Security & Protocol

### 8.1 HTTPS Implementation
**What to check**:
- Any HTTP (non-HTTPS) pages in the crawl
- Mixed content (HTTPS pages linking to HTTP resources)
- HTTP to HTTPS redirect implementation

### 8.2 Security Headers
**What to check** (if header data available):
- HSTS present
- Content-Security-Policy
- X-Frame-Options
- X-Content-Type-Options

---

## Category 9: International SEO

### 9.1 Hreflang Audit
**What to check** (if hreflang data present):
- Hreflang return links (bidirectional linking)
- Hreflang pointing to non-indexable pages
- Missing x-default
- Language/region code validity
- Hreflang conflicts with canonical

### 9.2 Language Consistency
**What to check**:
- HTML lang attribute matches content language
- Consistent language across page elements

---

## Category 10: AI & Future Readiness

### 10.1 llms.txt
**What to check**:
- Presence of llms.txt in root directory
- Quality and completeness of llms.txt content

### 10.2 Content Extractability
**What to check**:
- Is key content in semantic HTML (article, main, section) vs generic divs?
- Is content available in initial HTML or only after JS execution?
- Are heading hierarchies logical and descriptive?

### 10.3 Structured Data Completeness
**What to check**:
- Are all entity types properly marked up?
- Is there enough structured data for AI to build knowledge graph entries?

---

## Running the Analysis

For each category, the analysis script (`scripts/analyse_crawl.py`) processes the normalised data and returns a structured findings object:

```python
{
    "category": "Crawlability & Accessibility",
    "category_id": 1,
    "health_score": 72,  # 0-100
    "checks": [
        {
            "check_id": "1.1",
            "check_name": "HTTP Status Code Distribution",
            "status": "warning",  # pass / warning / critical / info
            "summary": "3 pages returning 4xx errors",
            "affected_urls_count": 3,
            "affected_urls": ["https://example.com/old-page", ...],
            "details": { ... },  # Check-specific data
            "seo_impact": 6,
            "business_impact": 4,
            "fix_effort": 2,
            "priority_score": 5.6,
            "fix_instructions": "Set up 301 redirects for these broken URLs to their closest equivalent pages.",
            "platform_notes": "In Shopify, go to Settings > Navigation > URL Redirects to add these."
        }
    ]
}
```
