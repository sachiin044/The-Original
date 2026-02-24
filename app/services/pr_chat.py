import requests
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dateutil import parser
import pytz

GITHUB_API_BASE = "https://api.github.com"

def fetch_pr_documents(
    repo_full_name: str,
    pr_number: int,
    github_token: Optional[str] = None,
    include_diff: bool = True,
    include_checks: bool = True,
) -> List[Dict]:

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    documents = []

    # 1️⃣ Fetch PR metadata
    pr_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}"
    
    try:
        pr_resp = requests.get(pr_url, headers=headers)
        pr_resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Pull Request #{pr_number} not found in {repo_full_name}. If private, ensure valid credentials.")
        if e.response.status_code == 403:
            raise ValueError(f"Access denied to {repo_full_name}. Rate limit exceeded or invalid credentials.")
        raise e
    pr = pr_resp.json()

    documents.append({
        "content": (
            f"PR Title: {pr.get('title')}\n\n"
            f"PR Body:\n{pr.get('body', '')}\n\n"
            f"Base Branch: {pr.get('base', {}).get('ref')}\n"
            f"Head Branch: {pr.get('head', {}).get('ref')}\n"
            f"State: {pr.get('state')}\n"
            f"Merged: {pr.get('merged')}"
        ),
        "source": f"pull_request#{pr_number}"
    })

    # 2️⃣ Fetch diff (optional)
    if include_diff:
        diff_headers = headers.copy()
        diff_headers["Accept"] = "application/vnd.github.v3.diff"
        diff_resp = requests.get(
            pr_url,
            headers=diff_headers
        )
        if diff_resp.status_code == 200:
            documents.append({
                "content": diff_resp.text,
                "source": f"pull_request_diff#{pr_number}"
            })

    # 3️⃣ Fetch check runs (optional)
    if include_checks:
        checks_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits/{pr['head']['sha']}/check-runs"
        checks_resp = requests.get(checks_url, headers=headers)
        if checks_resp.status_code == 200:
            checks = checks_resp.json().get("check_runs", [])
            summary = "\n".join(
                f"{c['name']} - {c['conclusion']}"
                for c in checks
            )
            documents.append({
                "content": summary,
                "source": ".github/workflows"
            })

    return documents


