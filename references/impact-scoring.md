# Business Impact Scoring Reference

This document defines how every issue found during the audit is scored and prioritised based on actual business impact rather than abstract technical severity.

---

## The Three Scoring Dimensions

### 1. SEO Impact (1-10)

How much does this issue affect search engine visibility?

| Score | Meaning | Examples |
|---|---|---|
| 9-10 | Catastrophic: Prevents indexing or ranking entirely | Entire site noindexed, robots.txt blocking all crawlers, site-wide 5xx errors |
| 7-8 | Severe: Major ranking factor compromised | Key pages non-indexable, massive duplicate content, critical redirect loops |
| 5-6 | Significant: Clear negative ranking signal | Missing titles on important pages, orphan key pages, slow response times |
| 3-4 | Moderate: Suboptimal but not blocking | Missing meta descriptions, non-optimal URL structure, thin content on secondary pages |
| 1-2 | Minor: Best practice not followed | Missing alt text on decorative images, suboptimal heading hierarchy on blog posts |

### 2. Business Impact (1-10)

How much revenue, leads, or business value is at risk?

This dimension requires the context gathered in Phase 2 (site type, revenue pages, business model).

| Score | Meaning | How to Assess |
|---|---|---|
| 9-10 | Direct revenue loss | Issues affecting product pages, checkout flow, pricing pages, or top landing pages |
| 7-8 | High-value page degradation | Issues affecting category pages, key service pages, lead generation forms |
| 5-6 | Moderate traffic pages affected | Issues affecting mid-tier content, blog posts with decent traffic, about/trust pages |
| 3-4 | Supporting page issues | Issues on secondary content, older blog posts, resource pages |
| 1-2 | Minimal business relevance | Issues on legal pages, very old content, low-traffic utility pages |

**Page importance hierarchy** (default, adjust based on user context):

For ecommerce:
1. Homepage, checkout, cart
2. Product pages
3. Collection/category pages
4. Landing pages
5. Blog posts
6. Information pages (about, contact, policies)

For SaaS:
1. Homepage, pricing, sign-up flow
2. Feature/solution pages
3. Comparison/alternative pages
4. Blog posts (especially bottom-funnel)
5. Documentation
6. Information pages

For publishers/blogs:
1. Homepage
2. Top-traffic articles
3. Category/topic pages
4. Recent articles
5. Older content
6. Utility pages

### 3. Fix Effort (1-10, where 1 = easiest)

How much work is needed to resolve this issue?

| Score | Meaning | Examples |
|---|---|---|
| 1-2 | Quick fix, no developer needed | Add meta descriptions in CMS, update title tags, add alt text |
| 3-4 | Simple developer task or CMS config | Set up redirects, update robots.txt, add canonical tags |
| 5-6 | Moderate development work | Fix site architecture, implement schema markup, restructure URL patterns |
| 7-8 | Significant development project | Migrate URL structure, rebuild navigation, implement hreflang, fix rendering issues |
| 9-10 | Major platform/infrastructure change | Platform migration needed, complete redesign required, server infrastructure overhaul |

**Platform-adjusted effort scoring**:

The same fix can have very different effort levels depending on the platform:

| Fix | Shopify | WordPress | Custom |
|---|---|---|---|
| Add redirects | 2 (Admin UI) | 2 (plugin) | 4 (server config) |
| Edit meta titles | 2 (page editor) | 1 (Yoast/RankMath) | 3 (template code) |
| Add schema markup | 4 (app or theme) | 2 (plugin) | 5 (manual JSON-LD) |
| Fix robots.txt | 3 (limited control) | 2 (plugin/file) | 2 (direct file) |
| URL restructure | 8 (very limited) | 5 (permalinks + redirects) | 6 (rewrite rules) |
| Fix pagination | 7 (theme-dependent) | 3 (plugin) | 5 (custom code) |
| Add hreflang | 6 (app required) | 3 (plugin) | 5 (manual) |
| Core Web Vitals | 5 (theme-dependent) | 4 (plugin + optimisation) | 6 (performance audit) |

---

## Priority Score Calculation

```
Priority Score = (SEO Impact × 0.4) + (Business Impact × 0.4) + ((10 - Fix Effort) × 0.2)
```

The formula weights SEO and business impact equally (40% each), with a 20% bonus for ease of fixing. This naturally surfaces "quick wins" (high impact, low effort) while still prioritising the most impactful issues overall.

### Priority Bands

| Priority Score | Band | Recommended Timeline |
|---|---|---|
| 8.0 - 10.0 | Critical | Fix immediately (this week) |
| 6.0 - 7.9 | High | Fix within 2 weeks |
| 4.0 - 5.9 | Medium | Fix within 1 month |
| 2.0 - 3.9 | Low | Fix within quarter |
| 0.0 - 1.9 | Informational | Address when convenient |

---

## Quick Wins Identification

A "Quick Win" is any issue where:
- Priority Score >= 5.0 AND Fix Effort <= 3

These are the items that should be highlighted prominently because they offer the best return on time invested. Present them as a separate section in both the report and spreadsheet.

---

## Overall Health Score Calculation

The site-wide health score (0-100) is calculated per category and overall:

### Per-Category Score

```
Category Score = 100 - (sum of issue penalties in that category)
```

Where each issue penalty is:
- Critical issue: -15 points (minimum 5, maximum 15, scaled by affected URL percentage)
- High issue: -8 points
- Medium issue: -4 points
- Low issue: -1 point

Category score is clamped between 0 and 100.

### Overall Score

```
Overall Score = Weighted average of category scores
```

Category weights (reflecting relative importance to overall SEO health):

| Category | Weight |
|---|---|
| Crawlability & Accessibility | 20% |
| Indexability & Index Management | 20% |
| On-Page SEO Elements | 15% |
| Site Architecture & Internal Linking | 12% |
| Performance & Core Web Vitals | 12% |
| Mobile & Rendering | 5% |
| Structured Data & Schema | 5% |
| Security & Protocol | 5% |
| International SEO | 3% |
| AI & Future Readiness | 3% |

These weights shift based on context:
- For an international site, bump International SEO to 10% and reduce others proportionally
- For a headless/SPA site, bump Mobile & Rendering to 10%
- For ecommerce, bump Structured Data to 8% (product schema is critical)

---

## Score Interpretation Guide

Include this in the report so stakeholders understand what the numbers mean:

| Score Range | Rating | Interpretation |
|---|---|---|
| 90-100 | Excellent | Site is technically very well optimised. Focus on maintaining and fine-tuning. |
| 75-89 | Good | Solid foundation with some areas for improvement. Address high-priority items. |
| 60-74 | Needs Work | Multiple significant issues holding back performance. Prioritised action plan needed. |
| 40-59 | Poor | Serious technical debt affecting visibility. Urgent remediation required. |
| 0-39 | Critical | Fundamental technical issues preventing proper indexing. Immediate intervention needed. |

---

## Contextual Adjustments

The scoring system adjusts based on Phase 2 context:

### Scale Adjustment
For very large sites (> 10,000 pages), issues affecting < 1% of pages get their SEO Impact reduced by 2 points (minimum 1). The logic: 50 broken links on a 100-page site is 50% of the site (critical), but 50 broken links on a 50,000-page site is 0.1% (much less critical).

### Revenue Page Boost
Any issue affecting pages the user identified as revenue-critical gets a +2 boost to Business Impact (capped at 10).

### Seasonal Adjustment
If the user mentions upcoming peak periods (Black Friday, product launch, etc.), time-sensitive fixes get a +1 boost to Business Impact.
