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


FALLBACK_REPOSITORIES: list[dict[str, Any]] = [
    {
        "name": "langchain",
        "url": "https://github.com/langchain-ai/langchain",
        "description": "Framework for building LLM apps and tool-using agents.",
        "language": "Python",
        "stars": None,
        "tags": {"tool", "production", "both", "python"},
    },
    {
        "name": "crewai",
        "url": "https://github.com/crewAIInc/crewAI",
        "description": "Multi-agent orchestration framework.",
        "language": "Python",
        "stars": None,
        "tags": {"multi-agent", "orchestration", "production", "both", "python"},
    },
    {
        "name": "autogen",
        "url": "https://github.com/microsoft/autogen",
        "description": "Programming framework for agentic AI and multi-agent workflows.",
        "language": "Python",
        "stars": None,
        "tags": {"multi-agent", "tool", "research", "both", "python"},
    },
    {
        "name": "semantic-kernel",
        "url": "https://github.com/microsoft/semantic-kernel",
        "description": "SDK for building AI agents and copilots.",
        "language": "C#",
        "stars": None,
        "tags": {"tool", "production", "both", "c#"},
    },
]


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

    terms.extend(["stars:>100", "archived:false"])
    return " ".join(terms)


def _search_github(query: str, language: str | None, limit: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    q = query
    if language:
        q = f"{q} language:{language}"

    try:
        response = requests.get(
            GITHUB_SEARCH_URL,
            params={"q": q, "sort": "stars", "order": "desc", "per_page": limit},
            headers={"Accept": "application/vnd.github+json"},
            timeout=15,
        )
    except requests.RequestException as exc:
        return [], f"network_error:{exc.__class__.__name__}"

    if response.status_code != 200:
        return [], f"github_status:{response.status_code}"

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

    return repositories, None


def _fallback_repositories(constraints: dict[str, str], limit: int = 5) -> list[dict[str, Any]]:
    agent_type = constraints.get("agent_type")
    language = constraints.get("language")
    maturity = constraints.get("maturity")

    scored: list[tuple[int, dict[str, Any]]] = []
    for repo in FALLBACK_REPOSITORIES:
        score = 0
        tags = repo["tags"]

        if agent_type and agent_type in tags:
            score += 3
        if language and language == str(repo.get("language", "")).lower():
            score += 2
        if maturity and maturity in tags:
            score += 2

        scored.append((score, repo))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: list[dict[str, Any]] = []
    for score, repo in scored:
        if score <= 0 and len(results) >= 2:
            continue

        results.append(
            {
                "name": repo["name"],
                "url": repo["url"],
                "description": repo["description"],
                "language": repo["language"],
                "stars": repo["stars"],
            }
        )
        if len(results) >= limit:
            break

    return results


def handle_search_turn(message: str, conversation: list[str]) -> dict[str, Any]:
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
    repositories, search_error = _search_github(
        query=query,
        language=constraints.get("language"),
        limit=8,
    )

    if repositories:
        return {
            "reply": "Here are high-signal repositories based on your requirements.",
            "follow_up_question": None,
            "repositories": repositories,
            "constraints": constraints,
            "ready": True,
            "query_used": query,
            "result_source": "github",
        }

    fallback = _fallback_repositories(constraints, limit=5)
    if fallback:
        return {
            "reply": "I couldn't fetch live GitHub results right now, so here are curated matches you can use immediately.",
            "follow_up_question": None,
            "repositories": fallback,
            "constraints": constraints,
            "ready": True,
            "query_used": query,
            "result_source": "fallback",
            "search_error": search_error,
        }

    return {
        "reply": "I couldn't find matching repositories yet. Want to broaden requirements (any language or prototype-ready)?",
        "follow_up_question": "Should I broaden the search to any language and include prototype-friendly repositories?",
        "repositories": [],
        "constraints": constraints,
        "ready": False,
        "query_used": query,
        "search_error": search_error,
    }
