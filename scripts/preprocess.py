#!/usr/bin/env python3
"""
Technical SEO Audit - Crawl Data Pre-processor
===============================================
Reads a raw crawl CSV from Ahrefs, Screaming Frog, or Sitebulb (can be
50-100 MB / 500k+ rows), auto-detects the source tool, runs all analysis
in-memory, and writes:

  audit_summary.json     — aggregate stats Claude reads for the audit
  issues/                — one small CSV per issue type (only affected URLs)
  slim.csv               — essential columns only, for any deep-dive reads

Usage:
    python3 preprocess.py --input <pages_csv> [--out-dir <dir>]
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Column mappings: tool-specific headers → internal schema
# ---------------------------------------------------------------------------

AHREFS_COL_MAP = {
    "URL":                                   "url",
    "Title":                                 "title",
    "Content type":                          "content_type",
    "HTTP status code":                      "status_code",
    "Organic traffic":                       "organic_traffic",
    "Depth":                                 "crawl_depth",
    "Is indexable page":                     "indexable",
    "Meta description":                      "meta_description",
    "H1":                                    "h1",
    "H2":                                    "h2",
    "No. of content words":                  "word_count",
    "Canonical URL":                         "canonical",
    "Canonical URL code":                    "canonical_status_code",
    "Redirect URL":                          "redirect_url",
    "Redirect URL code":                     "redirect_status_code",
    "Size (bytes)":                          "page_size_bytes",
    "Time to first byte (ms)":               "ttfb_ms",
    "Loading time (ms)":                     "load_time_ms",
    "Content hash":                          "content_hash",
    "No. of pages having the same content":  "duplicate_count",
    "Referenced in sitemaps":                "in_sitemap",
    "No. of href inlinks":                   "inlinks",
    "No. of inlinks dofollow":               "inlinks_dofollow",
    "No. of inlinks nofollow":               "inlinks_nofollow",
    "No. of canonical inlinks":              "canonical_inlinks",
    "No. of hreflang inlinks":               "hreflang_inlinks",
    "Schema items":                          "schema_items",
    "Structured data issues":                "structured_data_issues",
    "Redirect chain URLs":                   "redirect_chain",
    "Is redirect loop":                      "redirect_loop",
    "Linked images without alt attribute":   "images_no_alt",
    "Meta robots":                           "meta_robots",
}

SCREAMING_FROG_MAP = {
    "Address":                          "url",
    "Content Type":                     "content_type",
    "Status Code":                      "status_code",
    "Status":                           "status_text",
    "Indexability":                     "indexable",
    "Indexability Status":              "indexability_reason",
    "Title 1":                          "title",
    "Meta Description 1":               "meta_description",
    "H1-1":                             "h1",
    "H2-1":                             "h2",
    "Meta Robots 1":                    "meta_robots",
    "X-Robots-Tag 1":                   "x_robots_tag",
    "Canonical Link Element 1":         "canonical",
    "Size (bytes)":                     "page_size_bytes",
    "Word Count":                       "word_count",
    "Text Ratio":                       "text_ratio",
    "Crawl Depth":                      "crawl_depth",
    "Inlinks":                          "inlinks",
    "Unique Inlinks":                   "unique_inlinks",
    "Outlinks":                         "outlinks",
    "External Outlinks":                "external_outlinks",
    "Redirect URL":                     "redirect_url",
    "Redirect Type":                    "redirect_type",
    "Response Time":                    "response_time",
    "Hash":                             "content_hash",
    "CO2 (mg)":                         "co2_mg",
    "Closest Near Duplicate Match":     "near_duplicate_match",
    "No. Near Duplicates":              "duplicate_count",
    "Link Score":                       "link_score",
    "Clicks":                           "organic_traffic",  # GSC clicks if integrated
}

SITEBULB_MAP = {
    "URL":                  "url",
    "Status Code":          "status_code",
    "Indexable":            "indexable",
    "Page Title":           "title",
    "Meta Description":     "meta_description",
    "H1":                   "h1",
    "Canonical":            "canonical",
    "Word Count":           "word_count",
    "Internal Inlinks":     "inlinks",
    "Crawl Depth":          "crawl_depth",
    "Response Time (ms)":   "response_time",  # converted to seconds below
    "Page Size":            "page_size_bytes",
}

# Internal schema columns kept in slim.csv
SLIM_COLS = [
    "url", "status_code", "indexable", "crawl_depth",
    "title", "meta_description", "h1", "h2",
    "word_count", "canonical", "canonical_status_code",
    "redirect_url", "redirect_status_code", "redirect_chain", "redirect_loop",
    "page_size_bytes", "ttfb_ms", "load_time_ms", "response_time",
    "content_hash", "duplicate_count",
    "in_sitemap", "inlinks", "inlinks_dofollow",
    "organic_traffic", "schema_items", "structured_data_issues",
    "images_no_alt", "meta_robots",
]

# ---------------------------------------------------------------------------
# Tool detection
# ---------------------------------------------------------------------------

def detect_tool(headers):
    """Detect crawl tool from CSV column headers."""
    h = set(headers)
    if "Address" in h and ("Status Code" in h or "Indexability" in h):
        return "screaming_frog"
    if "URL" in h and "Indexable" in h and "Page Title" in h:
        return "sitebulb"
    if "URL" in h and "HTTP status code" in h:
        return "ahrefs"
    return "unknown"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_str(val, default=""):
    if pd.isna(val):
        return default
    return str(val).strip()

def safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def status_bucket(code):
    c = safe_int(code)
    if c == 200:       return "2xx_ok"
    if 200 <= c < 300: return "2xx_other"
    if 301 <= c < 308: return "3xx_redirect"
    if c == 404:       return "404"
    if 400 <= c < 500: return "4xx_other"
    if 500 <= c < 600: return "5xx"
    if c == 0:         return "0_unknown"
    return f"other_{c}"

# ---------------------------------------------------------------------------
# Main analysis (tool-agnostic — operates on internal schema)
# ---------------------------------------------------------------------------

def analyse(df):
    total = len(df)
    summary = {"total_urls": total}

    # -- Status codes --------------------------------------------------------
    status_dist = df["status_code"].apply(status_bucket).value_counts().to_dict()
    summary["status_distribution"] = {k: int(v) for k, v in status_dist.items()}
    summary["pages_200_count"] = int((df["status_code"].apply(safe_int) == 200).sum())

    # -- Indexability --------------------------------------------------------
    indexable_mask = df["indexable"].astype(str).str.lower().isin(
        ["true", "yes", "1", "indexable"]
    )
    not_indexable_mask = ~indexable_mask
    summary["indexable_count"]     = int(indexable_mask.sum())
    summary["not_indexable_count"] = int(not_indexable_mask.sum())

    # -- Crawl depth ---------------------------------------------------------
    depth_dist = df["crawl_depth"].dropna().apply(safe_int).value_counts().sort_index().to_dict()
    summary["depth_distribution"] = {str(k): int(v) for k, v in depth_dist.items()}

    # -- Organic traffic -----------------------------------------------------
    ot = df["organic_traffic"].fillna(0).apply(safe_int)
    summary["organic_traffic"] = {
        "total":               int(ot.sum()),
        "pages_with_traffic":  int((ot > 0).sum()),
        "pages_zero_traffic":  int((ot == 0).sum()),
        "top_traffic_pages":   df.nlargest(20, "organic_traffic")[
            ["url", "organic_traffic", "status_code", "indexable"]
        ].to_dict(orient="records"),
    }

    # -- Titles --------------------------------------------------------------
    df["_title_len"] = df["title"].apply(lambda x: len(safe_str(x)))
    title_missing   = df[df["title"].isna() | (df["title"].astype(str).str.strip() == "")]
    title_short     = df[(df["_title_len"] > 0) & (df["_title_len"] < 30)]
    title_long      = df[df["_title_len"] > 60]
    title_dupe_cnts = df["title"].dropna().value_counts()
    title_dupes     = title_dupe_cnts[title_dupe_cnts > 1]
    summary["titles"] = {
        "missing_count":        len(title_missing),
        "too_short_count":      len(title_short),
        "too_long_count":       len(title_long),
        "duplicate_groups":     int(len(title_dupes)),
        "duplicate_urls_total": int(title_dupes.sum()),
    }

    # -- Meta descriptions ---------------------------------------------------
    df["_md_len"] = df["meta_description"].apply(lambda x: len(safe_str(x)))
    md_missing    = df[df["meta_description"].isna() | (df["meta_description"].astype(str).str.strip() == "")]
    md_short      = df[(df["_md_len"] > 0) & (df["_md_len"] < 70)]
    md_long       = df[df["_md_len"] > 160]
    md_dupe_cnts  = df["meta_description"].dropna().value_counts()
    md_dupes      = md_dupe_cnts[md_dupe_cnts > 1]
    summary["meta_descriptions"] = {
        "missing_count":        len(md_missing),
        "too_short_count":      len(md_short),
        "too_long_count":       len(md_long),
        "duplicate_groups":     int(len(md_dupes)),
        "duplicate_urls_total": int(md_dupes.sum()),
    }

    # -- H1 ------------------------------------------------------------------
    df["_h1_len"]  = df["h1"].apply(lambda x: len(safe_str(x)))
    h1_missing     = df[df["h1"].isna() | (df["h1"].astype(str).str.strip() == "")]
    h1_dupe_cnts   = df["h1"].dropna().value_counts()
    h1_dupes       = h1_dupe_cnts[h1_dupe_cnts > 1]
    summary["h1"] = {
        "missing_count":        len(h1_missing),
        "duplicate_groups":     int(len(h1_dupes)),
        "duplicate_urls_total": int(h1_dupes.sum()),
    }

    # -- Canonicals ----------------------------------------------------------
    canon_missing = df[df["canonical"].isna() | (df["canonical"].astype(str).str.strip() == "")]
    canon_self    = df[
        df["canonical"].notna() &
        (df["canonical"].astype(str).str.strip() == df["url"].astype(str).str.strip())
    ]
    canon_other   = df[
        df["canonical"].notna() &
        (df["canonical"].astype(str).str.strip() != "") &
        (df["canonical"].astype(str).str.strip() != df["url"].astype(str).str.strip())
    ]
    canon_broken  = df[
        df["canonical"].notna() &
        (df["canonical"].astype(str).str.strip() != "") &
        (df["canonical_status_code"].apply(safe_int) != 200) &
        (df["canonical_status_code"].notna())
    ] if "canonical_status_code" in df.columns else df.iloc[0:0]
    summary["canonicals"] = {
        "missing_count":           len(canon_missing),
        "self_canonical_count":    len(canon_self),
        "pointing_elsewhere_count": len(canon_other),
        "broken_canonical_count":  len(canon_broken),
    }

    # -- Redirects -----------------------------------------------------------
    redirect_mask = df["redirect_url"].notna() & (df["redirect_url"].astype(str).str.strip() != "")
    redirects     = df[redirect_mask]
    chains_mask   = df["redirect_chain"].notna() & (df["redirect_chain"].astype(str).str.strip() != "") if "redirect_chain" in df.columns else pd.Series([False] * len(df))
    chains        = df[chains_mask]
    loops_mask    = df["redirect_loop"].astype(str).str.lower().isin(["true", "yes", "1"]) if "redirect_loop" in df.columns else pd.Series([False] * len(df))
    loops         = df[loops_mask]
    summary["redirects"] = {
        "total_redirect_urls":    len(redirects),
        "redirect_chains_count":  len(chains),
        "redirect_loops_count":   len(loops),
    }

    # -- Duplicate content ---------------------------------------------------
    dupe_content = df[df["duplicate_count"].apply(safe_int) > 0] if "duplicate_count" in df.columns else df.iloc[0:0]
    if "content_hash" in df.columns:
        unique_hashes = df.groupby("content_hash").size().reset_index(name="pages")
        hash_dupes    = unique_hashes[unique_hashes["pages"] > 1]
    else:
        hash_dupes = pd.DataFrame()
    summary["duplicate_content"] = {
        "urls_flagged_as_duplicate":        len(dupe_content),
        "exact_duplicate_groups_by_hash":   int(len(hash_dupes)),
    }

    # -- Thin content --------------------------------------------------------
    wc = df["word_count"].fillna(0).apply(safe_int)
    summary["content"] = {
        "thin_under_300_words": int((wc < 300).sum()),
        "thin_under_100_words": int((wc < 100).sum()),
        "zero_word_count":      int((wc == 0).sum()),
        "median_word_count":    int(wc.median()),
        "mean_word_count":      int(wc.mean()),
    }

    # -- Internal links / orphan pages ---------------------------------------
    il = df["inlinks"].fillna(0).apply(safe_int)
    summary["internal_links"] = {
        "orphan_pages_zero_inlinks": int((il == 0).sum()),
        "low_inlinks_1_to_3":        int(((il >= 1) & (il <= 3)).sum()),
        "median_inlinks":            float(il.median()),
    }

    # -- Performance ---------------------------------------------------------
    # Use ttfb_ms if available (Ahrefs), else fall back to response_time in ms (SF / Sitebulb)
    if "ttfb_ms" in df.columns and pd.to_numeric(df["ttfb_ms"], errors="coerce").fillna(0).sum() > 0:
        ttfb = pd.to_numeric(df["ttfb_ms"], errors="coerce").fillna(0).astype(int)
    elif "response_time" in df.columns:
        ttfb = (pd.to_numeric(df["response_time"], errors="coerce").fillna(0) * 1000).astype(int)
    else:
        ttfb = pd.Series([0] * len(df))

    load = pd.to_numeric(df["load_time_ms"], errors="coerce").fillna(0).astype(int) if "load_time_ms" in df.columns else pd.Series([0] * len(df))
    size = df["page_size_bytes"].fillna(0).apply(safe_int)
    summary["performance"] = {
        "slow_response_over_500ms":   int((ttfb > 500).sum()),
        "slow_response_over_1000ms":  int((ttfb > 1000).sum()),
        "slow_load_over_3s":          int((load > 3000).sum()),
        "large_pages_over_1mb":       int((size > 1_000_000).sum()),
        "large_pages_over_500kb":     int((size > 500_000).sum()),
        "median_response_ms":         int(ttfb.median()),
        "median_load_ms":             int(load.median()),
        "median_size_bytes":          int(size.median()),
    }

    # -- Structured data -----------------------------------------------------
    if "schema_items" in df.columns:
        schema_missing = df[df["schema_items"].isna() | (df["schema_items"].astype(str).str.strip().isin(["", "nan"]))]
        schema_issues  = df[df["structured_data_issues"].notna() & (df["structured_data_issues"].astype(str).str.strip() != "")] if "structured_data_issues" in df.columns else df.iloc[0:0]
    else:
        schema_missing = df.iloc[0:0]
        schema_issues  = df.iloc[0:0]
    summary["structured_data"] = {
        "pages_without_schema":       len(schema_missing),
        "pages_with_schema_issues":   len(schema_issues),
    }

    # -- Images alt text -----------------------------------------------------
    if "images_no_alt" in df.columns:
        img_no_alt = df[df["images_no_alt"].notna() & (df["images_no_alt"].astype(str).str.strip() != "")]
    else:
        img_no_alt = df.iloc[0:0]
    summary["images"] = {"pages_with_missing_alt": len(img_no_alt)}

    # -- Sitemap coverage ----------------------------------------------------
    if "in_sitemap" in df.columns:
        in_sitemap_mask = df["in_sitemap"].astype(str).str.lower().isin(["true", "yes", "1"])
        summary["sitemap"] = {
            "indexable_pages_in_sitemap":     int((in_sitemap_mask & indexable_mask).sum()),
            "indexable_pages_NOT_in_sitemap": int((~in_sitemap_mask & indexable_mask).sum()),
            "non_indexable_in_sitemap":       int((in_sitemap_mask & not_indexable_mask).sum()),
        }
    else:
        summary["sitemap"] = {"note": "not available for this crawl tool export"}

    # -- Meta robots ---------------------------------------------------------
    noindex_mask  = df["meta_robots"].astype(str).str.lower().str.contains("noindex",  na=False)
    nofollow_mask = df["meta_robots"].astype(str).str.lower().str.contains("nofollow", na=False)
    summary["meta_robots"] = {
        "noindex_count":  int(noindex_mask.sum()),
        "nofollow_count": int(nofollow_mask.sum()),
    }

    # -- URL quality ---------------------------------------------------------
    has_params    = df["url"].astype(str).str.contains(r'\?', na=False)
    has_uppercase = df["url"].astype(str).str.contains(r'[A-Z]', na=False)
    has_session   = df["url"].astype(str).str.contains(r'sessionid|phpsessid|jsessionid', case=False, na=False)
    summary["url_quality"] = {
        "urls_with_parameters": int(has_params.sum()),
        "urls_with_uppercase":  int(has_uppercase.sum()),
        "urls_with_session_ids": int(has_session.sum()),
    }

    return summary, {
        "title_missing":    title_missing,
        "title_short":      title_short,
        "title_long":       title_long,
        "title_dupes_df":   df[df["title"].isin(title_dupes.index)].sort_values("title"),
        "md_missing":       md_missing,
        "md_short":         md_short,
        "md_long":          md_long,
        "h1_missing":       h1_missing,
        "canon_broken":     canon_broken,
        "canon_other":      canon_other,
        "redirect_chains":  chains,
        "redirect_loops":   loops,
        "dupe_content":     dupe_content,
        "thin_content":     df[wc < 300],
        "orphan_pages":     df[il == 0],
        "slow_ttfb":        df[ttfb > 500].sort_values("ttfb_ms" if "ttfb_ms" in df.columns and df["ttfb_ms"].sum() > 0 else "response_time", ascending=False) if ("ttfb_ms" in df.columns or "response_time" in df.columns) else df.iloc[0:0],
        "large_pages":      df[size > 500_000].sort_values("page_size_bytes", ascending=False),
        "schema_issues":    schema_issues,
        "not_indexable":    df[not_indexable_mask],
        "img_no_alt":       img_no_alt,
        "noindex_pages":    df[noindex_mask],
        "not_in_sitemap":   df[~in_sitemap_mask & indexable_mask] if "in_sitemap" in df.columns else df.iloc[0:0],
        "urls_with_params": df[has_params],
        "4xx_pages":        df[df["status_code"].apply(safe_int).between(400, 499)],
        "5xx_pages":        df[df["status_code"].apply(safe_int).between(500, 599)],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",   required=True, help="Raw crawl CSV (Ahrefs, Screaming Frog, or Sitebulb)")
    parser.add_argument("--out-dir", default=None,  help="Output directory (default: same folder as input)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    out_dir    = Path(args.out_dir).resolve() if args.out_dir else input_path.parent
    issues_dir = out_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading {input_path} …", flush=True)
    try:
        df_raw = pd.read_csv(input_path, low_memory=False)
    except Exception as e:
        sys.exit(f"ERROR reading CSV: {e}")

    print(f"  {len(df_raw):,} rows, {len(df_raw.columns)} columns")

    # -- Detect tool and normalise columns -----------------------------------
    tool = detect_tool(df_raw.columns.tolist())
    print(f"  Detected tool: {tool}")

    if tool == "screaming_frog":
        df_raw.rename(columns=SCREAMING_FROG_MAP, inplace=True)
        if "indexable" in df_raw.columns:
            df_raw["indexable"] = df_raw["indexable"].map(
                lambda x: "true" if safe_str(x).lower() == "indexable" else "false"
            )
    elif tool == "sitebulb":
        df_raw.rename(columns=SITEBULB_MAP, inplace=True)
        if "indexable" in df_raw.columns:
            df_raw["indexable"] = df_raw["indexable"].map(
                lambda x: "true" if safe_str(x).lower() in ("yes", "true", "1", "indexable") else "false"
            )
        if "response_time" in df_raw.columns:
            df_raw["response_time"] = pd.to_numeric(df_raw["response_time"], errors="coerce") / 1000
    elif tool == "ahrefs":
        df_raw.rename(columns=AHREFS_COL_MAP, inplace=True)
        if "indexable" in df_raw.columns:
            df_raw["indexable"] = df_raw["indexable"].astype(str).str.lower()
    else:
        print("WARNING: Could not detect tool from headers. Columns will not be normalised.")
        url_candidates = [c for c in df_raw.columns if c.lower() in ("url", "address")]
        if url_candidates:
            df_raw.rename(columns={url_candidates[0]: "url"}, inplace=True)

    # -- Build slim dataframe ------------------------------------------------
    for col in SLIM_COLS:
        if col not in df_raw.columns:
            df_raw[col] = None

    df = df_raw[SLIM_COLS].copy()
    df["status_code"]     = pd.to_numeric(df["status_code"],     errors="coerce").fillna(0).astype(int)
    df["organic_traffic"] = pd.to_numeric(df["organic_traffic"], errors="coerce").fillna(0).astype(int)

    # -- Run analysis --------------------------------------------------------
    print("Analysing …", flush=True)
    summary, issue_dfs = analyse(df)
    summary["source_tool"] = tool

    # -- Write summary JSON --------------------------------------------------
    summary_path = out_dir / "audit_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Written: {summary_path}")

    # -- Write slim CSV ------------------------------------------------------
    slim_path = out_dir / "slim.csv"
    df.to_csv(slim_path, index=False)
    print(f"  Written: {slim_path}  ({slim_path.stat().st_size / 1_000_000:.1f} MB)")

    # -- Write per-issue CSVs ------------------------------------------------
    ISSUE_CONFIGS = {
        "title_missing":    (["url", "status_code", "indexable", "organic_traffic"], 2000),
        "title_short":      (["url", "title", "status_code", "organic_traffic"], 2000),
        "title_long":       (["url", "title", "status_code", "organic_traffic"], 2000),
        "title_dupes_df":   (["url", "title", "status_code", "organic_traffic"], 2000),
        "md_missing":       (["url", "status_code", "organic_traffic", "indexable"], 2000),
        "md_short":         (["url", "meta_description", "status_code", "organic_traffic"], 2000),
        "md_long":          (["url", "meta_description", "status_code", "organic_traffic"], 2000),
        "h1_missing":       (["url", "status_code", "organic_traffic", "indexable"], 2000),
        "canon_broken":     (["url", "canonical", "canonical_status_code", "organic_traffic"], 2000),
        "canon_other":      (["url", "canonical", "organic_traffic", "indexable"], 2000),
        "redirect_chains":  (["url", "redirect_chain", "redirect_url", "organic_traffic"], 2000),
        "redirect_loops":   (["url", "redirect_chain", "organic_traffic"], 500),
        "dupe_content":     (["url", "content_hash", "duplicate_count", "organic_traffic"], 2000),
        "thin_content":     (["url", "word_count", "status_code", "organic_traffic", "indexable"], 2000),
        "orphan_pages":     (["url", "inlinks", "status_code", "organic_traffic", "indexable"], 2000),
        "slow_ttfb":        (["url", "ttfb_ms", "load_time_ms", "response_time", "page_size_bytes", "organic_traffic"], 2000),
        "large_pages":      (["url", "page_size_bytes", "load_time_ms", "response_time", "organic_traffic"], 2000),
        "schema_issues":    (["url", "schema_items", "structured_data_issues", "organic_traffic"], 2000),
        "not_indexable":    (["url", "status_code", "meta_robots", "canonical", "organic_traffic"], 2000),
        "img_no_alt":       (["url", "images_no_alt", "organic_traffic"], 2000),
        "noindex_pages":    (["url", "meta_robots", "organic_traffic", "indexable"], 2000),
        "not_in_sitemap":   (["url", "status_code", "organic_traffic", "inlinks"], 2000),
        "urls_with_params": (["url", "status_code", "organic_traffic", "indexable"], 2000),
        "4xx_pages":        (["url", "status_code", "inlinks", "organic_traffic"], 2000),
        "5xx_pages":        (["url", "status_code", "inlinks", "organic_traffic"], 500),
    }

    for name, (cols, cap) in ISSUE_CONFIGS.items():
        subset = issue_dfs.get(name)
        if subset is None or len(subset) == 0:
            continue
        if "organic_traffic" in subset.columns:
            subset = subset.sort_values("organic_traffic", ascending=False)
        keep_cols = [c for c in cols if c in subset.columns]
        out_path = issues_dir / f"{name}.csv"
        subset[keep_cols].head(cap).to_csv(out_path, index=False)
        print(f"  Issue CSV: {name}.csv  ({len(subset):,} rows → {min(len(subset), cap):,} saved)")

    print(f"\nDone. Source tool: {tool}. Outputs in: {out_dir}")
    print(f"Next step: read audit_summary.json for the full analysis picture.")


if __name__ == "__main__":
    main()