def fetch_repository_prs(
    repo_full_name: str,
    github_token: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Fetch recent PRs from the repository with metadata only.
    Hard capped at `limit` (default 100).
    """
    print("Using token:", bool(github_token))
    print("Token length:", len(github_token) if github_token else 0)
    headers = {
        "Accept": "application/vnd.github+json"
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    prs = []
    page = 1
    per_page = 50 
    
    # Safety: Max pages to fetch based on limit
    max_pages = (limit // per_page) + (1 if limit % per_page > 0 else 0)

    try:
        while page <= max_pages:
            url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls"
            params = {
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }

            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            
            batch = resp.json()
            if not batch:
                break
                
            prs.extend(batch)
            
            if len(batch) < per_page:
                break
                
            page += 1
            
            if len(prs) >= limit:
                prs = prs[:limit]
                break
                
    except requests.exceptions.RequestException as e:
        # Return a clear error message instead of raw traceback
        print(f"[ERROR] Fetching repo PRs failed: {e}")
        # We re-raise as ValueError to be caught by the router and turned into HTTPException
        raise ValueError(f"Failed to fetch PRs from GitHub: {str(e)}")

    return prs


def filter_prs_by_query(
    prs: List[Dict],
    query: str,
    repo_full_name: str,
    github_token: Optional[str] = None
) -> str:
    """
    Filter PRs based on user query and return a formatted summary string.
    Includes intelligent intent detection to limit deep fetching.
    """
    q = query.lower()
    
    # 1. Intent Detection
    needs_files = any(w in q for w in ["touched", "modified", "changed", "file", "path"])
    needs_reviews = any(w in q for w in ["review", "approved", "changes requested", "commented"])
    
    # Date filtering keywords
    check_merged = "merged" in q
    check_last_week = "last week" in q
    
    # Performance keywords
    perf_keywords = ["performance", "optimize", "optimization", "latency", "speed", "efficiency", "throughput"]
    check_perf = any(k in q for k in perf_keywords)

    filtered_prs = []
    
    # 2. Metadata Filtering (In-Memory)
    now_utc = datetime.now(pytz.utc)

    for pr in prs:
        # Basic fields
        title = pr.get("title", "")
        body = pr.get("body") or ""
        state = pr.get("state", "")
        merged_at_str = pr.get("merged_at")
        
        # Merge status check
        if check_merged and not merged_at_str:
            continue
            
        # Date check (Last Week)
        if check_last_week and merged_at_str:
            try:
                merged_at = parser.parse(merged_at_str)
                # Ensure UTC
                if merged_at.tzinfo is None:
                    merged_at = merged_at.replace(tzinfo=pytz.utc)
                
                # Precise timedelta comparison
                if now_utc - merged_at > timedelta(days=7):
                    continue
            except Exception:
                pass # skip date error
        
        # Performance Keyword Prioritization
        # If query is about performance, ONLY keep PRs that mention it
        if check_perf:
             content_text = (title + " " + body).lower()
             if not any(k in content_text for k in perf_keywords):
                 # If explicit performance query, strictly filter metadata first
                 continue

        # Keyword match (simple)
        # If specific keywords are present, filter by them
        if "auth" in q:
             if "auth" not in title.lower() and "auth" not in body.lower():
                 if not needs_files:
                    continue

        filtered_prs.append(pr)

    # 3. Deep Fetching (Conditional & Capped)
    detailed_results = []
    
    # Cap deep fetch to top 10 to avoid rate limits
    MAX_DEEP_FETCH = 10
    deep_fetch_count = 0
    
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    for pr in filtered_prs:
        pr_number = pr["number"]
        match = True
        extra_info = ""

        # File Check
        if needs_files and deep_fetch_count < MAX_DEEP_FETCH:
            try:
                files_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/files"
                f_resp = requests.get(files_url, headers=headers)
                if f_resp.status_code == 200:
                    files = f_resp.json()
                    filenames = [f["filename"].lower() for f in files]
                    
                    query_terms = [t for t in q.split() if len(t) > 3] 
                    file_match = False
                    for term in query_terms:
                        if any(term in fn for fn in filenames):
                            file_match = True
                            extra_info += f" (Touched: {term})"
                            break
                    
                    if not file_match and "touched" in q:
                         match = False
                    
                    deep_fetch_count += 1
            except Exception:
                pass

        # Review Check
        if needs_reviews and deep_fetch_count < MAX_DEEP_FETCH and match:
            try:
                reviews_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/pulls/{pr_number}/reviews"
                r_resp = requests.get(reviews_url, headers=headers)
                if r_resp.status_code == 200:
                    reviews = r_resp.json()
                    # Filter for changes requested?
                    if "changes requested" in q:
                        has_changes_requested = any(r["state"] == "CHANGES_REQUESTED" for r in reviews)
                        if not has_changes_requested:
                            match = False
                        else:
                            extra_info += " [Changes Requested]"
                    
                    deep_fetch_count += 1
            except Exception:
                pass

        if match:
            detailed_results.append((pr, extra_info))

    # 4. Formatting Response
    if not detailed_results:
        return "No matching PRs found for your query."

    lines = [f"Found {len(detailed_results)} matching PRs:"]
    for pr, extra in detailed_results[:20]: # Show max 20 in chat
        date_str = pr.get("merged_at") or pr.get("created_at")
        date_display = date_str[:10] if date_str else "N/A"
        state_icon = "🟣" if pr.get("merged_at") else ("🟢" if pr["state"] == "open" else "🔴")
        
        lines.append(f"{state_icon} #{pr['number']} {pr['title']} ({date_display}){extra}")
    
    if len(detailed_results) > 20:
        lines.append(f"... and {len(detailed_results) - 20} more.")

    return "\n".join(lines)

