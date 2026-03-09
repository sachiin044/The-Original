from __future__ import annotations

from typing import Any
import requests

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


CLARIFICATION_RULES = [
    {
        "key": "agent_type",
        "question": "What type of AI agent do you want (chatbot, tool-using, autonomous, or multi-agent)?",
        "choices": ["chatbot", "tool", "autonomous", "multi-agent", "research", "orchestration"],
    },
    {
        "key": "language",
        "question": "Which programming language do you prefer (Python, TypeScript, Go, Rust, etc.)?",
        "choices": ["python", "typescript", "javascript", "go", "rust", "java", "c#"],
    },
    {
        "key": "maturity",
        "question": "Are you looking for prototype-friendly repos, production-ready repos, or both?",
        "choices": ["prototype", "production", "both"],
    },
]


KEYWORD_TO_TOPIC = {
    "tool": "tool-using agent",
    "multi-agent": "multi agent framework",
    "autonomous": "autonomous ai agent",
    "chatbot": "chatbot agent",
    "research": "agent research framework",
    "orchestration": "agent orchestration",
}


LANGUAGES = {"python", "typescript", "javascript", "go", "rust", "java", "c#"}


MATURITY_HINTS = {
    "prototype": "good first issues examples tutorial",
    "production": "production scalable orchestration observability",
    "both": "production examples",
}


def _extract_constraints(messages: list[str]) -> dict[str, str]:
    constraints: dict[str, str] = {}
    lowered = " ".join(messages).lower()

    for topic in KEYWORD_TO_TOPIC:
        if topic in lowered:
            constraints["agent_type"] = topic
            break

    for language in LANGUAGES:
        if language in lowered:
            constraints["language"] = language
            break

    for maturity in MATURITY_HINTS:
        if maturity in lowered:
            constraints["maturity"] = maturity
            break

    return constraints


def _build_github_query(constraints: dict[str, str], user_message: str) -> str:
    terms: list[str] = ["open source"]

    agent_type = constraints.get("agent_type")
    if agent_type:
        terms.append(KEYWORD_TO_TOPIC[agent_type])
    else:
        terms.append(user_message)

    maturity = constraints.get("maturity")
    if maturity:
        terms.append(MATURITY_HINTS[maturity])

    # Basic quality filters to reduce noisy repos.
    terms.extend(["stars:>100", "archived:false"])

    return " ".join(terms)


def _search_github(query: str, language: str | None, limit: int = 5) -> list[dict[str, Any]]:
    q = query
    if language:
        q = f"{q} language:{language}"

    response = requests.get(
        GITHUB_SEARCH_URL,
        params={"q": q, "sort": "stars", "order": "desc", "per_page": limit},
        headers={"Accept": "application/vnd.github+json"},
        timeout=15,
    )

    if response.status_code != 200:
        return []

    items = response.json().get("items", [])
    repositories: list[dict[str, Any]] = []
    for item in items:
        repositories.append(
            {
                "name": item.get("name"),
                "url": item.get("html_url"),
                "description": item.get("description"),
                "language": item.get("language"),
                "stars": item.get("stargazers_count"),
            }
        )

    return repositories


def handle_search_turn(message: str, conversation: list[str]) -> dict[str, Any]:
    """
    Simple conversational repository discovery turn handler.

    1) Parse current constraints from all conversation text.
    2) Ask one follow-up question if constraints are still missing.
    3) Once enough constraints exist, search GitHub and return curated repositories.
    """
    all_messages = [*conversation, message]
    constraints = _extract_constraints(all_messages)

    for rule in CLARIFICATION_RULES:
        if rule["key"] not in constraints:
            return {
                "reply": "Great start — I can find much better matches with one more detail.",
                "follow_up_question": rule["question"],
                "repositories": [],
                "constraints": constraints,
                "ready": False,
            }

    query = _build_github_query(constraints, message)
    repositories = _search_github(query=query, language=constraints.get("language"), limit=8)

    return {
        "reply": "Here are high-signal repositories based on your requirements.",
        "follow_up_question": None,
        "repositories": repositories,
        "constraints": constraints,
        "ready": True,
        "query_used": query,
    }
