# POST /chat — Endpoint Reference

> **Figma Design Blueprint** — Use this document to design the API screen for the `/chat` endpoint.

---

## Overview

| Property       | Value                                         |
|----------------|-----------------------------------------------|
| **Method**     | `POST`                                        |
| **Path**       | `/chat`                                       |
| **Auth**       | API Key (`X-API-Key` header)                  |
| **Scopes**     | `repo:read`, `repo:explain`                   |
| **Rate Limit** | Yes (per-key, endpoint-type: `chat`)          |
| **Purpose**    | AI conversation with an indexed GitHub repo using RAG |

---

## Request

### Headers

| Header       | Type     | Required | Description                                |
|--------------|----------|----------|--------------------------------------------|
| `X-API-Key`  | `string` | ✅ Yes   | API key with chat scopes                   |
| `Content-Type` | `string` | ✅ Yes | Must be `application/json`                 |

### Request Body (JSON)

```json
{
  "message":  "Explain how the RAG pipeline works",
  "repo_id":  "b44bd5ed97fb1c25",
  "chat_id":  "chat_101",
  "context":  { "focus": "services" },
  "files":    ["app/services/rag.py"]
}
```

### Field Details

| Field      | Type              | Required | Default  | Description                                                        |
|------------|-------------------|----------|----------|--------------------------------------------------------------------|
| `message`  | `string`          | ✅ Yes   | —        | The user's question about the repository                           |
| `repo_id`  | `string`          | ✅ Yes   | —        | Unique ID of the registered & indexed repository                   |
| `chat_id`  | `string \| null`  | ❌ No    | Auto UUID | Session ID for multi-turn conversation. Auto-generated if omitted |
| `context`  | `object \| null`  | ❌ No    | `null`   | Optional context hints passed to the RAG pipeline                  |
| `files`    | `string[] \| null`| ❌ No    | `null`   | Optional list of file paths to focus the search on                 |

---

## Response (200 OK)

### Success Response Body

```json
{
  "chat_id":     "chat_101",
  "reply":       "The RAG pipeline works by embedding repo code into vectors...",
  "tokens_used": 1250,
  "sources":     ["app/services/rag.py", "app/services/embed.py"],
  "follow_ups":  [
    "How does the question router classify queries?",
    "What embedding model is used?"
  ],
  "created_at":  "2026-03-02T09:15:30.123456Z"
}
```

### Field Details

| Field        | Type              | Nullable | Description                                                   |
|--------------|-------------------|----------|---------------------------------------------------------------|
| `chat_id`    | `string`          | No       | Session ID (returned for subsequent messages)                 |
| `reply`      | `string`          | No       | AI-generated answer about the repository                      |
| `tokens_used`| `integer \| null` | Yes      | OpenAI tokens consumed (null for greetings/structural)        |
| `sources`    | `string[]`        | No       | Source file paths used to generate the answer                 |
| `follow_ups` | `string[]`        | No       | AI-suggested follow-up questions                              |
| `created_at` | `string`          | No       | ISO 8601 timestamp of response creation                       |

---

## Error Responses

### 404 — Repository Not Registered

```json
{
  "detail": "Repository not registered"
}
```
> Thrown when `repo_id` does not exist in the database.

### 400 — Repository Not Indexed

```json
{
  "detail": "Repository is not indexed yet. Please index it first."
}
```
> Thrown when the repository is registered but hasn't been indexed (no embeddings).

### 401 — Unauthorized

```json
{
  "detail": "Invalid or missing API key"
}
```
> Thrown when `X-API-Key` header is missing or the key is invalid/revoked.

### 429 — Rate Limited

```json
{
  "detail": "Rate limit exceeded"
}
```
> Thrown when the API key has exceeded its rate limit for the `chat` endpoint type.

---

## Internal Flow (for Architecture Diagram)

