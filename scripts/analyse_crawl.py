#!/usr/bin/env python3
"""
Technical SEO Audit - Crawl Data Analysis Engine

This script processes normalised crawl data and runs all audit checks
across the 10 categories defined in the analysis-modules reference.

Usage:
    python analyse_crawl.py --input <normalised_csv> --output <results_json> [--platform <platform>]
"""

import pandas as pd
import json
import argparse
import sys
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# Column name normalisation helpers
# ---------------------------------------------------------------------------

SCREAMING_FROG_MAP = {
    "Address": "url",
    "Content Type": "content_type",
    "Status Code": "status_code",
    "Status": "status_text",
    "Indexability": "indexability",
    "Indexability Status": "indexability_reason",
    "Title 1": "title",
    "Title 1 Length": "title_length",
    "Title 1 Pixel Width": "title_pixel_width",
    "Meta Description 1": "meta_description",
    "Meta Description 1 Length": "meta_description_length",
    "Meta Description 1 Pixel Width": "meta_description_pixel_width",
    "Meta Keywords 1": "meta_keywords",
    "H1-1": "h1",
    "H1-1 Length": "h1_length",
    "H2-1": "h2",
    "H2-1 Length": "h2_length",
    "Meta Robots 1": "meta_robots",
    "X-Robots-Tag 1": "x_robots_tag",
    "Canonical Link Element 1": "canonical",
    'rel="next" 1': "rel_next",
    'rel="prev" 1': "rel_prev",
    "Size (bytes)": "page_size_bytes",
    "Transferred (bytes)": "transferred_bytes",
    "Total Transferred (bytes)": "total_transferred_bytes",
    "Word Count": "word_count",
    "Text Ratio": "text_ratio",
    "Crawl Depth": "crawl_depth",
    "Folder Depth": "folder_depth",
    "Inlinks": "inlinks",
    "Unique Inlinks": "unique_inlinks",
    "Unique JS Inlinks": "unique_js_inlinks",
    "% of Total": "pct_of_total",
    "Outlinks": "outlinks",
    "Unique Outlinks": "unique_outlinks",
    "External Outlinks": "external_outlinks",
    "Unique External Outlinks": "unique_external_outlinks",
    "Redirect URL": "redirect_url",
    "Redirect Type": "redirect_type",
    "Response Time": "response_time",
    "Last Modified": "last_modified",
    "Language": "language",
    "Hash": "hash",
    "HTTP Version": "http_version",
    "CO2 (mg)": "co2_mg",
    "Carbon Rating": "carbon_rating",
    "Flesch Reading Ease Score": "readability_score",
    "Sentence Count": "sentence_count",
    "Average Words Per Sentence": "avg_words_per_sentence",
    "Readability": "readability_level",
    "Closest Near Duplicate Match": "near_duplicate_match",
    "No. Near Duplicates": "near_duplicate_count",
    "Spelling Errors": "spelling_errors",
    "Grammar Errors": "grammar_errors",
    "Link Score": "link_score",
    "Closest Semantically Similar Address": "semantic_similarity_url",
    "Semantic Similarity Score": "semantic_similarity_score",
    "No. Semantically Similar": "semantic_similar_count",
    "Semantic Relevance Score": "semantic_relevance_score",
    "Crawl Timestamp": "crawl_timestamp",
    "Cookies": "cookies",
    "Clicks": "gsc_clicks",
    "Impressions": "gsc_impressions",
    "CTR": "gsc_ctr",
    "Position": "gsc_position",
}

SITEBULB_MAP = {
    "URL": "url",
    "Status Code": "status_code",
    "Indexable": "indexability",
    "Page Title": "title",
    "Meta Description": "meta_description",
    "H1": "h1",
    "Canonical": "canonical",
    "Word Count": "word_count",
    "Internal Inlinks": "inlinks",
    "Crawl Depth": "crawl_depth",
    "Response Time (ms)": "response_time",
    "Page Size": "page_size_bytes",
}


def detect_tool(headers):
    """Detect which crawl tool produced the CSV based on column headers."""
    header_set = set(headers)
    if "Address" in header_set and ("Status Code" in header_set or "Indexability" in header_set):
        return "screaming_frog"
    if "URL" in header_set and "Indexable" in header_set and "Address" not in header_set:
        return "sitebulb"
    if "URL" in header_set and "HTTP Code" in header_set:
        return "ahrefs"
    return "unknown"


def normalise_columns(df, tool):
    """Rename columns to internal schema based on detected tool."""
    if tool == "screaming_frog":
        df = df.rename(columns=SCREAMING_FROG_MAP)
    elif tool == "sitebulb":
        df = df.rename(columns=SITEBULB_MAP)
        if "indexability" in df.columns:
            df["indexability"] = df["indexability"].map(
                lambda x: "Indexable" if str(x).lower() in ("yes", "true", "1", "indexable") else "Non-Indexable"
            )
        if "response_time" in df.columns:
            df["response_time"] = pd.to_numeric(df["response_time"], errors="coerce") / 1000
    elif tool == "ahrefs":
        df = df.rename(columns={
            "URL": "url", "HTTP Code": "status_code", "Title": "title",
            "Description": "meta_description", "H1": "h1",
            "Canonical URL": "canonical", "Word Count": "word_count",
            "Internal Links In": "inlinks", "Depth": "crawl_depth",
        })
    return df


