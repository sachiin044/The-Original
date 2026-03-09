# ExplainGitHub — Master Flowchart (All Endpoints)

> Figma-ready flowchart text covering every endpoint in the system.

---

## TOP LEVEL — API Gateway

### 🟢 Start Node (Green Rounded)
> **CLIENT (HTTP Request)**

↓

### 🟪 Box (Purple)
> **FastAPI Application (app/main.py)**

Arrow text:
> RequestLoggingMiddleware + Global Exception Handler

↓

### 🔶 Decision Diamond (Orange) — MAIN ROUTER
> **Which endpoint is being called?**

**9 output arrows to different flows:**

| Arrow | Condition | Goes To |
|-------|-----------|---------|
| 1 | `POST /chat` | → **SECTION A: RAG Chat** |
| 2 | `POST /issues/chat` | → **SECTION B: Issues Chat** |
| 3 | `POST /pull-requests/chat` | → **SECTION C: PR Chat** |
| 4 | `POST /repos/register` | → **SECTION D: Repo Register** |
| 5 | `POST /repos/{id}/index` | → **SECTION E: Repo Index** |
| 6 | `GET /repos/{id}/status, /tree, /files` | → **SECTION F: Repo Query** |
| 7 | `POST /agent/chat` | → **SECTION G: Agent Investigation** |
| 8 | `POST /workflows/chat` | → **SECTION H: Workflows Chat** |
| 9 | `CRUD /api-keys, /credentials, /health` | → **SECTION I: Management** |

---
---

## SECTION A — POST /chat (RAG Chat)

### 🟢 Start (Green Rounded)
> **POST /chat**

### Input Arrow
> `{ message, repo_id, chat_id, context, files }`

↓

### 🟪 Box (Purple)
> **Auth & Rate Limit**

> Verify X-API-Key, check chat scopes (repo:read, repo:explain), enforce rate limit

↓

### 🔶 Diamond (Orange)
> **Does repo_id exist in database?**

**NO →** 🟥 `Return 404: "Repository not registered"`

**YES ↓**

### 🔶 Diamond (Orange)
> **Is repository indexed?**

**NO →** 🟥 `Return 400: "Repository is not indexed yet. Please index it first."`

**YES ↓**

### 🟪 Box (Purple)
> **create_chat function**

> Creates or resumes chat session using chat_id (auto UUID if not provided)

↓

### 🟪 Box (Purple)
> **append_message function**

> Stores the user's message in chat history

↓

### 🔶 Diamond (Orange) — QUESTION ROUTER
> **Question Router: What type of question?**

#### Branch 1: `If message = "hi", "hello", "hey"...`
> 🟢 **Greeting Handler** → Returns static welcome message
> Return: `{ reply: "Hi 👋...", tokens_used: null, sources: [], follow_ups: [] }`

#### Branch 2: `If message = "last question", "what did I ask"...`
> 🟢 **Memory Handler** → Fetches previous user messages from chat history
> Return: `{ reply: "Your last question was: '...'", tokens_used: 0, sources: [] }`

#### Branch 3: `If route == "STRUCTURAL"`
> 🟪 **format_folder_structure function** → Fetches manifest, formats folder tree
> Return: `{ reply: "repo/\n ├─ main.py\n...", tokens_used: null, sources: [] }`

#### Branch 4: `Default → SEMANTIC (RAG)`
> 🟪 **SupabaseVectorStore function** → Loads vector store for repo_id
> ↓
> 🟪 **ask_question function (RAG)** → Vector search (top 20 chunks) → GPT-4o-mini → Answer
> ↓
> 🟪 **generate_followups function** → AI generates follow-up suggestions
> ↓
> 🟢 Return: `{ reply: "...", tokens_used: 1250, sources: [...], follow_ups: [...] }`

---
---

## SECTION B — POST /issues/chat

### 🟢 Start (Green Rounded)
> **POST /issues/chat**

### Input Arrow
> `{ repo_id, issue_number, message, chat_id, context }`

↓

### 🟪 Box (Purple)
> **Auth — verify_api_key**

↓

### 🔶 Diamond (Orange)
> **Does repo_id exist in database?**

