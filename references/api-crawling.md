# API-Based Crawling Reference

This reference covers how to use external crawl APIs to gather site data when the user does not have a pre-existing crawl file.

---

## Firecrawl Integration

Firecrawl is the recommended API for live crawling. It handles JavaScript rendering, respects robots.txt, and returns clean data.

### Prerequisites
- Firecrawl API key (user must provide or have in environment as `FIRECRAWL_API_KEY`)
- Python with `firecrawl-py` package (`pip install firecrawl-py --break-system-packages`)

### Basic Crawl Implementation

```python
from firecrawl import FirecrawlApp
import json
import time

def crawl_site(api_key, target_url, max_pages=100, max_depth=3):
    """
    Crawl a website using Firecrawl API.

    Args:
        api_key: Firecrawl API key
        target_url: Starting URL to crawl
        max_pages: Maximum number of pages to crawl (each page = 1 credit)
        max_depth: Maximum crawl depth from starting URL

    Returns:
        list of page data dicts normalised to internal schema
    """
    app = FirecrawlApp(api_key=api_key)

    # Start the crawl
    crawl_result = app.crawl_url(
        target_url,
        params={
            'limit': max_pages,
            'maxDepth': max_depth,
            'scrapeOptions': {
                'formats': ['markdown', 'html'],
                'includeTags': ['title', 'meta', 'h1', 'h2', 'h3', 'link', 'a'],
            }
        },
        poll_interval=5  # Check every 5 seconds
    )

    return crawl_result

def normalise_firecrawl_data(crawl_result):
    """
    Convert Firecrawl response to internal schema format.
    """
    from bs4 import BeautifulSoup

    pages = []
    for page in crawl_result.get('data', []):
        metadata = page.get('metadata', {})
        html = page.get('html', '')
        markdown = page.get('markdown', '')

        # Parse HTML for additional fields
        soup = BeautifulSoup(html, 'html.parser') if html else None

        row = {
            'url': metadata.get('sourceURL', ''),
            'status_code': metadata.get('statusCode', 200),
            'title': metadata.get('title', ''),
            'meta_description': metadata.get('description', ''),
            'language': metadata.get('language', ''),
            'content_type': 'text/html',
        }

        if soup:
            # Extract H1
            h1_tag = soup.find('h1')
            row['h1'] = h1_tag.get_text(strip=True) if h1_tag else ''

            # Extract H2
            h2_tag = soup.find('h2')
            row['h2'] = h2_tag.get_text(strip=True) if h2_tag else ''

            # Extract canonical
            canonical_tag = soup.find('link', rel='canonical')
            row['canonical'] = canonical_tag.get('href', '') if canonical_tag else ''

            # Extract meta robots
            robots_tag = soup.find('meta', attrs={'name': 'robots'})
            row['meta_robots'] = robots_tag.get('content', '') if robots_tag else ''

            # Page size
            row['page_size_bytes'] = len(html.encode('utf-8'))

            # Word count from markdown (more accurate than HTML)
            row['word_count'] = len(markdown.split()) if markdown else 0

            # Text ratio
            text_content = soup.get_text()
            text_bytes = len(text_content.encode('utf-8'))
            html_bytes = len(html.encode('utf-8'))
            row['text_ratio'] = round((text_bytes / html_bytes) * 100, 3) if html_bytes > 0 else 0

            # Count internal links
            links = page.get('links', [])
            domain = row['url'].split('/')[2] if '/' in row['url'] else ''
            row['inlinks'] = 0  # Will be calculated in post-processing
            row['outlinks'] = len(links)
            row['external_outlinks'] = sum(1 for l in links if domain not in l)

            # Extract hreflang
            hreflang_tags = soup.find_all('link', rel='alternate', hreflang=True)
            row['hreflang_count'] = len(hreflang_tags)

            # Extract structured data
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            row['structured_data_count'] = len(json_ld_scripts)
            if json_ld_scripts:
                try:
                    schemas = []
                    for script in json_ld_scripts:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            schemas.append(data.get('@type', 'Unknown'))
                        elif isinstance(data, list):
                            for item in data:
                                schemas.append(item.get('@type', 'Unknown'))
                    row['structured_data_types'] = ', '.join(schemas)
                except (json.JSONDecodeError, AttributeError):
                    row['structured_data_types'] = ''

        pages.append(row)

    # Post-process: calculate inlinks
    url_set = {p['url'] for p in pages}
    inlink_counts = {url: 0 for url in url_set}
    for page in crawl_result.get('data', []):
        for link in page.get('links', []):
            if link in inlink_counts:
                inlink_counts[link] += 1

    for page_row in pages:
        page_row['inlinks'] = inlink_counts.get(page_row['url'], 0)

    return pages
```