```
┌──────────────────────────────────────────────────────────┐
│                     POST /chat                            │
│                   (User Request)                          │
└─────────────────────────┬────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Auth Middleware      │
              │  • Verify X-API-Key   │
              │  • Check scopes       │
              │  • Rate limit check   │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Repo Guard          │
              │  • Exists in DB?      │
              │  • Is indexed?        │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Create/Resume Chat  │
              │  • chat_id (new/old)  │
              │  • Store user message │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Question Router     │
              │  Classify question:   │
              │  ┌─────────────────┐  │
              │  │ • GREETING      │  │
              │  │ • MEMORY        │  │
              │  │ • STRUCTURAL    │  │
              │  │ • SEMANTIC(RAG) │  │
              │  └─────────────────┘  │
              └───────────┬───────────┘
                          │
            ┌─────────────┼─────────────┬──────────────┐
            ▼             ▼             ▼              ▼
     ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐
     │ GREETING │ │   MEMORY     │ │STRUCTURAL│ │   SEMANTIC   │
     │          │ │              │ │          │ │   (RAG)      │
     │ Returns  │ │ Returns last │ │ Returns  │ │              │
     │ welcome  │ │ user question│ │ folder   │ │ Vector search│
     │ message  │ │ from history │ │ tree     │ │ → GPT-4o-mini│
     │          │ │              │ │          │ │ → Answer     │
     └────┬─────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘
          │              │              │              │
          └──────────────┴──────────────┴──────────────┘
                                  │
                                  ▼
                    ┌───────────────────────┐
                    │   Generate Follow-ups │
                    │  (AI-suggested next   │
                    │   questions)           │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Return Response     │
                    │  { chat_id, reply,    │
                    │    tokens, sources,   │
                    │    follow_ups }       │
                    └───────────────────────┘
```

---

## Question Routing Behavior

The endpoint classifies each message before processing:

| Route          | Trigger                                        | Response Style                        | tokens_used |
|----------------|------------------------------------------------|---------------------------------------|-------------|
| **GREETING**   | `"hi"`, `"hello"`, `"hey"`, etc.               | Static welcome message                | `null`      |
| **MEMORY**     | `"last question"`, `"what did I ask"`           | Echoes previous user question         | `0`         |
| **STRUCTURAL** | Questions about structure, folders, file tree   | Formatted folder tree from manifest   | `null`      |
| **SEMANTIC**   | Everything else (default)                       | RAG: vector search → GPT-4o-mini      | `integer`   |

---

## Example Conversations

### 1. First-time Chat (New Session)

**Request:**
```json
{
  "message": "What does this repository do?",
  "repo_id": "b44bd5ed97fb1c25"
}
```

**Response:**
```json
{
  "chat_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "reply": "This repository is a FastAPI-based GitHub analysis tool that...",
  "tokens_used": 980,
  "sources": ["README.md", "app/main.py"],
  "follow_ups": [
    "What technologies does it use?",
    "How is the project structured?"
  ],
  "created_at": "2026-03-02T09:16:00Z"
}
```

### 2. Greeting

**Request:**
```json
{
  "message": "hi",
  "repo_id": "b44bd5ed97fb1c25",
  "chat_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response:**
```json
{
  "chat_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "reply": "Hi 👋 I'm here to help you understand this repository.\n\nYou can ask things like:\n- What does a file do?\n- Show code of a file\n- Explain the architecture\n- How different parts work together",
  "tokens_used": null,
  "sources": [],
  "follow_ups": [],
  "created_at": "2026-03-02T09:17:00Z"
}
```

### 3. Structural Query

**Request:**
```json
{
  "message": "Show me the folder structure",
  "repo_id": "b44bd5ed97fb1c25"
}
```

**Response:**
```json
{
  "chat_id": "f7g8h9i0-j1k2-3456-lmno-pq7890123456",
  "reply": "repo/\n  ├─ main.py\n  ├─ requirements.txt\napp/\n  ├─ __init__.py\nrouters/\n  ├─ chat.py\n  ├─ repos.py",
  "tokens_used": null,
  "sources": [],
  "follow_ups": [],
  "created_at": "2026-03-02T09:18:00Z"
}
```

---

## Figma Design Checklist

Use this checklist when designing the Figma frame for this endpoint:

- [ ] **Header card** — Method badge (`POST`, green), path `/chat`, and one-line description
- [ ] **Auth section** — Show `X-API-Key` header with scope badges (`repo:read`, `repo:explain`)
- [ ] **Request body** — JSON editor-style block with all 5 fields, required fields highlighted
- [ ] **Response body** — JSON block showing all 6 response fields
- [ ] **Error cards** — 4 error states (404, 400, 401, 429) with colored status badges
- [ ] **Flow diagram** — Simplified version of the internal flow above
- [ ] **Route table** — The 4 question routing types with behavior descriptions
