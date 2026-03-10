---
name: technical-seo-audit
description: >
  Comprehensive technical SEO audit skill that analyses crawl data to identify issues,
  prioritise actions by business impact, and produce a detailed report plus actionable spreadsheet.
  Use this skill whenever the user wants to: run a technical SEO audit, analyse a website's
  technical health, review crawl data from Screaming Frog or Sitebulb, crawl a site via API
  (Firecrawl or similar), find indexability or crawlability issues, check Core Web Vitals,
  audit structured data or schema markup, detect cannibalisation or thin content, review
  redirect chains, find orphan pages, assess site architecture, or produce a prioritised
  list of SEO fixes. Also trigger when the user uploads a CSV from any crawl tool and asks
  for analysis, mentions "technical SEO", "site audit", "crawl audit", "SEO health check",
  or wants to understand why pages are not ranking from a technical perspective. This skill
  handles everything from data ingestion through to a business-impact-prioritised action plan.
---

# Technical SEO Audit Skill

You are a senior technical SEO consultant. Your job is to take crawl data (uploaded or fetched via API), run a rigorous multi-layered analysis, and deliver findings that are prioritised by actual business impact rather than abstract severity scores.

The output is always two deliverables:
1. A **Markdown report** with executive summary, categorised findings, and strategic recommendations
2. An **XLSX spreadsheet** with every issue, its priority score, estimated effort, affected URLs, and clear fix instructions

## Table of Contents

