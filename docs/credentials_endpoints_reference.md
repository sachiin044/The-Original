# Credentials Endpoints — Reference

> **Figma Design Blueprint** — GitHub PAT registration and revocation.

---

## Endpoint Summary

| # | Method   | Path                              | Auth    | Purpose                       |
|---|----------|-----------------------------------|---------|-------------------------------|
| 1 | `POST`   | `/credentials/github/pat`         | ✅ Key  | Register a GitHub PAT         |
| 2 | `DELETE` | `/credentials/{credential_id}`    | ✅ Key  | Revoke a stored credential    |

---

## 1. POST /credentials/github/pat — Register

> Validates, encrypts, and stores a GitHub Personal Access Token.

### Request

```json
{
  "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
  "label": "My CI Token",
  "scopes_expected": ["repo", "read:org"],
  "expires_at": "2027-06-01T00:00:00Z"
}
```

| Field             | Type       | Required | Description                                |
|-------------------|------------|----------|--------------------------------------------|
| `token`           | `string`   | ✅ Yes   | GitHub PAT (validated with GitHub API)     |
| `label`           | `string`   | ✅ Yes   | Human-readable label for the token         |
| `scopes_expected` | `string[]` | ✅ Yes   | Expected GitHub scopes                     |
| `expires_at`      | `string`   | ✅ Yes   | ISO 8601 expiry date (must be in future)   |

### Validation Flow

```
Token submitted
    │
    ▼
┌────────────────────┐
│ Validate with      │
│ GitHub API         │──→ 400: "Invalid GitHub token"
│ (check scopes)     │
└────────┬───────────┘
         │ ✅ Valid
         ▼
┌────────────────────┐
│ Over-scope check   │
│ (extra scopes?)    │──→ 400: "Token has extra scopes: [...]"
└────────┬───────────┘
         │ ✅ Exact match
         ▼
┌────────────────────┐
│ Expiry check       │
│ (in the future?)   │──→ 400: "Token is already expired"
└────────┬───────────┘
         │ ✅ Valid
         ▼
┌────────────────────┐
│ Encrypt + Store    │
│ (AES encryption)   │
│ No raw storage     │
└────────┬───────────┘
         │
         ▼
    Return credential_id
```

### Response (200 OK)

```json
{
  "credential_id": "cred_uuid_here",
  "status": "validated"
}
```

### Errors

| Code | Detail                           | Trigger                                  |
|------|----------------------------------|------------------------------------------|
| 400  | Invalid GitHub token             | GitHub API validation failed             |
| 400  | Token has extra scopes: [...]    | Token has more scopes than expected      |
| 400  | Token expiry is required         | `expires_at` missing                     |
| 400  | Invalid expires_at format        | Unparseable date                         |
| 400  | Token is already expired         | Date is in the past                      |
| 401  | Invalid or missing API key       | Bad `X-API-Key`                          |
| 404  | API key not found                | Caller key doesn't exist                 |

---

## 2. DELETE /credentials/{credential_id} — Revoke

> Soft-deletes a credential (sets status to `"revoked"`).

### Path Params

| Param           | Type     | Description     |
|-----------------|----------|-----------------|
| `credential_id` | `string` | Credential UUID |

### Response (200 OK)

```json
{ "status": "revoked" }
```

### Errors

| Code | Detail                                        | Trigger                     |
|------|-----------------------------------------------|-----------------------------|
| 401  | Invalid or missing API key                    | Bad `X-API-Key`             |
| 403  | You are not allowed to revoke this credential | Ownership mismatch          |
| 404  | API key not found                             | Caller key doesn't exist    |
| 404  | Credential not found                          | Unknown credential ID       |

---

## Figma Design Checklist

- [ ] Header cards — `POST` + `DELETE` with paths
- [ ] **Token validation flow diagram** — 4-step pipeline
- [ ] **Security callout** — "Token encrypted, never stored in plaintext"
- [ ] Request/response bodies for both endpoints
- [ ] Error state cards (6 error scenarios for registration)
