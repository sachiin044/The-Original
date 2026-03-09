# API Keys Endpoints — Reference

> **Figma Design Blueprint** — Full CRUD for API key management.

---

## Endpoint Summary

| # | Method   | Path                  | Auth     | Purpose                           |
|---|----------|-----------------------|----------|-----------------------------------|
| 1 | `POST`   | `/api-keys`           | ❌ None  | Create a new API key              |
| 2 | `GET`    | `/api-keys`           | ✅ Key   | List all keys for the user        |
| 3 | `PATCH`  | `/api-keys/{key_id}`  | ✅ Key   | Update key metadata               |
| 4 | `DELETE` | `/api-keys/{key_id}`  | ✅ Key   | Revoke a specific key             |
| 5 | `GET`    | `/manage-keys`        | ✅ Key   | Full key dashboard with logs      |
| 6 | `POST`   | `/revoke-keys`        | ✅ Key   | Revoke key by ID (body-based)     |

---

## 1. POST /api-keys — Create

### Request

```json
{
  "email": "dev@example.com",
  "name": "Production Key",
  "environment": "production",
  "scopes": ["repo:read", "repo:explain"],
  "expires_at": "2027-01-01T00:00:00Z",
  "ip_allowlist": ["203.0.113.0/24"]
}
```

| Field          | Type              | Required | Default | Description                    |
|----------------|-------------------|----------|---------|--------------------------------|
| `email`        | `string`          | ✅ Yes   | —       | User email                     |
| `name`         | `string`          | ✅ Yes   | —       | Key label                      |
| `environment`  | `string \| null`  | ❌ No    | `null`  | `"development"` / `"production"` |
| `scopes`       | `string[] \| null`| ❌ No    | `null`  | Permission scopes              |
| `expires_at`   | `string \| null`  | ❌ No    | `null`  | ISO 8601 expiry date           |
| `ip_allowlist` | `string[] \| null`| ❌ No    | `null`  | Allowed IP ranges              |

### Response (200 OK)

```json
{
  "key_id": "uuid-here",
  "api_key": "eg_live_xxxxxxxxxxxx",
  "created_at": "2026-03-02T09:30:00Z"
}
```

> ⚠️ `api_key` is shown **ONCE** — never retrievable again.

---

## 2. GET /api-keys — List

### Response (200 OK)

```json
[
  {
    "key_id": "uuid-here",
    "name": "Production Key",
    "environment": "production",
    "scopes": ["repo:read", "repo:explain"],
    "last_used_at": "2026-03-01T15:00:00Z"
  }
]
```

---

## 3. PATCH /api-keys/{key_id} — Update

### Request

```json
{
  "name": "Updated Key Name",
  "scopes": ["repo:read"]
}
```

### Response

```json
{ "status": "updated" }
```

---

## 4. DELETE /api-keys/{key_id} — Revoke

### Response

```json
{
  "status": "success",
  "message": "API key revoked successfully",
  "api_key_id": "uuid-here"
}
```

> If already revoked: `"message": "API key already revoked"`

---

## 5. GET /manage-keys — Dashboard

> Returns all keys + full usage logs for the authenticated user.

### Response (200 OK)

```json
{
  "user_email": "dev@example.com",
  "keys": [
    {
      "api_key_id": "uuid-here",
      "name": "Production Key",
      "status": "active",
      "created_at": "2026-03-01T10:00:00Z",
      "last_used_at": "2026-03-02T09:00:00Z",
      "usage": {
        "total_requests": 150,
        "error_count": 3
      },
      "logs": [
        {
          "endpoint": "/chat",
          "method": "POST",
          "status_code": 200,
          "duration_ms": 1200,
          "created_at": "2026-03-02T09:00:00Z",
          "request_id": "req_abc123",
          "error_message": null
        }
      ]
    }
  ]
}
```

---

## 6. POST /revoke-keys — Revoke (Body)

### Request

```json
{ "api_key_id": "uuid-to-revoke" }
```

### Response — same as DELETE endpoint

---

## Error Responses (All Endpoints)

| Code | Detail                                    | Trigger                     |
|------|-------------------------------------------|-----------------------------|
| 400  | (dynamic validation error)                | Invalid input               |
| 401  | Invalid or missing API key                | Bad `X-API-Key`             |
| 403  | You are not allowed to revoke this API key| Ownership mismatch          |
| 404  | API key not found / Target key not found  | Unknown key ID              |
| 429  | Rate limit exceeded                       | Create endpoint rate limit  |
| 500  | Failed to create/revoke API key           | Internal error              |

---

## Figma Design Checklist

- [ ] **Endpoint overview table** — all 6 endpoints with methods
- [ ] **Create flow** — show the one-time `api_key` reveal
- [ ] **Key list card** — show scopes as badges
- [ ] **Dashboard view** — usage stats + log table
- [ ] **Revoke flow** — with ownership check
- [ ] **Auth badges** — which endpoints need existing key vs public
- [ ] Error state cards