def ensure_numeric(df, cols):
    """Convert columns to numeric, coercing errors to NaN."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

PLATFORM_SIGNATURES = {
    "shopify": ["/collections/", "/products/", "cdn.shopify.com", "myshopify.com"],
    "wordpress": ["/wp-content/", "/wp-admin/", "/wp-json/"],
    "wix": ["wixsite.com", "static.wixstatic.com"],
    "squarespace": ["squarespace.com", "sqsp.net"],
    "magento": ["/catalog/product/", "/checkout/cart/"],
    "webflow": ["webflow.io", "assets.website-files.com"],
    "nextjs": ["/_next/"],
    "drupal": ["/node/", "/sites/default/"],
}


def detect_platform(df):
    """Detect CMS/platform from URL patterns."""
    if "url" not in df.columns:
        return "unknown"
    all_urls = " ".join(df["url"].dropna().astype(str).tolist()).lower()
    scores = {}
    for platform, sigs in PLATFORM_SIGNATURES.items():
        scores[platform] = sum(1 for s in sigs if s.lower() in all_urls)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "custom"


def detect_site_type(df):
    """Infer site type from URL patterns."""
    if "url" not in df.columns:
        return "unknown"
    urls = df["url"].dropna().astype(str)
    product_count = urls.str.contains("/product", case=False).sum()
    blog_count = urls.str.contains("/blog|/news|/article|/post", case=False).sum()
    category_count = urls.str.contains("/collection|/categor", case=False).sum()
    total = len(urls)
    if product_count > total * 0.2:
        return "ecommerce"
    if blog_count > total * 0.3:
        return "blog_publisher"
    if category_count > total * 0.15:
        return "ecommerce"
    return "brochure_saas"


# ---------------------------------------------------------------------------
# Analysis checks
# ---------------------------------------------------------------------------

def check_status_codes(df):
    """1.1 HTTP Status Code Distribution"""
    findings = {"check_id": "1.1", "check_name": "HTTP Status Code Distribution"}
    if "status_code" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Status code data not available"
        return findings

    dist = df["status_code"].value_counts().to_dict()
    code_ranges = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
    for code, count in dist.items():
        code = int(code) if pd.notna(code) else 0
        if 200 <= code < 300: code_ranges["2xx"] += count
        elif 300 <= code < 400: code_ranges["3xx"] += count
        elif 400 <= code < 500: code_ranges["4xx"] += count
        elif 500 <= code < 600: code_ranges["5xx"] += count
        else: code_ranges["other"] += count

    error_urls_4xx = df[df["status_code"].between(400, 499)]["url"].tolist() if "url" in df.columns else []
    error_urls_5xx = df[df["status_code"].between(500, 599)]["url"].tolist() if "url" in df.columns else []

    total_errors = code_ranges["4xx"] + code_ranges["5xx"]
    if code_ranges["5xx"] > 0:
        findings["status"] = "critical"
    elif code_ranges["4xx"] > 5:
        findings["status"] = "critical"
    elif code_ranges["4xx"] > 0:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{code_ranges['4xx']} client errors (4xx), {code_ranges['5xx']} server errors (5xx) out of {len(df)} URLs"
    findings["affected_urls_count"] = total_errors
    findings["affected_urls"] = (error_urls_4xx + error_urls_5xx)[:50]
    findings["details"] = {"distribution": code_ranges, "full_distribution": {str(k): v for k, v in dist.items()}}
    findings["seo_impact"] = min(10, 3 + total_errors)
    findings["business_impact"] = min(10, 2 + total_errors)
    findings["fix_effort"] = 3
    return findings


def check_redirects(df):
    """1.2 Redirect Analysis"""
    findings = {"check_id": "1.2", "check_name": "Redirect Analysis"}
    redirects = df[df["status_code"].between(300, 399)] if "status_code" in df.columns else pd.DataFrame()

    if len(redirects) == 0:
        findings["status"] = "pass"
        findings["summary"] = "No redirects found in crawl data"
        findings["affected_urls_count"] = 0
        return findings

    chains = []
    loops = []
    temp_redirects = []
    redirect_to_4xx = []

    if "redirect_url" in df.columns and "url" in df.columns:
        redirect_map = dict(zip(df["url"], df["redirect_url"]))
        status_map = dict(zip(df["url"], df["status_code"]))

        for url, target in redirect_map.items():
            if pd.isna(target) or target == "":
                continue
            chain = [url]
            current = target
            seen = {url}
            while current in redirect_map and pd.notna(redirect_map.get(current)):
                if current in seen:
                    loops.append(chain + [current])
                    break
                seen.add(current)
                chain.append(current)
                current = redirect_map[current]
            if len(chain) > 2:
                chains.append(chain)

            target_status = status_map.get(target)
            if pd.notna(target_status) and 400 <= int(target_status) < 500:
                redirect_to_4xx.append({"from": url, "to": target, "target_status": int(target_status)})

    if "status_code" in df.columns:
        temp_redirects = df[df["status_code"].isin([302, 307])]["url"].tolist()

    issues = len(chains) + len(loops) + len(redirect_to_4xx)
    if loops:
        findings["status"] = "critical"
    elif chains or redirect_to_4xx:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(chains)} redirect chains, {len(loops)} loops, {len(temp_redirects)} temporary redirects, {len(redirect_to_4xx)} redirects to 4xx"
    findings["affected_urls_count"] = len(redirects)
    findings["details"] = {
        "chains": chains[:20],
        "loops": loops[:10],
        "temp_redirects": temp_redirects[:20],
        "redirects_to_4xx": redirect_to_4xx[:20],
    }
    findings["seo_impact"] = min(10, 4 + len(loops) * 3 + len(chains))
    findings["business_impact"] = min(10, 3 + len(loops) * 2)
    findings["fix_effort"] = 3
    return findings


def check_crawl_depth(df):
    """1.3 Crawl Depth Analysis"""
    findings = {"check_id": "1.3", "check_name": "Crawl Depth Analysis"}
    if "crawl_depth" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Crawl depth data not available"
        return findings

    depth_dist = df["crawl_depth"].value_counts().sort_index().to_dict()
    deep_pages = df[df["crawl_depth"] >= 4]
    very_deep = df[df["crawl_depth"] >= 6]

    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df
    deep_indexable = indexable[indexable["crawl_depth"] >= 4] if "crawl_depth" in indexable.columns else pd.DataFrame()
    pct_deep = (len(deep_indexable) / len(indexable) * 100) if len(indexable) > 0 else 0

    if pct_deep > 30:
        findings["status"] = "critical"
    elif pct_deep > 15:
        findings["status"] = "warning"
    elif len(very_deep) > 0:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(deep_pages)} pages at depth 4+, {len(very_deep)} at depth 6+. {pct_deep:.1f}% of indexable pages are deep."
    findings["affected_urls_count"] = len(deep_pages)
    findings["affected_urls"] = deep_pages["url"].tolist()[:30] if "url" in deep_pages.columns else []
    findings["details"] = {"depth_distribution": {str(k): v for k, v in depth_dist.items()}, "pct_deep_indexable": round(pct_deep, 2)}
    findings["seo_impact"] = min(10, 3 + int(pct_deep / 10))
    findings["business_impact"] = min(10, 2 + int(pct_deep / 15))
    findings["fix_effort"] = 6
    return findings


def check_orphan_pages(df):
    """1.4 Orphan Pages"""
    findings = {"check_id": "1.4", "check_name": "Orphan Pages"}
    if "unique_inlinks" not in df.columns and "inlinks" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Inlink data not available"
        return findings

    inlink_col = "unique_inlinks" if "unique_inlinks" in df.columns else "inlinks"
    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df

    orphans = indexable[indexable[inlink_col] <= 1]
    zero_inlinks = indexable[indexable[inlink_col] == 0]

    if len(zero_inlinks) > 5:
        findings["status"] = "critical"
    elif len(orphans) > 10:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(zero_inlinks)} pages with 0 inlinks, {len(orphans)} pages with 0-1 inlinks"
    findings["affected_urls_count"] = len(orphans)
    findings["affected_urls"] = orphans["url"].tolist()[:30] if "url" in orphans.columns else []
    findings["seo_impact"] = min(10, 5 + len(zero_inlinks))
    findings["business_impact"] = min(10, 3 + len(zero_inlinks))
    findings["fix_effort"] = 4
    return findings


def check_response_times(df):
    """1.6 Response Time Analysis"""
    findings = {"check_id": "1.6", "check_name": "Response Time Analysis"}
    if "response_time" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Response time data not available"
        return findings

    rt = df["response_time"].dropna()
    if len(rt) == 0:
        findings["status"] = "info"
        findings["summary"] = "No response time data"
        return findings

    mean_rt = rt.mean()
    median_rt = rt.median()
    slow_1s = df[df["response_time"] > 1]
    slow_3s = df[df["response_time"] > 3]
    pct_slow = len(slow_1s) / len(df) * 100

    if mean_rt > 2 or len(slow_3s) > 5:
        findings["status"] = "critical"
    elif mean_rt > 1 or pct_slow > 20:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"Mean: {mean_rt:.2f}s, Median: {median_rt:.2f}s. {len(slow_1s)} pages > 1s, {len(slow_3s)} pages > 3s."
    findings["affected_urls_count"] = len(slow_1s)
    findings["affected_urls"] = slow_3s["url"].tolist()[:20] if "url" in slow_3s.columns else []
    findings["details"] = {
        "mean": round(mean_rt, 3), "median": round(median_rt, 3),
        "slow_1s_count": len(slow_1s), "slow_3s_count": len(slow_3s),
        "pct_slow": round(pct_slow, 2),
    }
    findings["seo_impact"] = min(10, 3 + int(mean_rt * 2))
    findings["business_impact"] = min(10, 3 + int(mean_rt * 2))
    findings["fix_effort"] = 5
    return findings


def check_url_structure(df):
    """1.5 URL Structure Quality"""
    findings = {"check_id": "1.5", "check_name": "URL Structure Quality"}
    if "url" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "URL data not available"
        return findings

    urls = df["url"].dropna().astype(str)
    issues = {
        "has_parameters": [],
        "has_uppercase": [],
        "too_long": [],
        "has_special_chars": [],
        "double_slashes": [],
    }

    for u in urls:
        parsed = urlparse(u)
        if parsed.query:
            issues["has_parameters"].append(u)
        if u != u.lower():
            issues["has_uppercase"].append(u)
        if len(u) > 200:
            issues["too_long"].append(u)
        path = parsed.path
        if re.search(r'[^a-zA-Z0-9/_\-.]', path):
            issues["has_special_chars"].append(u)
        if '//' in parsed.path:
            issues["double_slashes"].append(u)

    total_issues = sum(len(v) for v in issues.values())
    if total_issues > len(urls) * 0.2:
        findings["status"] = "warning"
    elif total_issues > 0:
        findings["status"] = "info"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(issues['has_parameters'])} parameterised URLs, {len(issues['has_uppercase'])} with uppercase, {len(issues['too_long'])} too long"
    findings["affected_urls_count"] = total_issues
    findings["details"] = {k: v[:15] for k, v in issues.items()}
    findings["seo_impact"] = min(10, 2 + total_issues // 5)
    findings["business_impact"] = 2
    findings["fix_effort"] = 5
    return findings


def check_indexability(df):
    """2.1 Indexability Distribution"""
    findings = {"check_id": "2.1", "check_name": "Indexability Distribution"}
    if "indexability" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Indexability data not available"
        return findings

    dist = df["indexability"].value_counts().to_dict()
    indexable = dist.get("Indexable", 0)
    non_indexable = dist.get("Non-Indexable", 0)
    total = indexable + non_indexable

    reason_dist = {}
    if "indexability_reason" in df.columns:
        reasons = df[df["indexability"].str.lower() == "non-indexable"]["indexability_reason"].value_counts().to_dict()
        reason_dist = {str(k): v for k, v in reasons.items()}

    pct_non_indexable = (non_indexable / total * 100) if total > 0 else 0

    if pct_non_indexable > 40:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{indexable} indexable ({100-pct_non_indexable:.1f}%), {non_indexable} non-indexable ({pct_non_indexable:.1f}%)"
    findings["affected_urls_count"] = non_indexable
    findings["details"] = {"distribution": dist, "non_indexable_reasons": reason_dist}
    findings["seo_impact"] = min(10, 2 + int(pct_non_indexable / 10))
    findings["business_impact"] = min(10, 2 + int(pct_non_indexable / 10))
    findings["fix_effort"] = 4
    return findings


def check_canonicals(df):
    """2.2 Canonical Tag Audit"""
    findings = {"check_id": "2.2", "check_name": "Canonical Tag Audit"}
    if "canonical" not in df.columns or "url" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Canonical data not available"
        return findings

    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df

    missing_canonical = indexable[indexable["canonical"].isna() | (indexable["canonical"] == "")]
    self_ref = indexable[indexable["canonical"] == indexable["url"]]
    non_self = indexable[(indexable["canonical"].notna()) & (indexable["canonical"] != "") & (indexable["canonical"] != indexable["url"])]

    # Check canonical targets
    all_urls = set(df["url"].dropna())
    status_map = dict(zip(df["url"], df.get("status_code", pd.Series(dtype=int))))

    broken_canonical_targets = []
    for _, row in non_self.iterrows():
        target = row["canonical"]
        target_status = status_map.get(target)
        if target_status and (400 <= int(target_status) < 600):
            broken_canonical_targets.append({"url": row["url"], "canonical_target": target, "target_status": int(target_status)})

    issues_count = len(missing_canonical) + len(broken_canonical_targets)
    if broken_canonical_targets:
        findings["status"] = "critical"
    elif len(missing_canonical) > len(indexable) * 0.3:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(missing_canonical)} indexable pages missing canonical, {len(self_ref)} self-referencing (good), {len(non_self)} non-self-referencing, {len(broken_canonical_targets)} pointing to error pages"
    findings["affected_urls_count"] = issues_count
    findings["affected_urls"] = missing_canonical["url"].tolist()[:20]
    findings["details"] = {
        "missing_count": len(missing_canonical),
        "self_referencing_count": len(self_ref),
        "non_self_count": len(non_self),
        "broken_targets": broken_canonical_targets[:10],
    }
    findings["seo_impact"] = min(10, 4 + len(broken_canonical_targets) * 2)
    findings["business_impact"] = min(10, 3 + len(broken_canonical_targets))
    findings["fix_effort"] = 3
    return findings


def check_titles(df):
    """3.1 Title Tag Analysis"""
    findings = {"check_id": "3.1", "check_name": "Title Tag Analysis"}
    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df

    if "title" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Title data not available"
        return findings

    missing = indexable[indexable["title"].isna() | (indexable["title"].astype(str).str.strip() == "")]
    titles = indexable["title"].dropna().astype(str)
    duplicates = titles[titles.duplicated(keep=False)]
    dup_groups = duplicates.value_counts()

    too_long = indexable[indexable.get("title_length", pd.Series(dtype=float)).fillna(0) > 60] if "title_length" in indexable.columns else pd.DataFrame()
    too_short = indexable[(indexable.get("title_length", pd.Series(dtype=float)).fillna(0) > 0) & (indexable.get("title_length", pd.Series(dtype=float)).fillna(0) < 30)] if "title_length" in indexable.columns else pd.DataFrame()

    pixel_truncated = indexable[indexable.get("title_pixel_width", pd.Series(dtype=float)).fillna(0) > 580] if "title_pixel_width" in indexable.columns else pd.DataFrame()

    total_issues = len(missing) + len(dup_groups) + len(too_long) + len(too_short)
    if len(missing) > 0:
        findings["status"] = "critical"
    elif len(dup_groups) > 3:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(missing)} missing titles, {len(dup_groups)} duplicate title groups, {len(too_long)} too long, {len(too_short)} too short, {len(pixel_truncated)} pixel-truncated"
    findings["affected_urls_count"] = total_issues
    findings["affected_urls"] = missing["url"].tolist()[:20] if "url" in missing.columns else []
    findings["details"] = {
        "missing_count": len(missing),
        "duplicate_groups": len(dup_groups),
        "duplicate_titles": {str(k): v for k, v in dup_groups.head(10).to_dict().items()},
        "too_long_count": len(too_long),
        "too_short_count": len(too_short),
        "pixel_truncated_count": len(pixel_truncated),
    }
    findings["seo_impact"] = min(10, 5 + len(missing))
    findings["business_impact"] = min(10, 4 + len(missing))
    findings["fix_effort"] = 2
    return findings


def check_meta_descriptions(df):
    """3.2 Meta Description Analysis"""
    findings = {"check_id": "3.2", "check_name": "Meta Description Analysis"}
    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df

    if "meta_description" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Meta description data not available"
        return findings

    missing = indexable[indexable["meta_description"].isna() | (indexable["meta_description"].astype(str).str.strip() == "")]
    descs = indexable["meta_description"].dropna().astype(str)
    duplicates = descs[descs.duplicated(keep=False)]
    dup_count = len(duplicates.unique())

    too_long = indexable[indexable.get("meta_description_length", pd.Series(dtype=float)).fillna(0) > 160] if "meta_description_length" in indexable.columns else pd.DataFrame()
    too_short = indexable[(indexable.get("meta_description_length", pd.Series(dtype=float)).fillna(0) > 0) & (indexable.get("meta_description_length", pd.Series(dtype=float)).fillna(0) < 70)] if "meta_description_length" in indexable.columns else pd.DataFrame()

    pct_missing = len(missing) / len(indexable) * 100 if len(indexable) > 0 else 0
    if pct_missing > 50:
        findings["status"] = "warning"
    elif pct_missing > 20:
        findings["status"] = "info"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(missing)} missing ({pct_missing:.1f}%), {dup_count} duplicate groups, {len(too_long)} too long, {len(too_short)} too short"
    findings["affected_urls_count"] = len(missing) + dup_count
    findings["affected_urls"] = missing["url"].tolist()[:20] if "url" in missing.columns else []
    findings["seo_impact"] = min(10, 3 + int(pct_missing / 20))
    findings["business_impact"] = min(10, 2 + int(pct_missing / 25))
    findings["fix_effort"] = 2
    return findings


def check_headings(df):
    """3.3 Heading Analysis"""
    findings = {"check_id": "3.3", "check_name": "Heading Analysis"}
    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df

    if "h1" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "H1 data not available"
        return findings

    missing_h1 = indexable[indexable["h1"].isna() | (indexable["h1"].astype(str).str.strip() == "")]

    if len(missing_h1) > 0:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(missing_h1)} indexable pages missing H1"
    findings["affected_urls_count"] = len(missing_h1)
    findings["affected_urls"] = missing_h1["url"].tolist()[:20] if "url" in missing_h1.columns else []
    findings["seo_impact"] = min(10, 4 + len(missing_h1))
    findings["business_impact"] = min(10, 3 + len(missing_h1) // 2)
    findings["fix_effort"] = 2
    return findings


def check_content_quality(df):
    """3.4 Content Quality Signals"""
    findings = {"check_id": "3.4", "check_name": "Content Quality Signals"}
    if "word_count" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Word count data not available"
        return findings

    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df
    wc = indexable["word_count"].dropna()

    if len(wc) == 0:
        findings["status"] = "info"
        findings["summary"] = "No word count data for indexable pages"
        return findings

    thin = indexable[indexable["word_count"] < 300]
    very_thin = indexable[indexable["word_count"] < 100]
    mean_wc = wc.mean()
    median_wc = wc.median()

    text_ratio_issues = pd.DataFrame()
    if "text_ratio" in indexable.columns:
        text_ratio_issues = indexable[indexable["text_ratio"].fillna(100) < 10]

    pct_thin = len(thin) / len(indexable) * 100 if len(indexable) > 0 else 0
    if pct_thin > 30:
        findings["status"] = "warning"
    elif len(very_thin) > 5:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"Mean word count: {mean_wc:.0f}, Median: {median_wc:.0f}. {len(thin)} pages < 300 words ({pct_thin:.1f}%), {len(very_thin)} < 100 words. {len(text_ratio_issues)} pages with text ratio < 10%"
    findings["affected_urls_count"] = len(thin)
    findings["affected_urls"] = very_thin["url"].tolist()[:20] if "url" in very_thin.columns else []
    findings["details"] = {
        "mean_word_count": round(mean_wc),
        "median_word_count": round(median_wc),
        "thin_count": len(thin),
        "very_thin_count": len(very_thin),
        "low_text_ratio_count": len(text_ratio_issues),
    }
    findings["seo_impact"] = min(10, 3 + int(pct_thin / 10))
    findings["business_impact"] = min(10, 2 + int(pct_thin / 15))
    findings["fix_effort"] = 6
    return findings


def check_duplicate_content(df):
    """2.5 Duplicate Content Detection"""
    findings = {"check_id": "2.5", "check_name": "Duplicate Content Detection"}

    near_dup_count = 0
    near_dup_urls = []

    if "near_duplicate_count" in df.columns:
        has_dups = df[df["near_duplicate_count"].fillna(0) > 0]
        near_dup_count = len(has_dups)
        near_dup_urls = has_dups["url"].tolist()[:20] if "url" in has_dups.columns else []

    if "hash" in df.columns:
        hash_dups = df[df["hash"].notna() & (df["hash"] != "")].groupby("hash").filter(lambda x: len(x) > 1)
        exact_dup_count = len(hash_dups)
    else:
        exact_dup_count = 0

    total = near_dup_count + exact_dup_count
    if exact_dup_count > 5:
        findings["status"] = "critical"
    elif near_dup_count > 10:
        findings["status"] = "warning"
    elif total > 0:
        findings["status"] = "info"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{exact_dup_count} exact duplicate pages, {near_dup_count} near-duplicate pages"
    findings["affected_urls_count"] = total
    findings["affected_urls"] = near_dup_urls
    findings["seo_impact"] = min(10, 4 + exact_dup_count + near_dup_count // 3)
    findings["business_impact"] = min(10, 3 + exact_dup_count)
    findings["fix_effort"] = 5
    return findings


def check_page_weight(df):
    """5.1 Page Weight Analysis"""
    findings = {"check_id": "5.1", "check_name": "Page Weight Analysis"}
    size_col = None
    for col_name in ["total_transferred_bytes", "transferred_bytes", "page_size_bytes"]:
        if col_name in df.columns:
            size_col = col_name
            break

    if size_col is None:
        findings["status"] = "info"
        findings["summary"] = "Page size data not available"
        return findings

    sizes = df[size_col].dropna()
    if len(sizes) == 0:
        findings["status"] = "info"
        findings["summary"] = "No page size data"
        return findings

    mean_size = sizes.mean()
    heavy_3mb = df[df[size_col] > 3_000_000]
    heavy_5mb = df[df[size_col] > 5_000_000]

    if len(heavy_5mb) > 0:
        findings["status"] = "critical"
    elif mean_size > 2_000_000:
        findings["status"] = "warning"
    elif len(heavy_3mb) > 0:
        findings["status"] = "warning"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"Mean page size: {mean_size/1024:.0f}KB. {len(heavy_3mb)} pages > 3MB, {len(heavy_5mb)} > 5MB"
    findings["affected_urls_count"] = len(heavy_3mb)
    findings["affected_urls"] = heavy_3mb["url"].tolist()[:20] if "url" in heavy_3mb.columns else []
    findings["details"] = {
        "mean_bytes": round(mean_size),
        "mean_kb": round(mean_size / 1024),
        "heavy_3mb_count": len(heavy_3mb),
        "heavy_5mb_count": len(heavy_5mb),
    }
    findings["seo_impact"] = min(10, 3 + len(heavy_3mb))
    findings["business_impact"] = min(10, 3 + len(heavy_5mb) * 2)
    findings["fix_effort"] = 5
    return findings


def check_https(df):
    """8.1 HTTPS Implementation"""
    findings = {"check_id": "8.1", "check_name": "HTTPS Implementation"}
    if "url" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "URL data not available"
        return findings

    http_pages = df[df["url"].str.startswith("http://", na=False)]
    https_pages = df[df["url"].str.startswith("https://", na=False)]

    if len(http_pages) > 0:
        findings["status"] = "critical"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(https_pages)} HTTPS pages, {len(http_pages)} HTTP pages"
    findings["affected_urls_count"] = len(http_pages)
    findings["affected_urls"] = http_pages["url"].tolist()[:20]
    findings["seo_impact"] = 8 if len(http_pages) > 0 else 0
    findings["business_impact"] = 7 if len(http_pages) > 0 else 0
    findings["fix_effort"] = 3
    return findings


def check_internal_linking(df):
    """4.1 Internal Link Distribution"""
    findings = {"check_id": "4.1", "check_name": "Internal Link Distribution"}
    inlink_col = None
    for c in ["unique_inlinks", "inlinks"]:
        if c in df.columns:
            inlink_col = c
            break

    if inlink_col is None:
        findings["status"] = "info"
        findings["summary"] = "Internal link data not available"
        return findings

    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df
    inlinks = indexable[inlink_col].dropna()

    if len(inlinks) == 0:
        findings["status"] = "info"
        findings["summary"] = "No inlink data for indexable pages"
        return findings

    mean_inlinks = inlinks.mean()
    median_inlinks = inlinks.median()
    low_inlinks = indexable[indexable[inlink_col] <= 3]
    high_inlinks = indexable[indexable[inlink_col] > inlinks.quantile(0.95)] if len(inlinks) > 10 else pd.DataFrame()

    findings["status"] = "info"  # Linking is always informational unless severe
    if len(low_inlinks) > len(indexable) * 0.3:
        findings["status"] = "warning"

    findings["summary"] = f"Mean inlinks: {mean_inlinks:.1f}, Median: {median_inlinks:.0f}. {len(low_inlinks)} pages with <= 3 inlinks."
    findings["affected_urls_count"] = len(low_inlinks)
    findings["affected_urls"] = low_inlinks["url"].tolist()[:20] if "url" in low_inlinks.columns else []
    findings["details"] = {
        "mean": round(mean_inlinks, 1),
        "median": round(median_inlinks),
        "low_inlink_count": len(low_inlinks),
        "high_inlink_count": len(high_inlinks),
    }
    findings["seo_impact"] = min(10, 3 + len(low_inlinks) // 5)
    findings["business_impact"] = min(10, 2 + len(low_inlinks) // 10)
    findings["fix_effort"] = 5
    return findings


def check_cannibalisation(df):
    """3.5 Keyword Cannibalisation Detection"""
    findings = {"check_id": "3.5", "check_name": "Keyword Cannibalisation Detection"}
    if "title" not in df.columns or "url" not in df.columns:
        findings["status"] = "info"
        findings["summary"] = "Title data not available for cannibalisation check"
        return findings

    indexable = df[df.get("indexability", pd.Series(dtype=str)).str.lower() == "indexable"] if "indexability" in df.columns else df
    titles = indexable[["url", "title"]].dropna(subset=["title"])
    titles = titles[titles["title"].astype(str).str.strip() != ""]

    if len(titles) < 2:
        findings["status"] = "pass"
        findings["summary"] = "Not enough pages for cannibalisation analysis"
        return findings

    # Group by similar titles using fuzzy matching
    cannibal_groups = []
    processed = set()
    title_list = titles.to_dict("records")

    for i, row_a in enumerate(title_list):
        if i in processed:
            continue
        group = [row_a]
        for j, row_b in enumerate(title_list[i+1:], start=i+1):
            if j in processed:
                continue
            similarity = SequenceMatcher(None, str(row_a["title"]).lower(), str(row_b["title"]).lower()).ratio()
            if similarity > 0.7:
                group.append(row_b)
                processed.add(j)
        if len(group) > 1:
            cannibal_groups.append(group)
            processed.add(i)

    if len(cannibal_groups) > 5:
        findings["status"] = "warning"
    elif len(cannibal_groups) > 0:
        findings["status"] = "info"
    else:
        findings["status"] = "pass"

    findings["summary"] = f"{len(cannibal_groups)} potential cannibalisation groups detected"
    findings["affected_urls_count"] = sum(len(g) for g in cannibal_groups)
    findings["details"] = {
        "groups": [
            {"title_sample": g[0]["title"], "urls": [item["url"] for item in g]}
            for g in cannibal_groups[:10]
        ]
    }
    findings["seo_impact"] = min(10, 4 + len(cannibal_groups))
    findings["business_impact"] = min(10, 3 + len(cannibal_groups))
    findings["fix_effort"] = 6
    return findings


# ---------------------------------------------------------------------------
# Priority scoring
# ---------------------------------------------------------------------------

def calculate_priority(finding):
    """Calculate priority score for a finding."""
    seo = finding.get("seo_impact", 0)
    biz = finding.get("business_impact", 0)
    effort = finding.get("fix_effort", 5)
    score = (seo * 0.4) + (biz * 0.4) + ((10 - effort) * 0.2)
    finding["priority_score"] = round(score, 2)
    if score >= 8:
        finding["priority_band"] = "Critical"
    elif score >= 6:
        finding["priority_band"] = "High"
    elif score >= 4:
        finding["priority_band"] = "Medium"
    elif score >= 2:
        finding["priority_band"] = "Low"
    else:
        finding["priority_band"] = "Informational"
    return finding


def calculate_health_score(findings):
    """Calculate overall and per-category health scores."""
    category_penalties = defaultdict(float)
    status_penalty = {"critical": 15, "warning": 8, "info": 2, "pass": 0}

    for f in findings:
        cat = f.get("check_id", "0")[0]
        penalty = status_penalty.get(f.get("status", "pass"), 0)
        # Scale penalty by affected URL proportion
        affected = f.get("affected_urls_count", 0)
        scale = min(1, affected / 50)  # Cap scaling at 50 URLs
        penalty = penalty * max(0.3, scale)
        category_penalties[cat] += penalty

    category_scores = {}
    for cat, penalty in category_penalties.items():
        category_scores[cat] = max(0, min(100, round(100 - penalty)))

    # Overall weighted score
    weights = {"1": 0.20, "2": 0.20, "3": 0.15, "4": 0.12, "5": 0.12,
               "6": 0.05, "7": 0.05, "8": 0.05, "9": 0.03, "0": 0.03}
    overall = sum(category_scores.get(cat, 100) * weights.get(cat, 0.05) for cat in weights)

    return round(overall), category_scores


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_full_audit(df, platform="auto"):
    """Run all audit checks and return structured results."""

    # Ensure numeric columns
    numeric_cols = ["status_code", "title_length", "title_pixel_width", "meta_description_length",
                    "h1_length", "word_count", "text_ratio", "page_size_bytes", "transferred_bytes",
                    "total_transferred_bytes", "response_time", "crawl_depth", "folder_depth",
                    "inlinks", "unique_inlinks", "outlinks", "external_outlinks",
                    "near_duplicate_count", "spelling_errors", "grammar_errors",
                    "co2_mg", "readability_score", "sentence_count", "semantic_similarity_score"]
    df = ensure_numeric(df, numeric_cols)

    # Detect platform
    if platform == "auto":
        platform = detect_platform(df)
    site_type = detect_site_type(df)

    # Run all checks
    checks = [
        check_status_codes(df),
        check_redirects(df),
        check_crawl_depth(df),
        check_orphan_pages(df),
        check_url_structure(df),
        check_response_times(df),
        check_indexability(df),
        check_canonicals(df),
        check_duplicate_content(df),
        check_titles(df),
        check_meta_descriptions(df),
        check_headings(df),
        check_content_quality(df),
        check_cannibalisation(df),
        check_internal_linking(df),
        check_page_weight(df),
        check_https(df),
    ]

    # Calculate priority for each
    checks = [calculate_priority(c) for c in checks]

    # Sort by priority score descending
    checks.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

    # Calculate health scores
    overall_health, category_scores = calculate_health_score(checks)

    return {
        "platform": platform,
        "site_type": site_type,
        "total_urls": len(df),
        "overall_health_score": overall_health,
        "category_scores": category_scores,
        "findings": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="Technical SEO Audit Analysis")
    parser.add_argument("--input", required=True, help="Path to crawl CSV file")
    parser.add_argument("--output", required=True, help="Path for results JSON output")
    parser.add_argument("--platform", default="auto", help="Platform override (shopify, wordpress, etc.)")
    args = parser.parse_args()

    # Load CSV
    print(f"Loading {args.input}...")
    df = pd.read_csv(args.input, low_memory=False)
    print(f"Loaded {len(df)} rows with {len(df.columns)} columns")

    # Detect tool and normalise
    tool = detect_tool(df.columns.tolist())
    print(f"Detected tool: {tool}")
    df = normalise_columns(df, tool)

    # Run audit
    print("Running full audit...")
    results = run_full_audit(df, platform=args.platform)

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {args.output}")
    print(f"Overall health score: {results['overall_health_score']}/100")
    print(f"Platform: {results['platform']}")
    print(f"Site type: {results['site_type']}")
    print(f"Issues found: {len([f for f in results['findings'] if f['status'] != 'pass'])}")

    return results


if __name__ == "__main__":
    main()