**NO →** 🟥 `Return error: "Repository not registered"`

**YES ↓**

### 🟪 Box (Purple)
> **Resolve repo_full_name**

> Extracts owner/repo from repo_url

↓

### 🔶 Diamond (Orange)
> **Does repo have a credential_id?**

**YES →** 🟪 **decrypt_token function** → Decrypts stored GitHub PAT

**NO →** Continue without token (public repo)

↓

### 🟪 Box (Purple)
> **create_chat + append_message**

> Creates isolated chat session, stores user message

↓

### 🔶 Diamond (Orange)
> **Is issue_number provided?**

#### Branch LEFT: `NO → REPO-LEVEL FLOW`
> 🟪 **fetch_repository_issues function** → Fetches top 100 issues from GitHub
> ↓
> 🟪 **filter_issues_by_query function** → Filters using natural language query
> ↓
> 🟢 Return: `{ reply: "Found issues matching...", tokens_used: 0 }`

#### Branch RIGHT: `YES → SINGLE ISSUE FLOW`
> 🟪 **fetch_issue_documents function** → Fetches issue body + comments
> ↓
> 🟪 **RecursiveCharacterTextSplitter** → Splits into 800-char chunks
> ↓
> 🟪 **FAISS.from_texts** → Creates temp vector store with embeddings
> ↓
> 🟪 **ask_question function (RAG)** → Vector search → GPT-4o-mini → Answer
> ↓
> 🟢 Return: `{ reply: "Issue #128 is about...", sources: [...], tokens_used: 850 }`

---
---

## SECTION C — POST /pull-requests/chat

### 🟢 Start (Green Rounded)
> **POST /pull-requests/chat**

### Input Arrow
> `{ repo_id, pr_number, message, chat_id, context }`

↓

### 🟪 Box (Purple)
> **Auth — verify_api_key**

↓

### 🔶 Diamond (Orange)
> **Does repo_id exist in database?**

**NO →** 🟥 `Return 404: "Repository not registered"`

**YES ↓**

### 🟪 Box (Purple)
> **Resolve repo_full_name + Decrypt credential (if exists)**

↓

### 🟪 Box (Purple)
> **create_chat + append_message**

↓

### 🔶 Diamond (Orange)
> **Is pr_number provided?**

#### Branch LEFT: `NO → REPO-LEVEL FLOW`
> 🟪 **fetch_repository_prs function** → Fetches top 100 PRs from GitHub
> ↓
> 🟪 **filter_prs_by_query function** → Filters using query, deep-fetches up to 10
> ↓
> 🟢 Return: `{ reply: "Found PRs matching...", tokens_used: 0 }`

#### Branch RIGHT: `YES → SINGLE PR FLOW`
> 🟪 **fetch_pr_documents function** → Fetches PR body + diff + checks + reviews
> ↓
> 🟪 **RecursiveCharacterTextSplitter** → Splits into 800-char chunks
> ↓
> 🟪 **FAISS.from_documents** → Creates temp vector store
> ↓
> 🟪 **ask_question function (RAG)** → Vector search → GPT-4o-mini → Answer
> ↓
> 🟢 Return: `{ reply: "PR #42 refactors...", sources: [...], tokens_used: 1100 }`

---
---

## SECTION D — POST /repos/register

### 🟢 Start (Green Rounded)
> **POST /repos/register**

### Input Arrow
> `{ provider, repo_url, branch, visibility, credential_id }`

↓

### 🔶 Diamond (Orange)
> **Is visibility "private" AND credential_id is null?**

**YES →** 🟥 `Return error: "credential_id required for private repositories"`

**NO ↓**

### 🟪 Box (Purple)
> **get_repo_id function**

> Generates deterministic repo_id by hashing repo_url

↓

### 🔶 Diamond (Orange)
> **Does repo_id already exist in database?**

**YES →** 🟢 `Return: { repo_id, status: "already_registered" }`

**NO ↓**

### 🟪 Box (Purple)
> **Supabase INSERT**

> Inserts repo_id, repo_url, credential_id into repos table

↓

### 🟢 Response (Green Rounded)
> Return: `{ repo_id: "b44bd5ed...", status: "registered" }`

