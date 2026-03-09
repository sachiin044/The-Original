# GET /health — Endpoint Reference

> **Figma Design Blueprint** — Simple health check endpoint.

---

## Overview

| Property       | Value                         |
|----------------|-------------------------------|
| **Method**     | `GET`                         |
| **Path**       | `/health`                     |
| **Auth**       | ❌ None                       |
| **Rate Limit** | No                            |
| **Purpose**    | Verify the API is running     |

---

## Request

No headers, no body, no parameters required.

```
GET /health
```

---

## Response (200 OK)

```json
{
  "status": "ok",
  "service": "running"
}
```

| Field     | Type     | Value       | Description              |
|-----------|----------|-------------|--------------------------|
| `status`  | `string` | `"ok"`      | Health status indicator  |
| `service` | `string` | `"running"` | Service state            |

---

## Figma Design Checklist

- [ ] Minimal card — `GET` badge + `/health`
- [ ] Green status indicator — "ok" / "running"
- [ ] No auth required badge
