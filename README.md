# Technical SEO Audit Skill

A comprehensive technical SEO audit skill that analyses crawl data, identifies issues across 10 audit categories, prioritises findings by actual business impact, and produces a detailed Markdown report alongside an actionable XLSX spreadsheet.

## What It Does

This skill takes crawl data from any major SEO tool (or fetches it live via API) and runs a full technical audit. Unlike generic audit checklists, every issue is scored against three dimensions: SEO impact, business impact, and fix effort. The result is a prioritised action plan that surfaces quick wins and high value fixes first, tailored to the specific platform and business model.

## Directory Structure

```
technical-seo-audit/
  SKILL.md                          Core skill instructions (the brain)
  README.md                         This file
  references/
    data-ingestion.md               Column mappings, schema, tool detection
    analysis-modules.md             All 10 audit categories and their checks
    impact-scoring.md               Business impact scoring methodology
    api-crawling.md                 Firecrawl, SF CLI, DataForSEO integration
  scripts/
    analyse_crawl.py                Python analysis engine (1,295 lines)
  assets/                           Reserved for templates and output assets
```

## Supported Data Sources

### File Uploads (Path A)

The skill auto-detects the source tool from CSV headers and normalises columns into a standard internal schema.

| Tool             | Typical Files                      |
|------------------|------------------------------------|
| Screaming Frog   | internal_html.csv, internal_all.csv |
| Sitebulb         | urls.csv                           |
| Ahrefs Site Audit| pages.csv                          |
| Generic CSV      | Any CSV with URL + status columns  |

### API Crawling (Path B)

For sites without existing crawl data, the skill can fetch data live.

| API              | Notes                                         |
|------------------|-----------------------------------------------|
| Firecrawl        | Recommended. Full JS rendering, clean output  |
| ScreamingFrog CLI| Requires local licence and CLI access         |
| DataForSEO       | Per-page on-page analysis via MCP tools       |
| Generic REST     | Extensible adapter pattern for custom crawlers|

### Multi-Source Merge (Path C)

When data from two sources is available, the merge pipeline resolves conflicts using a freshness-first strategy and backfills gaps from the secondary source. Every merged row is tagged with provenance metadata so you always know where the data came from.

```bash
python scripts/analyse_crawl.py \
  --input screaming_frog.csv \
  --secondary sitebulb.csv \
  --merge-strategy freshest \
  --output results.json
```

## The 10 Audit Categories

1. **Crawlability and Accessibility** : Status codes, redirects (chains, loops), crawl depth, orphan pages, URL structure, response times, robots.txt, XML sitemaps
2. **Indexability and Index Management** : Indexability distribution, canonical audit, meta robots directives, pagination, duplicate content
3. **On-Page SEO Elements** : Title tags, meta descriptions, heading hierarchy, content quality, keyword cannibalisation, image optimisation
4. **Site Architecture and Internal Linking** : Link distribution, content silos, navigation assessment, breadcrumbs, faceted navigation
5. **Performance and Core Web Vitals** : Page weight, response times, CWV guidance (LCP, INP, CLS), sustainability metrics
6. **Mobile and Rendering** : Mobile signals, viewport, JS rendering concerns, AMP
7. **Structured Data and Schema** : Schema presence, missing opportunities by page type, deprecated schema warnings
8. **Security and Protocol** : HTTPS implementation, mixed content, security headers
9. **International SEO** : Hreflang audit, language consistency, regional URL structure
10. **AI and Future Readiness** : llms.txt, content extractability, semantic HTML, structured data completeness

## Business Impact Scoring

Every issue is scored on three dimensions:

| Dimension       | Weight | What It Measures                          |
|-----------------|--------|-------------------------------------------|
| SEO Impact      | 40%    | Effect on search engine visibility        |
| Business Impact | 40%    | Revenue, leads, or business value at risk |
| Fix Effort      | 20%    | Inverse of effort (easy fixes score higher)|

**Priority Score** = (SEO Impact x 0.4) + (Business Impact x 0.4) + ((10 minus Fix Effort) x 0.2)

Priority bands:

| Score     | Band          | Timeline              |
|-----------|---------------|-----------------------|
| 8.0+      | Critical      | Fix this week         |
| 6.0 to 7.9| High         | Fix within 2 weeks    |
| 4.0 to 5.9| Medium       | Fix within 1 month    |
| 2.0 to 3.9| Low          | Fix within quarter    |
| Below 2.0 | Informational | Address when convenient|

Fix effort scores are calibrated per platform (e.g. adding redirects is effort 2 on Shopify, effort 4 on a custom build).

## Platform Awareness

The skill auto-detects the CMS or framework from URL patterns and meta signatures, then tailors every recommendation accordingly.

| Platform    | Detection Signals                              |
|-------------|------------------------------------------------|
| Shopify     | /collections/, /products/, cdn.shopify.com     |
| WordPress   | /wp-content/, /wp-admin/, /wp-json/            |
| Wix         | wixsite.com, static.wixstatic.com              |
| Squarespace | squarespace.com, /s/                           |
| Magento     | /catalog/product/, /checkout/cart/              |
| Next.js     | /_next/, __next data attributes                |
| Custom      | No known signatures matched                    |

## Output Deliverables

### Markdown Report

A structured report containing: executive summary with overall health score, category-by-category health breakdown, issues grouped by priority band, a dedicated quick wins section, strategic recommendations, and an appendix referencing the spreadsheet.

### XLSX Spreadsheet (7 sheets)

1. **Executive Dashboard** : Health scores, issue counts, priority distribution
2. **All Issues** : Every issue with scores, affected URL counts, fix instructions
3. **URL-Level Detail** : Per-URL data with all associated issues
4. **Quick Wins** : High impact, low effort items filtered for fast action
5. **Redirect Map** : All redirects with chains mapped out
6. **Duplicate Content** : Near-duplicate page clusters
7. **Action Plan** : Timeline-based implementation roadmap

## Running the Analysis Script Directly

```bash
# Single source
python scripts/analyse_crawl.py \
  --input path/to/crawl_data.csv \
  --output results.json \
  --platform shopify

# Multi-source merge
python scripts/analyse_crawl.py \
  --input primary.csv \
  --secondary secondary.csv \
  --merge-strategy freshest \
  --output results.json
```

The script outputs a JSON file containing all findings, health scores, and issue details which the skill then uses to generate the report and spreadsheet.

## Dependencies

The analysis script requires:

| Package         | Purpose                              |
|-----------------|--------------------------------------|
| pandas          | Data processing and analysis         |
| openpyxl        | XLSX generation (used by pandas)     |
| beautifulsoup4  | HTML parsing for API crawl data      |
| firecrawl-py    | Firecrawl API integration (optional) |

Install with:
```bash
pip install pandas openpyxl beautifulsoup4 firecrawl-py --break-system-packages
```

## How the Skill Triggers

The skill activates when a user mentions any of the following: technical SEO audit, site audit, crawl audit, SEO health check, crawlability issues, indexability problems, redirect chains, orphan pages, duplicate content, site architecture review, Core Web Vitals, structured data audit, or uploads a CSV from any crawl tool and asks for analysis.

## Version History

| Date       | Change                                                    |
|------------|-----------------------------------------------------------|
| 2026-03-04 | Initial skill creation with full 10-category audit engine |
| 2026-03-10 | Added multi-source merge pipeline with freshness-first conflict resolution and backfill strategy |
