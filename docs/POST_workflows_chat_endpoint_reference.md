# POST /workflows/chat — Endpoint Reference

> **Figma Design Blueprint** — Chat with GitHub Actions workflows and runs.

---

## Overview

| Property       | Value                                              |
|----------------|----------------------------------------------------|
| **Method**     | `POST`                                             |
| **Path**       | `/workflows/chat`                                  |
| **Auth**       | API Key (`X-API-Key` header)                       |
| **Scopes**     | Workflow chat scopes                               |
| **Rate Limit** | Yes (endpoint-type: `chat`)                        |
| **Purpose**    | AI conversation about CI/CD workflows and runs     |

---

## Request

### Headers

| Header       | Type     | Required | Description                        |
|--------------|----------|----------|------------------------------------|
| `X-API-Key`  | `string` | ✅ Yes   | API key with workflow scopes       |
| `Content-Type` | `string` | ✅ Yes | `application/json`                 |

### Request Body

```json
{
  "repo_id": "b44bd5ed97fb1c25",
  "workflow_id": "ci.yml",
  "run_id": "12345678",
  "question": "Why did this workflow run fail?",
  "chat_id": "chat_wf_01",
  "include_logs": true
}
```

### Field Details

| Field          | Type              | Required | Default  | Description                                      |
|----------------|-------------------|----------|----------|--------------------------------------------------|
| `repo_id`      | `string`          | ✅ Yes   | —        | Registered repository ID                         |
| `question`     | `string`          | ✅ Yes   | —        | Question about the workflow(s)                   |
| `workflow_id`  | `string \| null`  | ❌ No    | `null`   | Specific workflow file name                      |
| `run_id`       | `string \| null`  | ❌ No    | `null`   | Specific workflow run ID for deep analysis       |
| `chat_id`      | `string \| null`  | ❌ No    | `null`   | Chat session ID                                  |
| `include_logs` | `boolean`         | ❌ No    | `false`  | Include raw workflow logs in analysis            |

---

## Scope Behavior (3 Levels)

```
┌──────────────────────────────┐
│  repo_id ONLY                │ → High-level workflow analysis
│  (no workflow_id, no run_id) │   (all workflows overview)
├──────────────────────────────┤
│  repo_id + workflow_id       │ → Aggregate workflow run analysis
│  (no run_id)                 │   (history, success rate, trends)
├──────────────────────────────┤
│  repo_id + run_id            │ → Deep run analysis
│                              │   (logs, steps, timing, errors)
└──────────────────────────────┘
```

---

## Response (200 OK)

```json
{
  "answer": "The CI workflow failed at the 'Test' step due to...",
  "sources": ["workflow_run_12345", "step_3_logs"],
  "metadata": {
    "workflow_name": "CI Pipeline",
    "run_status": "failure",
    "analyzed_at": "2026-03-02T09:28:00Z"
  }
}
```

### Field Details

| Field      | Type       | Description                               |
|------------|------------|-------------------------------------------|
| `answer`   | `string`   | AI-generated workflow analysis            |
| `sources`  | `string[]` | Source references                         |
| `metadata` | `object`   | Additional context about the analysis     |

---

## Error Responses

| Code | Detail                     | Trigger                        |
|------|----------------------------|--------------------------------|
| 401  | Invalid or missing API key | Bad/missing `X-API-Key`        |
| 403  | Insufficient scopes        | Missing workflow scopes        |
| 429  | Rate limit exceeded        | Rate limit hit                 |

---

## Figma Design Checklist

- [ ] Header card — `POST` badge + `/workflows/chat`
- [ ] **3-level scope diagram** — repo-only → workflow → run
- [ ] `include_logs` toggle highlight
- [ ] Response body with `metadata` object
- [ ] Error state cards
