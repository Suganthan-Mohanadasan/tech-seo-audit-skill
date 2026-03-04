# Technical SEO Audit Skill for Claude

An open source skill for [Claude](https://claude.ai) (Anthropic's AI) that transforms raw crawl data from any SEO tool into a fully prioritised, business impact scored audit report and actionable spreadsheet.

Built and maintained by [Snippet Digital](https://snippet.digital), a specialist SEO agency based in the West Midlands, UK.

## What It Does

This skill sits on top of whatever crawl data you already have (Screaming Frog, Sitebulb, Firecrawl, Ahrefs Site Audit, or any CSV with URL and status data) and handles the analysis, prioritisation, and reporting that typically takes hours of manual work.

Specifically, it:

1. **Auto detects your crawl tool** and normalises column formats into a standard schema
2. **Identifies your platform** (WordPress, Shopify, Magento, custom) and site type automatically
3. **Runs analysis across 10 audit categories**: crawlability, indexability, on page elements, site architecture, performance, mobile readiness, structured data, security, international SEO, and AI/future readiness
4. **Scores every issue on three dimensions**: SEO Impact (1 to 10), Business Impact (1 to 10), and Fix Effort (1 to 10)
5. **Generates two deliverables**: a comprehensive Markdown report with executive summary and strategic recommendations, plus an XLSX spreadsheet with every issue, priority score, affected URLs, and an implementation timeline

The priority scoring formula ensures high impact, easy to fix issues surface first:

```
Priority Score = (SEO Impact x 0.4) + (Business Impact x 0.4) + ((10 - Fix Effort) x 0.2)
```

## Installation

### Option A: Claude Desktop (Cowork Mode)

This is the simplest route for most users.

1. Download this repository as a ZIP (click **Code > Download ZIP** above)
2. Extract the ZIP file
3. Open Claude Desktop and switch to **Cowork mode**
4. Select a working folder on your machine
5. Copy the `technical-seo-audit` folder (the one containing `SKILL.md`) into the `.skills/skills/` directory inside your selected working folder:

```
your-selected-folder/
└── .skills/
    └── skills/
        └── technical-seo-audit/
            ├── SKILL.md
            ├── references/
            │   ├── analysis-modules.md
            │   ├── impact-scoring.md
            │   ├── api-crawling.md
            │   └── data-ingestion.md
            └── scripts/
                └── analyse_crawl.py
```

The `.skills` folder may be hidden by default. On macOS, press `Cmd + Shift + .` in Finder to reveal hidden folders. On Windows, enable "Show hidden items" in File Explorer's View tab.

6. Start a new conversation and say: "Run a technical SEO audit on [your domain]"

### Option B: Claude Code CLI

For developers who prefer working in the terminal.

```bash
# Clone the repository
git clone https://github.com/Suganthan-Mohanadasan/tech-seo-audit-skill.git

# Project level installation
mkdir -p .claude/skills/technical-seo-audit
cp -r technical-seo-audit-skill/* .claude/skills/technical-seo-audit/

# Or global installation (available across all projects)
mkdir -p ~/.claude/skills/technical-seo-audit
cp -r technical-seo-audit-skill/* ~/.claude/skills/technical-seo-audit/
```

Then launch Claude Code and type: "Run a technical SEO audit"

### Optional: API Access

To pull supplementary data from Ahrefs or DataForSEO, set environment variables:

```bash
export AHREFS_API_KEY="your_ahrefs_api_key_here"
export DATAFORSEO_LOGIN="your_login_here"
export DATAFORSEO_PASSWORD="your_password_here"
```

## Supported Crawl Tools

| Tool | Typical Files | Auto Detected |
|------|--------------|---------------|
| Screaming Frog | `internal_html.csv`, `internal_all.csv` | Yes |
| Sitebulb | `urls.csv`, `links.csv`, `hints.csv` | Yes |
| Ahrefs Site Audit | `pages.csv`, `issues.csv` | Yes |
| Firecrawl | API response (JSON/Markdown) | Yes |
| Generic CSV | Any CSV with URL + status columns | Yes (header matching) |

## Audit Categories

The skill analyses your site across 10 categories:

1. **Crawlability and Accessibility**: Robots.txt, XML sitemaps, status codes, redirects, crawl depth, orphan pages
2. **Indexability and Index Management**: Canonical tags, meta robots, pagination, duplicate content
3. **On Page SEO Elements**: Titles, meta descriptions, heading hierarchy, content quality, internal linking, image optimisation
4. **Site Architecture and Internal Linking**: Depth analysis, click depth, navigation structure, content silos
5. **Performance and Core Web Vitals**: Page size, response times, resource optimisation
6. **Mobile and Rendering**: Responsive signals, viewport, JavaScript rendering
7. **Structured Data and Schema**: Schema presence, missing opportunities by page type
8. **Security and Protocol**: HTTPS, mixed content, security headers
9. **International SEO**: Hreflang, language targeting
10. **AI and Future Readiness**: llms.txt, content extractability, semantic HTML

## Output

The skill produces two deliverables:

1. **Markdown Report**: Executive summary, health score breakdown, categorised findings (Critical/High/Medium/Low), quick wins, and strategic recommendations
2. **XLSX Spreadsheet**: Executive dashboard, all issues with priority scores, quick wins tab, and a week by week action plan

## Example

We ran this skill against a live client site and it identified 20 issues across all categories, including a canonical tag misconfiguration on a high traffic page that was actively suppressing rankings. The entire audit, from data gathering to finished deliverables, took under 10 minutes.

Read the full write up: [We Open Sourced Our Technical SEO Audit Process](https://snippet.digital/blog/technical-seo-audit-ai-process/)

## Repository Structure

```
technical-seo-audit-skill/
├── README.md
├── LICENCE
├── .gitignore
├── SKILL.md                          # Main skill instructions
├── references/
│   ├── analysis-modules.md           # Detailed check specifications for all 10 categories
│   ├── impact-scoring.md             # Business impact scoring methodology
│   ├── api-crawling.md               # API integration documentation
│   └── data-ingestion.md             # Column mapping and normalisation logic
├── scripts/
│   └── analyse_crawl.py              # Automated crawl data processing
├── examples/
│   ├── ukmodels-technical-seo-audit.md    # Example audit report
│   └── ukmodels-technical-seo-audit.xlsx  # Example audit spreadsheet
└── blog/
    └── technical-seo-audit-ai-blog-post.md  # Companion blog post
```

## Contributing

Contributions, feedback, and feature requests are welcome. Please open an issue or submit a pull request.

## Licence

MIT Licence. See [LICENCE](LICENCE) for details.

## About Snippet Digital

[Snippet Digital](https://snippet.digital) is a specialist SEO agency focused on technical SEO, link audits, and reputation management. We have been integrating AI into our workflows since 2024 and are committed to sharing tools and methodologies that push the industry forward.

[Get in touch](https://snippet.digital/contact/) if you would like us to run a technical SEO audit for your site.
