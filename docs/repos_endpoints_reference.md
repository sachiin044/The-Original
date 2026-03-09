# Repos Endpoints — Reference

> **Figma Design Blueprint** — 7 endpoints for repository registration, indexing, and querying.

---

## Endpoint Summary

| # | Method   | Path                       | Auth     | Purpose                                  |
|---|----------|----------------------------|----------|------------------------------------------|
| 1 | `POST`   | `/repos/register`          | ❌ None  | Register a repository (no indexing)       |
| 2 | `POST`   | `/repos/{repo_id}/index`   | ❌ None  | Start async indexing                      |
| 3 | `GET`    | `/repos/{repo_id}/status`  | ❌ None  | Check indexing status                     |
| 4 | `GET`    | `/repos/{repo_id}/tree`    | ❌ None  | Get folder/file tree                      |
| 5 | `GET`    | `/repos/{repo_id}/files`   | ❌ None  | Get file content                          |
| 6 | `POST`   | `/upload-repo`             | ✅ Key   | Upload & fully index (legacy/sync)        |
| 7 | `POST`   | `/private-repo-access`     | ✅ Key   | Index private repo with per-request token |

---

## 1. POST /repos/register

> Register a repository and get a `repo_id`. Does **NOT** index.

### Request Body

```json
{
  "provider": "github",
  "repo_url": "https://github.com/user/repo",
  "branch": "main",
  "visibility": "private",
  "credential_id": "cred_abc123"
}
```

| Field           | Type              | Required | Default     | Description                          |
|-----------------|-------------------|----------|-------------|--------------------------------------|
| `provider`      | `string`          | ✅ Yes   | —           | Always `"github"`                    |
| `repo_url`      | `string`          | ✅ Yes   | —           | Full GitHub URL                      |
| `branch`        | `string \| null`  | ❌ No    | `"main"`    | Branch to index                      |
| `visibility`    | `string \| null`  | ❌ No    | `"private"` | `"public"` or `"private"`            |
| `credential_id` | `string \| null`  | ❌ No    | `null`      | Required for private repos           |

### Response (200 OK)

```json
{
  "repo_id": "b44bd5ed97fb1c25",
  "status": "registered"
}
```

> If already registered: `"status": "already_registered"`

### Errors

| Code | Detail                                             |
|------|----------------------------------------------------|
| —    | `"credential_id required for private repositories"` (inline error) |

---

## 2. POST /repos/{repo_id}/index

> Starts **async background** indexing. Returns immediately.

### Path Params

| Param     | Type     | Description    |
|-----------|----------|----------------|
| `repo_id` | `string` | Repository ID  |

### Query Params

| Param   | Type   | Default | Description                        |
|---------|--------|---------|------------------------------------|
| `force` | `bool` | `false` | Force re-index even if up-to-date  |

### Response (200 OK)

```json
{
  "index_id": "idx_b44bd5ed97fb1c25",
  "status": "started"
}
```

> If already indexed and no new commits: `"status": "already_indexed"`

### Errors

| Code | Detail                    |
|------|---------------------------|
| 404  | Repository not registered |

### Internal Flow

```
Request → Check repo exists → Check if already indexed
    → (if indexed + !force) Check GitHub for new commits
    → Start background task:
        Clone → Read files → Split chunks → Embed → Store in Pinecone
    → Return immediately {"status": "started"}
```

---

## 3. GET /repos/{repo_id}/status

> Check repository indexing status.

### Response (200 OK)

```json
{
  "repo_id": "b44bd5ed97fb1c25",
  "status": "indexed",
  "last_indexed_at": "2026-03-01T10:30:00Z"
}
```

| `status` value  | Meaning                         |
|-----------------|---------------------------------|
| `"indexed"`     | Vectors exist in Pinecone       |
| `"not_indexed"` | No vectors found yet            |

---

## 4. GET /repos/{repo_id}/tree

> Get the full folder/file tree of an indexed repository.

### Response (200 OK)

```json
{
  "repo_id": "b44bd5ed97fb1c25",
  "tree": [
    { "path": "app/", "type": "dir" },
    { "path": "app/main.py", "type": "file" },
    { "path": "app/routers/", "type": "dir" },
    { "path": "app/routers/chat.py", "type": "file" }
  ]
}
```

### Errors

| Code | Detail                    |
|------|---------------------------|
| 404  | Repository not registered |
| 400  | Repository not indexed    |

---

## 5. GET /repos/{repo_id}/files?path=

> Get file content from an indexed repository.

### Query Params

| Param  | Type     | Required | Description            |
|--------|----------|----------|------------------------|
| `path` | `string` | ✅ Yes   | Relative file path     |

### Response (200 OK)

```json
{
  "repo_id": "b44bd5ed97fb1c25",
  "path": "app/main.py",
  "content": "from fastapi import FastAPI\n..."
}
```

### Errors

| Code | Detail                    |
|------|---------------------------|
| 400  | Invalid file path         |
| 400  | Repository not indexed    |
| 404  | Repository not registered |
| 404  | File not found            |
| 500  | Unable to read file       |

---

## 6. POST /upload-repo (Legacy)

> Synchronous upload + full index. Requires API key.

### Request

```json
{ "repo_url": "https://github.com/user/repo" }
```

### Response

```json
{
  "status": "Repository indexed successfully",
  "repo_id": "b44bd5ed97fb1c25"
}
```

---

## 7. POST /private-repo-access

> Index a private repository using a per-request GitHub token.

### Request

```json
{
  "repo_url": "https://github.com/user/private-repo",
  "github_token": "ghp_xxxxxxxxxxxx"
}
```

### Response

```json
{
  "status": "Private repository indexed successfully",
  "repo_id": "a1b2c3d4e5f67890"
}
```

### Errors

| Code | Detail                               |
|------|--------------------------------------|
| 401  | Invalid or missing API key           |
| 500  | Failed to access private repository  |

---

## Figma Design Checklist

- [ ] **Master overview card** — table of all 7 repo endpoints
- [ ] **Registration flow** — POST /register → POST /index → GET /status
- [ ] **Indexing pipeline diagram** — Clone → Read → Chunk → Embed → Store
- [ ] **Tree & file viewer** — sample tree output + file content
- [ ] **Auth badges** — show which endpoints need API key vs public
- [ ] **Error cards** for each endpoint