### Crawl Configuration Guide

| Site Size | max_pages | max_depth | Estimated Credits | Estimated Time |
|---|---|---|---|---|
| Small (< 50 pages) | 100 | 4 | ~50-100 | 2-5 min |
| Medium (50-500 pages) | 500 | 4 | ~200-500 | 5-15 min |
| Large (500-5000 pages) | 2000 | 5 | ~1000-2000 | 15-45 min |
| Enterprise (5000+ pages) | 5000 | 5 | ~3000-5000 | 45-120 min |

Always confirm with the user before starting large crawls due to credit consumption.

### Rate Limiting and Error Handling

Firecrawl handles rate limiting internally, but if you encounter issues:
- 429 errors: Wait and retry with exponential backoff
- Timeout: Increase poll_interval for large sites
- Partial results: Firecrawl returns partial data if crawl is interrupted; use what is available

---

## ScreamingFrog CLI Integration

For users with a Screaming Frog licence, the CLI allows headless crawling.

### Prerequisites
- Screaming Frog installed locally
- Valid licence
- CLI access configured

### Usage

```bash
# Basic crawl with CSV export
screamingfrogseospider --crawl https://example.com \
  --headless \
  --save-crawl \
  --export-tabs "Internal:HTML" \
  --output-folder /path/to/output/
```

After the crawl completes, the exported CSV files follow the standard Screaming Frog format and can be ingested using Path A (file upload) column mappings.

---

## DataForSEO On-Page API

If the user has DataForSEO tools available in the environment, use the `instant_pages` tool:

```python
# Using the DataForSEO MCP tool
result = instant_pages(url="https://example.com")
```

This provides on-page metrics for a single URL. For full site audits, iterate over a URL list (obtained from sitemap or another source).

---

## Generic REST Adapter Pattern

For users with custom or self-hosted crawl services, provide this adapter interface:

```python
class CrawlAdapter:
    """Base adapter for any crawl API."""

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url

    def start_crawl(self, target_url, options=None):
        """Start a crawl job. Returns a job ID."""
        raise NotImplementedError

    def get_status(self, job_id):
        """Check crawl job status. Returns 'running', 'complete', or 'failed'."""
        raise NotImplementedError

    def get_results(self, job_id):
        """Get crawl results. Returns list of page data dicts."""
        raise NotImplementedError

    def normalise(self, raw_data):
        """Convert API-specific data to internal schema."""
        raise NotImplementedError
```

The user can extend this pattern for any crawl service they use. The key requirement is that the `normalise` method outputs data matching the internal schema defined in `data-ingestion.md`.

---

## Post-Crawl Enrichment

After the initial crawl (regardless of method), optionally enrich the data:

1. **Robots.txt fetch**: `GET {domain}/robots.txt` to check directives
2. **Sitemap fetch**: `GET {domain}/sitemap.xml` (and any referenced sitemaps) to cross-reference crawled vs listed URLs
3. **llms.txt check**: `GET {domain}/llms.txt` for AI readiness assessment
4. **Search Console data**: If the user provides GSC access, merge impression/click data for traffic-weighted prioritisation