---
---

## SECTION E — POST /repos/{repo_id}/index

### 🟢 Start (Green Rounded)
> **POST /repos/{repo_id}/index**

### Input Arrow
> Path: `repo_id` | Query: `?force=true/false`

↓

### 🔶 Diamond (Orange)
> **Does repo_id exist in database?**

**NO →** 🟥 `Return 404: "Repository not registered"`

**YES ↓**

### 🔶 Diamond (Orange)
> **Is already indexed AND force=false?**

**YES ↓**

### 🔶 Diamond (Orange)
> **Are there new commits since last index?**

**NO →** 🔶 **Do vectors exist in Pinecone?**
> **YES →** 🟢 `Return: { status: "already_indexed", indexed_at: "..." }`
> **NO →** Fall through to re-index

**YES (new commits) ↓**

### 🟪 Box (Purple)
> **Background Task: _index_repo_background**

> Runs asynchronously — returns immediately to client

↓ (async background)

### 🟪 Box (Purple)
> **clone_repo function**

> Clones the GitHub repository to local disk

↓

### 🟪 Box (Purple)
> **read_repo_files function**

> Reads .py, .md, .txt files — builds manifest

↓

### 🟪 Box (Purple)
> **create_vector_store function**

> Splits into chunks → Embeds via OpenAI → Stores in Pinecone + Supabase

↓

### 🟪 Box (Purple)
> **Update repos table**

> Sets indexed_at timestamp and manifest in Supabase

↓ (immediate response to client)

### 🟢 Response (Green Rounded)
> Return: `{ index_id: "idx_b44bd5ed...", status: "started" }`

---
---

## SECTION F — Repo Query Endpoints

### F1: GET /repos/{repo_id}/status

> 🟢 Start → 🔶 Repo exists? → 🟪 Check Pinecone for vectors → 🟢 Return: `{ status: "indexed"/"not_indexed", last_indexed_at }`

### F2: GET /repos/{repo_id}/tree

> 🟢 Start → 🔶 Repo exists? → 🔶 Indexed? → 🟪 Read manifest → 🟢 Return: `{ tree: [{path, type}...] }`

### F3: GET /repos/{repo_id}/files?path=

> 🟢 Start → 🔶 Repo exists? → 🔶 Indexed? → 🟪 clone_repo → 🟪 read_file_content → 🔶 Valid path? → 🟢 Return: `{ path, content }`

---
---

## SECTION G — POST /agent/chat

### 🟢 Start (Green Rounded)
> **POST /agent/chat**

### Input Arrow
> `{ repo_id, query }`

↓

### 🟪 Box (Purple)
> **Auth — verify_api_key**

↓

### 🟪 Box (Purple)
> **GitHubAgentController**

> Initializes the autonomous agent

↓

### 🔶 Diamond (Orange) — AGENT LOOP
> **GPT-4o-mini: Need more tools or ready to answer?**

#### Loop Path: `Need more tools`
> 🟪 **Tool Selection** → LLM picks a tool from:
> - `get_failed_workflows` — Fetch failed CI runs
> - `get_deployment_info` — Fetch deployment status
> - `get_recent_prs` — Fetch recent PRs
> - `get_open_issues` — Fetch open issues
> ↓
> 🟪 **Execute Tool** → Run with timeout enforcement + failure recovery
> ↓
> 🟪 **Log Step** → Record { iteration, tool, args, result, duration_ms }
> ↓
> ↩️ Back to Diamond (loop)

#### Exit Path: `Ready to answer`
> 🟪 **Synthesize Answer** → Combine all tool results into final answer

↓

### 🟢 Response (Green Rounded)
> Return: `{ answer, steps: [...], sources, tool_call_count, iterations_used, investigated_at }`

---
---

## SECTION H — POST /workflows/chat

### 🟢 Start (Green Rounded)
> **POST /workflows/chat**

### Input Arrow
> `{ repo_id, workflow_id, run_id, question, chat_id, include_logs }`

↓

### 🟪 Box (Purple)
> **Auth + Workflow Scopes + Rate Limit**

↓

