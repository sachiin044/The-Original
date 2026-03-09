# POST /pull-requests/chat — Endpoint Reference

> **Figma Design Blueprint** — Chat about Pull Requests (single PR or repo-level).

---

## Overview

| Property       | Value                                              |
|----------------|----------------------------------------------------|
| **Method**     | `POST`                                             |
| **Path**       | `/pull-requests/chat`                              |
| **Auth**       | API Key (`X-API-Key` header)                       |
| **Rate Limit** | No                                                 |
| **Purpose**    | AI conversation about PRs — diff analysis, reviews, CI status, intent, and risk |

---

## Request

### Headers

| Header       | Type     | Required | Description              |
|--------------|----------|----------|--------------------------|
| `X-API-Key`  | `string` | ✅ Yes   | Valid API key             |
| `Content-Type` | `string` | ✅ Yes | `application/json`       |

### Request Body

```json
{
  "repo_id": "b44bd5ed97fb1c25",
  "pr_number": 42,
  "message": "What does this PR change and is it risky?",
  "chat_id": "chat_303",
  "context": {
    "include_diff": true,
    "include_checks": true
  }
}
```

### Field Details

| Field        | Type              | Required | Default   | Description                                              |
|--------------|-------------------|----------|-----------|----------------------------------------------------------|
| `repo_id`    | `string`          | ✅ Yes   | —         | Registered repository ID                                 |
| `message`    | `string`          | ✅ Yes   | —         | Question about the PR(s)                                 |
| `pr_number`  | `integer \| null` | ❌ No    | `null`    | Specific PR number. Omit for repo-level queries          |
| `chat_id`    | `string \| null`  | ❌ No    | Auto UUID | Chat session ID                                          |
| `context`    | `object \| null`  | ❌ No    | `null`    | `include_diff` (bool), `include_checks` (bool)           |

---

## Two Modes

```
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│       SINGLE PR MODE             │    │       REPO-LEVEL MODE            │
│    (pr_number provided)          │    │    (pr_number omitted)           │
│                                  │    │                                  │
│  • Fetches PR metadata + diff    │    │  • Fetches top 100 PRs           │
│  • Fetches CI checks & reviews   │    │  • Filters by natural language   │
│  • Builds temp vector store      │    │  • Deep-fetches up to 10 PRs     │
│  • RAG answer via GPT-4o-mini    │    │  • Returns formatted summary     │
│  • tokens_used = integer         │    │  • tokens_used = 0               │
└──────────────────────────────────┘    └──────────────────────────────────┘
```

---

## Response (200 OK)

```json
{
  "chat_id": "chat_303",
  "reply": "PR #42 refactors the auth module to use JWT tokens...",
  "sources": ["pr_body", "diff_chunk_5", "ci_check"],
  "tokens_used": 1100,
  "created_at": "2026-03-02T09:22:00Z"
}
```

### Field Details

| Field        | Type        | Description                                   |
|--------------|-------------|-----------------------------------------------|
| `chat_id`    | `string`    | Session ID                                    |
| `reply`      | `string`    | AI-generated analysis                         |
| `sources`    | `string[]`  | Source references used                        |
| `tokens_used`| `integer`   | Tokens consumed (0 for repo-level)            |
| `created_at` | `string`    | ISO 8601 timestamp                            |

---

## Error Responses

| Code | Detail                             | Trigger                        |
|------|------------------------------------|--------------------------------|
| 401  | Invalid or missing API key         | Bad/missing `X-API-Key`        |
| 403  | GitHub credential not verified     | PAT status is not validated    |
| 404  | Repository not registered          | Unknown `repo_id`              |
| 502  | (dynamic message)                  | GitHub API failure             |

---

## Figma Design Checklist

- [ ] Header card — `POST` badge + `/pull-requests/chat`
- [ ] Two-mode diagram — Single PR vs Repo-Level
- [ ] Context options — `include_diff` + `include_checks` toggles
- [ ] Response body — show sources include diff chunks and CI checks
- [ ] Error state cards
