# POST /agent/chat — Endpoint Reference

> **Figma Design Blueprint** — Autonomous AI investigation of GitHub repositories.

---

## Overview

| Property       | Value                                              |
|----------------|----------------------------------------------------|
| **Method**     | `POST`                                             |
| **Path**       | `/agent/chat`                                      |
| **Auth**       | API Key (`X-API-Key` header)                       |
| **Rate Limit** | No                                                 |
| **Purpose**    | LLM-driven agent autonomously investigates a GitHub repo using tool-calling |

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
  "query": "Why did the last CI build fail and are there any related open issues?"
}
```

### Field Details

| Field     | Type     | Required | Description                                    |
|-----------|----------|----------|------------------------------------------------|
| `repo_id` | `string` | ✅ Yes   | Registered repository ID                       |
| `query`   | `string` | ✅ Yes   | Natural language question about the repository |

---

## Response (200 OK)

```json
{
  "answer": "The last CI build failed due to a missing dependency in requirements.txt. Issue #45 reports the same error...",
  "steps": [
    {
      "iteration": 1,
      "tool": "get_failed_workflows",
      "args": { "repo_id": "b44bd5ed97fb1c25", "limit": 5 },
      "result": { "workflows": [...] },
      "error": null,
      "duration_ms": 1200
    },
    {
      "iteration": 2,
      "tool": "get_open_issues",
      "args": { "repo_id": "b44bd5ed97fb1c25" },
      "result": { "issues": [...] },
      "error": null,
      "duration_ms": 800
    }
  ],
  "sources": ["workflow_run_12345", "issue_45"],
  "tool_call_count": 2,
  "iterations_used": 2,
  "investigated_at": "2026-03-02T09:25:00Z"
}
```

### Field Details

| Field              | Type           | Description                                           |
|--------------------|----------------|-------------------------------------------------------|
| `answer`           | `string`       | Final synthesized answer from the agent                |
| `steps`            | `StepRecord[]` | Full execution trace of every tool call                |
| `sources`          | `string[]`     | Data sources referenced in the answer                  |
| `tool_call_count`  | `integer`      | Total number of tools invoked                          |
| `iterations_used`  | `integer`      | Number of LLM reasoning iterations                     |
| `investigated_at`  | `string`       | ISO 8601 timestamp                                     |

### StepRecord Schema

| Field         | Type           | Description                           |
|---------------|----------------|---------------------------------------|
| `iteration`   | `integer`      | Loop iteration number                 |
| `tool`        | `string`       | Tool name that was called             |
| `args`        | `object`       | Arguments passed to the tool          |
| `result`      | `object\|null` | Tool return value (null on error)     |
| `error`       | `string\|null` | Error message (null on success)       |
| `duration_ms` | `integer`      | Execution time in milliseconds        |

---

## Available Agent Tools

| Tool                    | Purpose                              |
|-------------------------|--------------------------------------|
| `get_failed_workflows`  | Fetch recent failed CI/CD runs       |
| `get_deployment_info`   | Fetch deployment status & history    |
| `get_recent_prs`        | Fetch recent pull requests           |
| `get_open_issues`       | Fetch open issues                    |

---

## Internal Flow

```
┌──────────────────────────────────────┐
│         POST /agent/chat             │
│         (User Query)                 │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│     GitHubAgentController            │
│                                      │
│  GPT-4o-mini with tool-calling API   │
│  ┌────────────────────────────────┐  │
│  │  LOOP (max N iterations):     │  │
│  │                               │  │
│  │  1. LLM picks a tool          │  │
│  │  2. Execute tool with timeout │  │
│  │  3. Return result to LLM      │  │
│  │  4. LLM decides: more tools   │  │
│  │     or final answer?          │  │
│  └────────────────────────────────┘  │
│                                      │
│  Failure recovery + step logging     │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Return: answer + full step trace    │
└──────────────────────────────────────┘
```

---

## Error Responses

| Code | Detail                    | Trigger                        |
|------|---------------------------|--------------------------------|
| 401  | Invalid or missing API key| Bad/missing `X-API-Key`        |

---

## Figma Design Checklist

- [ ] Header card — `POST` badge + `/agent/chat`
- [ ] Request body — simple 2-field input
- [ ] **Agent loop diagram** — show the autonomous tool-calling loop
- [ ] **Tool cards** — 4 available tools with descriptions
- [ ] **Step trace** — show the execution timeline with tool → result pairs
- [ ] Response body — highlight `steps[]` as the execution trace