### 🟪 Box (Purple)
> **WorkflowChatService.answer_question**

↓

### 🔶 Diamond (Orange) — SCOPE LEVEL
> **What scope of data was provided?**

#### Branch 1: `repo_id ONLY`
> 🟢 **High-level workflow analysis** → Overview of all workflows

#### Branch 2: `repo_id + workflow_id`
> 🟢 **Aggregate workflow run analysis** → History, success rate, trends

#### Branch 3: `repo_id + run_id`
> 🟢 **Deep run analysis** → Logs, steps, timing, errors

↓

### 🟢 Response (Green Rounded)
> Return: `{ answer, sources, metadata }`

---
---

## SECTION I — Management Endpoints

### I1: API Keys

```
POST /api-keys (Create)
  → No auth required
  → { email, name, environment, scopes, expires_at, ip_allowlist }
  → 🟪 create_api_key_internal → Hash key, store in DB
  → 🟢 Return: { key_id, api_key (shown ONCE), created_at }

GET /api-keys (List)
  → Auth required
  → 🟪 Resolve caller email → list_api_keys_internal
  → 🟢 Return: [{ key_id, name, environment, scopes, last_used_at }]

PATCH /api-keys/{key_id} (Update)
  → Auth required
  → 🟪 Ownership check → update_api_key_internal
  → 🟢 Return: { status: "updated" }

DELETE /api-keys/{key_id} (Revoke)
  → Auth required
  → 🟪 Ownership check → revoke_api_key_internal
  → 🟢 Return: { status: "success", message: "API key revoked" }

GET /manage-keys (Dashboard)
  → Auth required
  → 🟪 Fetch all keys + usage logs for user
  → 🟢 Return: { user_email, keys: [{ usage, logs }] }
```

### I2: Credentials

```
POST /credentials/github/pat (Register PAT)
  → Auth required
  → { token, label, scopes_expected, expires_at }
  → 🔶 Validate with GitHub API
  → 🔶 Over-scope check (extra scopes?)
  → 🔶 Expiry check (in future?)
  → 🟪 encrypt_token → Store encrypted in DB
  → 🟢 Return: { credential_id, status: "validated" }

DELETE /credentials/{credential_id} (Revoke)
  → Auth required
  → 🔶 Ownership check
  → 🟪 Soft-delete (status → "revoked")
  → 🟢 Return: { status: "revoked" }
```

### I3: Health

```
GET /health
  → No auth, no params
  → 🟢 Return: { status: "ok", service: "running" }
```

---
---

## MASTER NODE SUMMARY TABLE

| # | Shape | Color | Text | Section |
|---|-------|-------|------|---------|
| 1 | Rounded | 🟢 Green | `CLIENT (HTTP Request)` | Top |
| 2 | Box | 🟪 Purple | `FastAPI Application` | Top |
| 3 | Diamond | 🔶 Orange | `Which endpoint?` | Top Router |
| 4–19 | Various | Various | POST /chat flow (16 nodes) | Section A |
| 20–35 | Various | Various | POST /issues/chat flow (16 nodes) | Section B |
| 36–50 | Various | Various | POST /pull-requests/chat flow (15 nodes) | Section C |
| 51–57 | Various | Various | POST /repos/register flow (7 nodes) | Section D |
| 58–67 | Various | Various | POST /repos/{id}/index flow (10 nodes) | Section E |
| 68–73 | Various | Various | GET /status, /tree, /files (6 nodes) | Section F |
| 74–82 | Various | Various | POST /agent/chat flow (9 nodes) | Section G |
| 83–88 | Various | Various | POST /workflows/chat flow (6 nodes) | Section H |
| 89–99 | Various | Various | API Keys + Credentials + Health (11 nodes) | Section I |

**Total: ~99 nodes across 9 sections**

---

## COLOR LEGEND

| Color | Shape | Meaning |
|-------|-------|---------|
| 🟢 Green Rounded | Start/End/Response | Entry points and final responses |
| 🟪 Purple Box | Function/Service | Backend functions and services |
| 🔶 Orange Diamond | Decision | Conditional branches |
| 🟥 Red Box | Error | Error responses |