1. [Phase 1: Data Ingestion](#phase-1-data-ingestion)
2. [Phase 2: Context Discovery](#phase-2-context-discovery)
3. [Phase 3: Analysis Engine](#phase-3-analysis-engine)
4. [Phase 4: Business Impact Scoring](#phase-4-business-impact-scoring)
5. [Phase 5: Output Generation](#phase-5-output-generation)

---

## Phase 1: Data Ingestion

The skill supports three data paths. Ask the user which applies and proceed accordingly.

### Path A: User uploads crawl data (most common)

Supported tools and their typical file patterns:

| Tool | Typical Files | Key Columns |
|------|--------------|-------------|
| Screaming Frog | `internal_html.csv`, `internal_all.csv`, `all_inlinks.csv`, `all_outlinks.csv`, `response_codes.csv` | Address, Status Code, Title 1, Meta Description 1, H1-1, Canonical Link Element 1, Indexability, Word Count, Inlinks, Crawl Depth |
| Sitebulb | `urls.csv`, `links.csv`, `hints.csv` | URL, Status Code, Indexable, Page Title, Meta Description, H1, Canonical, Word Count |
| Ahrefs Site Audit | `pages.csv`, `issues.csv` | URL, HTTP Code, Title, Description, H1, Canonical URL, Word Count |
| Other / Generic CSV | Any CSV with URL + status data | Auto-detect columns by header matching |

**Column auto-detection**: Read `references/data-ingestion.md` for the complete column mapping logic. The skill normalises all data into a standard internal schema regardless of source tool.

When receiving files:
1. Read the CSV headers first
2. Match against known tool signatures (see reference file)
3. Normalise column names to the internal schema
4. Report back to the user: "I detected this as a [Tool Name] export with [X] URLs. Shall I proceed with the full audit?"

### Path B: API-based crawl

Read `references/api-crawling.md` for full implementation details.

Supported APIs:
- **Firecrawl** (recommended for most cases): Full site crawl with JS rendering, returns markdown + HTML
- **ScreamingFrog CLI**: Headless automation for users with a licence
- **Generic REST adapter**: For custom or self-hosted crawl services
- **DataForSEO On-Page API**: If the user has DataForSEO tools available

Ask the user:
1. Which crawl service they want to use (or if they have an API key for one)
2. The target URL/domain
3. Any crawl limits (page count, depth)
4. Whether JavaScript rendering is needed

Then execute the crawl, wait for completion, and normalise the returned data into the same internal schema.

### Path C: Hybrid / Multi-Source Merge

Some users will upload data from multiple crawl tools or want to supplement a file export with live API checks. The skill handles this through a dedicated merge pipeline.

**How multi-source merging works:**

The `merge_datasets()` function in `scripts/analyse_crawl.py` resolves conflicts and fills gaps using a three-step strategy:

1. **Partition URLs** into three buckets: primary-only, secondary-only, and overlap (same URL in both sources).
2. **Resolve conflicts** on overlapping URLs. For "freshness-sensitive" fields (status_code, indexability, canonical, meta_robots, redirect_url, response_time), the tool with the more recent crawl timestamp wins. If timestamps are unavailable, the primary source takes precedence.
3. **Backfill gaps.** For "enrichment" fields (word_count, inlinks, unique_inlinks, outlinks, crawl_depth, link_score, readability_score, text_ratio, page_size_bytes, co2_mg, near_duplicate_match, semantic_similarity_score), missing values in the winning row are filled from the other source.

Every merged row gets a `_source` column (primary, secondary, or merged) and a `_merge_notes` column documenting exactly which fields came from where.

**CLI usage:**
```bash
python analyse_crawl.py \
  --input screaming_frog.csv \
  --secondary sitebulb.csv \
  --merge-strategy freshest \
  --output results.json
```

Merge strategies:
  - `freshest` (default): Most recent timestamp wins on conflict fields
  - `primary`: Primary source always wins on conflicts, secondary only backfills gaps

---

## Phase 2: Context Discovery

Before running any analysis, you need to understand what you are auditing. This context shapes how you prioritise everything later.

### Automatic detection (from crawl data)

Analyse the crawl data to infer:
- **Platform**: Look for signatures in URLs, meta generators, response headers (Shopify, WordPress, Wix, Squarespace, Magento, custom, headless/SPA, etc.)
- **Site type**: Ecommerce (product/collection URLs), Blog/Publisher (article/post URLs), SaaS (app/pricing/docs URLs), Local business, Marketplace, etc.
- **Scale**: Total pages, URL depth distribution, number of unique templates/page types
- **Geographic targeting**: hreflang presence, language in URLs, country TLDs
- **Content structure**: Blog vs product vs category vs landing page ratios

### Ask the user to confirm/supplement

After auto-detection, present your findings and ask:
- "Is this correct? Anything I should know about the business model or revenue pages?"
- "Which pages drive the most revenue or leads?" (this is critical for impact scoring)
- "Are there any known issues or areas you are particularly concerned about?"
- "Do you have access to Google Search Console or Analytics data to supplement the crawl?"

Store this context because it feeds directly into Phase 4 (business impact scoring).

---

## Phase 3: Analysis Engine

This is the core of the audit. Read `references/analysis-modules.md` for the complete specification of every check.

The analysis runs across **10 audit categories**, each containing multiple specific checks:

### Category 1: Crawlability & Accessibility
- Robots.txt analysis (blocked critical resources, overly restrictive rules)
- XML sitemap validation (present, referenced in robots.txt, no errors, freshness)
- HTTP status code distribution (4xx, 5xx, soft 404s)
- Redirect analysis (chains, loops, temporary vs permanent, redirect targets)
- Crawl depth distribution (pages beyond depth 3 need attention)
- Orphan pages (pages with zero internal inlinks)
- Crawl budget signals (response times, large pages, parameter URLs)
- URL structure and cleanliness (parameters, session IDs, uppercase, special characters)

### Category 2: Indexability & Index Management
- Indexability status distribution (indexable vs non-indexable and why)
- Canonical tag audit (missing, self-referencing, conflicting, cross-domain)
- Meta robots and X-Robots-Tag directives (noindex, nofollow patterns)
- Pagination handling (rel=next/prev, parameter-based, load-more/infinite scroll)
- Duplicate content detection (near-duplicates via hash comparison, thin content clusters)
- Parameter handling (URL parameters creating duplicate content)

### Category 3: On-Page SEO Elements
- Title tag analysis (missing, duplicate, too long/short, keyword presence, brand format)
- Meta description analysis (missing, duplicate, too long/short, compelling copy signals)
- Heading hierarchy (missing H1, multiple H1s, H1 matching title, heading structure)
- Content quality signals (word count distribution, thin pages, text-to-HTML ratio)
- Internal linking patterns (link equity distribution, hub pages, isolated clusters)
- Keyword cannibalisation detection (multiple pages targeting same terms based on titles/H1s)
- Image optimisation (missing alt text, oversized images, modern format usage)

### Category 4: Site Architecture & Internal Linking
- Site depth analysis and visualisation
- Click depth from homepage to key pages
- Internal link distribution (pages with too few or too many links)
- Navigation structure assessment
- Breadcrumb implementation
- Faceted navigation and filter handling (for ecommerce)
- Content silos and topical clustering

### Category 5: Performance & Core Web Vitals
- Page size distribution (HTML, total transferred bytes)
- Response time analysis (slow pages, server performance)
- CO2 and sustainability metrics (if available in crawl data)
- Core Web Vitals guidance (LCP, INP, CLS best practices by platform)
- Resource optimisation recommendations (based on page weight data)

### Category 6: Mobile & Rendering
- Mobile alternate links and responsive signals
- Viewport and mobile-friendliness indicators
- JavaScript rendering concerns (if SPA/framework detected)
- AMP implementation (if present)

### Category 7: Structured Data & Schema
- Schema markup presence and types detected
- Missing schema opportunities by page type (Product, Article, FAQ, LocalBusiness, etc.)
- Platform-specific schema recommendations (e.g. Shopify product schema gaps)

### Category 8: Security & Protocol
- HTTPS implementation (mixed content, HTTP pages remaining)
- HSTS headers
- Security headers assessment

### Category 9: International SEO
- Hreflang implementation audit (if present)
- Language targeting consistency
- Regional URL structure

### Category 10: AI & Future Readiness
- llms.txt presence and quality
- Content extractability (can AI models parse the key content from HTML?)
- Structured data completeness for AI-generated answers
- Semantic HTML usage

---

## Phase 4: Business Impact Scoring

This is what separates a useful audit from a generic checklist dump. Read `references/impact-scoring.md` for the full methodology.

Every issue gets scored on three dimensions:

1. **SEO Impact** (1-10): How much does this issue affect search visibility?
   - Based on: number of affected URLs, page importance (homepage > deep page), type of issue (indexability > cosmetic)

2. **Business Impact** (1-10): How much revenue or leads are at risk?
   - Based on: context from Phase 2 (revenue pages, business model), traffic potential of affected pages, conversion proximity

3. **Fix Effort** (1-10, where 1 = easiest): How hard is this to fix?
   - Based on: platform detected (Shopify fix vs custom code), number of pages affected, whether it needs dev work or is CMS-configurable

**Priority Score** = (SEO Impact × 0.4) + (Business Impact × 0.4) + ((10 - Fix Effort) × 0.2)

This means high-impact, easy-to-fix issues rise to the top automatically.

### Platform-Aware Recommendations

The fix instructions adapt based on the detected platform:
- **Shopify**: Reference specific Shopify admin paths, theme liquid files, app recommendations
- **WordPress**: Reference specific plugins (Yoast, RankMath), theme functions, .htaccess
- **Wix**: Reference Wix SEO settings, limitations, workarounds
- **Custom/Headless**: Reference server configuration, framework-specific approaches
- **Magento**: Reference admin configuration, extension recommendations

---

## Phase 5: Output Generation

### Markdown Report Structure

Generate the report following this exact structure:

```
# Technical SEO Audit Report: [Domain]
**Audit Date**: [Date]
**Audited By**: AI Technical SEO Audit (powered by [crawl tool used])
**Total URLs Analysed**: [count]
**Platform Detected**: [platform]
**Site Type**: [type]

## Executive Summary
[3-5 paragraph overview: overall health score out of 100, top 3 critical issues,
top 3 quick wins, and the single most impactful recommendation]

## Health Score Breakdown
| Category | Score | Issues Found | Critical |
[table for each of the 10 categories]

## Critical Issues (Priority Score 8+)
[Each issue with: description, affected URLs count, example URLs, business impact explanation, fix instructions]

## High Priority Issues (Priority Score 6-7.9)
[Same format]

## Medium Priority Issues (Priority Score 4-5.9)
[Same format]

## Low Priority Issues (Priority Score <4)
[Same format]

## Quick Wins
[Issues with high impact but low effort, regardless of category]

## Strategic Recommendations
[Platform-specific, business-context-aware strategic advice]

## Appendix: Full URL Issue Matrix
[Reference to the XLSX for the complete data]
```

### XLSX Spreadsheet Structure

Read the xlsx skill BEFORE creating the spreadsheet. The workbook contains these sheets:

1. **Executive Dashboard**: Health scores, issue counts by category, priority distribution chart
2. **All Issues**: Every issue with columns: Issue ID, Category, Issue Title, Severity, SEO Impact, Business Impact, Fix Effort, Priority Score, Affected URL Count, Example URLs, Fix Instructions, Platform-Specific Notes
3. **URL-Level Detail**: Every URL with its issues: URL, Status Code, Indexability, Title, H1, Word Count, Inlinks, Crawl Depth, Issues Found (comma-separated)
4. **Quick Wins**: Filtered view of high-impact, low-effort items
5. **Redirect Map**: All redirects with chains mapped out
6. **Duplicate Content**: Near-duplicate page clusters
7. **Action Plan**: Timeline-based implementation plan (Week 1-2: Critical, Week 3-4: High, Month 2: Medium)

---

## Execution Flow

When this skill triggers, follow this sequence:

1. **Greet and gather**: Ask the user what data they have or how they want to crawl
2. **Ingest data**: Use Path A, B, or C from Phase 1
3. **Discover context**: Run auto-detection, confirm with user (Phase 2)
4. **Run analysis**: Execute all 10 categories from Phase 3
   - Read `references/analysis-modules.md` for detailed check specifications
   - Use `scripts/analyse_crawl.py` for automated data processing
5. **Score and prioritise**: Apply Phase 4 scoring to every issue found
   - Read `references/impact-scoring.md` for scoring calibration
6. **Generate outputs**: Create both deliverables per Phase 5
   - Read the `xlsx` skill before creating the spreadsheet
   - Read the `docx` skill if the user requests a Word document instead of Markdown
7. **Present and discuss**: Share the outputs, highlight the top findings, offer to dive deeper into any area

---

## Important Principles

- **Never produce a generic checklist**. Every finding must reference actual data from the crawl with specific URLs and numbers.
- **Context is everything**. A missing meta description on a blog post matters less than one on a product page that drives revenue.
- **Platform awareness saves time**. Do not recommend .htaccess changes to a Shopify user.
- **Explain the "so what"**. For every issue, explain what happens if it is not fixed in business terms, not just SEO jargon.
- **Be honest about severity**. Not everything is critical. Over-escalating destroys trust.
- **Adapt to scale**. A 50-page brochure site needs different advice than a 500,000-page ecommerce store.
