# POST /issues/chat — Endpoint Reference

> **Figma Design Blueprint** — Chat about GitHub issues (single issue or repo-level).

---

## Overview

| Property       | Value                                              |
|----------------|----------------------------------------------------|
| **Method**     | `POST`                                             |
| **Path**       | `/issues/chat`                                     |
| **Auth**       | API Key (`X-API-Key` header)                       |
| **Rate Limit** | No                                                 |
| **Purpose**    | AI conversation about GitHub issues — single-issue deep dive or repo-level issue query |

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
  "issue_number": 128,
  "chat_id": "chat_202",
  "message": "Summarize this issue and possible fixes",
  "context": {
    "include_comments": true,
    "depth": "medium"
  }
}
```

### Field Details

| Field          | Type              | Required | Default                                    | Description                                         |
|----------------|-------------------|----------|--------------------------------------------|-----------------------------------------------------|
| `repo_id`      | `string`          | ✅ Yes   | —                                          | Registered repository ID                            |
| `message`      | `string`          | ✅ Yes   | —                                          | Question about the issue(s)                         |
| `issue_number` | `integer \| null` | ❌ No    | `null`                                     | Specific issue number. Omit for repo-level queries  |
| `chat_id`      | `string \| null`  | ❌ No    | Auto UUID                                  | Chat session ID                                     |
| `context`      | `object \| null`  | ❌ No    | `{"include_comments": true, "depth": "medium"}` | Controls comment inclusion and analysis depth |

---

## Two Modes

```
┌────────────────────────────────┐    ┌────────────────────────────────┐
│      SINGLE ISSUE MODE         │    │      REPO-LEVEL MODE           │
│   (issue_number provided)      │    │   (issue_number omitted)       │
│                                │    │                                │
│  • Fetches issue + comments    │    │  • Fetches top 100 issues      │
│  • Builds temp vector store    │    │  • Filters by natural language │
│  • RAG answer via GPT-4o-mini  │    │  • Returns matching issues     │
│  • tokens_used = integer       │    │  • tokens_used = 0             │
└────────────────────────────────┘    └────────────────────────────────┘
```

---

## Response (200 OK)

```json
{
  "chat_id": "chat_202",
  "reply": "Issue #128 is a NullPointerException in the parser module...",
  "sources": ["issue_body", "comment_3"],
  "tokens_used": 850,
  "created_at": "2026-03-02T09:20:00Z"
}
```

### Field Details

| Field        | Type        | Description                                   |
|--------------|-------------|-----------------------------------------------|
| `chat_id`    | `string`    | Session ID                                    |
| `reply`      | `string`    | AI-generated answer                           |
| `sources`    | `string[]`  | Source references                              |
| `tokens_used`| `integer`   | Tokens consumed (0 for repo-level)            |
| `created_at` | `string`    | ISO 8601 timestamp                            |

---

## Error Responses

| Code | Detail                           | Trigger                        |
|------|----------------------------------|--------------------------------|
| 401  | Invalid or missing API key       | Bad/missing `X-API-Key`        |
| 404  | Repository not registered        | Unknown `repo_id`              |
| 502  | (dynamic message)                | GitHub API failure             |

---

## Figma Design Checklist

- [ ] Header card — `POST` badge + `/issues/chat`
- [ ] Two-mode diagram — Single Issue vs Repo-Level
- [ ] Request body — highlight `issue_number` as the mode toggle
- [ ] Context options — show `include_comments` + `depth`
- [ ] Response body with example
- [ ] Error state cards
