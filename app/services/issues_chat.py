# issues_chat.py

import requests
from typing import List, Dict, Optional, Any


GITHUB_API_BASE = "https://api.github.com"


def fetch_issue_documents(
    repo_full_name: str,
    issue_number: int,
    include_comments: bool = True,
    github_token: Optional[str] = None,
) -> List[Dict]:
    """
    Fetches a GitHub issue and (optionally) its comments
    and converts them into RAG-friendly documents.
    """

    headers = {
        "Accept": "application/vnd.github+json"
    }
    
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    # 1️⃣ Fetch issue
    issue_url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{issue_number}"
    issue_resp = requests.get(issue_url, headers=headers)
    issue_resp.raise_for_status()
    issue = issue_resp.json()

    documents = [
        {
            "content": (
                f"Issue Title: {issue.get('title')}\n\n"
                f"Issue Body:\n{issue.get('body', '')}"
            ),
            "source": f"issue#{issue_number}",
        }
    ]

    # 2️⃣ Fetch comments (optional)
    if include_comments and issue.get("comments", 0) > 0:
        comments_resp = requests.get(issue["comments_url"], headers=headers)
        comments_resp.raise_for_status()

        for idx, comment in enumerate(comments_resp.json(), start=1):
            documents.append({
                "content": comment.get("body", ""),
                "source": f"comment#{idx}",
            })

    return documents


def fetch_repository_issues(
    repo_full_name: str,
    github_token: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Fetch recent issues from the repository with metadata only.
    Hard capped at `limit` (default 100).
    """
    headers = {
        "Accept": "application/vnd.github+json"
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    issues = []
    page = 1
    per_page = 50 
    
    # Safety: Max pages to fetch based on limit
    max_pages = (limit // per_page) + (1 if limit % per_page > 0 else 0)

    try:
        while page <= max_pages:
            url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues"
            params = {
                "state": "all",
                "sort": "updated", 
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }

            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            
            batch = resp.json()
            if not batch:
                break
                
            # Filter out PRs (GitHub API returns PRs as issues too)
            real_issues = [i for i in batch if "pull_request" not in i]
            issues.extend(real_issues)
            
            if len(batch) < per_page:
                break
                
            page += 1
            
            if len(issues) >= limit:
                issues = issues[:limit]
                break
                
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Fetching repo issues failed: {e}")
        # We re-raise as ValueError to be caught by the router
        raise ValueError(f"Failed to fetch issues from GitHub: {str(e)}")

    return issues


def filter_issues_by_query(
    issues: List[Dict],
    query: str,
    repo_full_name: str,
    github_token: Optional[str] = None
) -> str:
    """
    Filter issues based on user query and return a formatted summary string.
    Implements intelligent intent detection.
    """
    q = query.lower()
    
    # Intent Detection
    check_most_commented = "most comments" in q or "most discussed" in q
    check_needs_info = any(p in q for p in ["asked for info", "need more info", "waiting for info"])
    check_unresolved = "unresolved" in q or "question" in q
    check_disagreement = "disagree" in q or "controversial" in q or "alternative" in q
    check_workaround = "workaround" in q or "temporary fix" in q
    
    detailed_results = []
    
    if check_most_commented:
        # Sort by comments descending
        sorted_issues = sorted(issues, key=lambda x: x.get("comments", 0), reverse=True)
        # Top 5
        top_issues = sorted_issues[:5]
        
        for issue in top_issues:
             extra = f" ({issue['comments']} comments)"
             detailed_results.append((issue, extra))
             
    else:
        # For other queries or general search, we might need deep scan.
        # Let's process top 20 recent issues for deep scan candidates if needed.
        candidates = issues[:20]
        
        headers = {"Accept": "application/vnd.github+json"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"
            
        MAX_DEEP_FETCH = 10
        deep_fetch_count = 0
        
        needs_deep_scan = check_needs_info or check_unresolved or check_disagreement or check_workaround

        for issue in candidates:
            matched = False
            extra_info = ""
            
            if not needs_deep_scan:
                # If no specific intent, include the issue by default
                matched = True
            
            elif deep_fetch_count < MAX_DEEP_FETCH:
                 try:
                    comments_url = issue["comments_url"]
                    if issue["comments"] > 0:
                        c_resp = requests.get(comments_url, headers=headers)
                        if c_resp.status_code == 200:
                            comments = c_resp.json()
                            comments_text = " ".join([c.get("body", "").lower() for c in comments])
                            
                            if check_needs_info:
                                phrases = ["please provide", "need more info", "can you clarify", "steps to reproduce"]
                                if any(p in comments_text for p in phrases):
                                    matched = True
                                    extra_info += " [Needs Info]"

                            if check_unresolved:
                                if issue["state"] == "open":
                                    if comments:
                                        last_comment = comments[-1].get("body", "").strip()
                                        if "?" in last_comment:
                                             matched = True
                                             extra_info += " [Unresolved Question]"
                                    elif "?" in issue.get("body", ""): 
                                         matched = True
                                         extra_info += " [Unresolved Question]"

                            if check_disagreement:
                                phrases = ["i disagree", "not the right approach", "we should not", "alternative solution"]
                                if any(p in comments_text for p in phrases):
                                    matched = True
                                    extra_info += " [Disagreement]"

                            if check_workaround:
                                 phrases = ["workaround", "temporary fix", "until fixed", "for now you can"]
                                 if any(p in comments_text for p in phrases):
                                     matched = True
                                     extra_info += " [Workaround]"
                            
                            deep_fetch_count += 1
                    elif check_unresolved and issue["state"] == "open" and "?" in issue.get("body", ""):
                        # Handle case with 0 comments but unresolved question in body
                        matched = True
                        extra_info += " [Unresolved Question]"
                        
                 except Exception:
                    pass

            if matched:
                detailed_results.append((issue, extra_info))

    # 3. Format Output
    if not detailed_results:
        return "No matching issues found for your query. Try asking something else."

    lines = [f"Found {len(detailed_results)} matching issues:"]
    for issue, extra in detailed_results[:20]:
        date_str = issue.get("created_at", "")[:10]
        state_icon = "🟢" if issue["state"] == "open" else "🟣"
        lines.append(f"{state_icon} #{issue['number']} {issue['title']} ({date_str}){extra}")
    
    if len(detailed_results) > 20:
        lines.append(f"... and {len(detailed_results) - 20} more.")

    return "\n".join(lines)
