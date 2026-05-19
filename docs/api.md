# OpenKeepr REST API — v1

> Base URL: `https://YOUR-HOST/api/v1`
> Source of truth: this file. The page at `/docs/api` is rendered from
> `docs/api.md`, so updates land in the docs automatically.

## Authentication

All endpoints require an API key, sent as a Bearer token:

```http
Authorization: Bearer okp_xxxxxxxxxxxxxxxxxxxxxxxxxx
```

Create keys from your account at `/auth/account` (UI) or under
**Admin → API keys** (admin-only overview).

API keys are shown **once** at creation. We store only a SHA-256 hash, so a
lost key cannot be recovered — generate a new one and revoke the old.

### Scopes

| Scope             | What it allows                                              |
|-------------------|-------------------------------------------------------------|
| `messages:write`  | Create and delete (burn) your own messages                  |
| `messages:read`   | Read metadata for your own messages                         |
| `feedback:write`  | Submit user feedback                                        |
| `admin:read`      | Read admin-only data (audit log, settings) — admins only    |
| `admin:write`     | Mutate admin-only data — admins only                        |

Calls without the required scope return `403 insufficient_scope`.

## Rate limits

Per-route limits are listed below. When exceeded, you receive `429 Too Many
Requests` with a `Retry-After` header. The default global limit is configured
via `RATELIMIT_DEFAULT` in `.env`.

## Conventions

* **Encoding**: request and response bodies are JSON (UTF-8).
* **Binary data**: base64-encoded (URL-safe accepted; padding optional).
* **Timestamps**: ISO 8601 in UTC, e.g. `2026-06-01T12:00:00+00:00`.
* **Errors**: `{"error": "<machine_code>", "...": "..."}` with the appropriate HTTP status.

---

## Zero-knowledge primer

OpenKeepr never sees plaintext. Before calling `POST /messages` you must:

1. Generate a random 256-bit key `K`.
2. Generate a random 96-bit IV (12 bytes) and a 128-bit salt (16 bytes).
3. Encrypt your plaintext with AES-256-GCM using `K` (and the IV).
4. POST the ciphertext, IV and salt to OpenKeepr.
5. Share the response URL with `#<base64(K)>` appended as a fragment.

Browsers do this automatically via `app/static/js/crypto.js`; a Python
example using `cryptography` is shown below.

```python
import base64, os, requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

key   = AESGCM.generate_key(bit_length=256)
iv    = os.urandom(12)
salt  = os.urandom(16)
ct    = AESGCM(key).encrypt(iv, b"hello world", None)

def b64(x): return base64.urlsafe_b64encode(x).rstrip(b"=").decode()

r = requests.post("https://YOUR-HOST/api/v1/messages",
    headers={"Authorization": "Bearer okp_..."},
    json={
        "ciphertext_b64": b64(ct),
        "iv_b64":         b64(iv),
        "salt_b64":       b64(salt),
        "expires_in_hours": 24,
        "max_opens": 1,
        "is_markdown": False,
        # Either provide recipients (e-mail allow-list) OR omit them to get a
        # 6-digit security code in the response.
        "recipients": ["alice@example.com"],
    })
print(r.json()["url"] + "#" + b64(key))   # the URL with the key in the fragment
```

---

## Endpoints

### `POST /messages` — create

Scope: `messages:write`  ·  Rate limit: 60 / hour per IP.

**Request body**

| Field                | Type            | Required | Notes                                                 |
|----------------------|-----------------|----------|-------------------------------------------------------|
| `ciphertext_b64`     | string (b64)    | yes      | AES-256-GCM ciphertext (incl. 16-byte tag)            |
| `iv_b64`             | string (b64)    | yes      | 12 bytes                                              |
| `salt_b64`           | string (b64)    | yes      | 16 or 32 bytes (forward-compat for KDF use cases)     |
| `is_markdown`        | bool            | no       | Render hint for the recipient's browser               |
| `expires_in_hours`   | integer         | no       | 1..720 (capped by `MAX_RETENTION_DAYS`, default 30d)  |
| `max_opens`          | integer / null  | no       | 1..100, null = unlimited                              |
| `recipients`         | array of string | no       | Plaintext e-mails. Stored as HMAC hashes.             |
| `use_security_code`  | bool            | no       | Force a 6-digit code even with recipients present     |

**Response** `201 Created`

```json
{
  "id": "5DJBOaW09Bs8Y4ToZGqQiK",
  "url": "https://YOUR-HOST/m/5DJBOaW09Bs8Y4ToZGqQiK",
  "expires_at": "2026-06-01T12:00:00+00:00",
  "max_opens": 1,
  "security_code": null,
  "requires_email": true
}
```

`security_code` is non-null **only** when one was generated (anonymous-recipient
mode). It is returned **once** and never recoverable.

**Errors**

* `400 missing or invalid ciphertext/iv/salt`
* `413 ciphertext exceeds N KB`
* `401 missing_api_key` / `401 invalid_or_revoked_api_key`
* `403 insufficient_scope`

---

### `GET /messages/{id}` — metadata

Scope: `messages:read`. Returns metadata for a message you created (404 if
created by someone else, to prevent leaking IDs).

**Response** `200 OK`

```json
{
  "id": "5DJBOaW09Bs8Y4ToZGqQiK",
  "created_at": "2026-05-19T08:00:00+00:00",
  "expires_at": "2026-05-20T08:00:00+00:00",
  "max_opens": 1,
  "opens": 0,
  "burned": false,
  "is_markdown": false,
  "recipients_count": 1,
  "size_bytes": 312
}
```

Content is never returned by the API — by design, the server doesn't have the key.

---

### `DELETE /messages/{id}` — burn

Scope: `messages:write`. Immediately marks the message as burned. Idempotent.

**Response** `200 OK`

```json
{"ok": true}
```

---

### `POST /feedback` — submit feedback

Scope: `feedback:write`  ·  Rate limit: 20 / hour per IP.

**Request body**

| Field      | Type   | Required | Notes                                                 |
|------------|--------|----------|-------------------------------------------------------|
| `type`     | string | no       | one of `bug`, `feature`, `praise`, `other` (default)  |
| `message`  | string | yes      | 1..5000 characters                                    |
| `contact`  | string | no       | optional reply address                                |
| `page`     | string | no       | what page the feedback is about                       |
| `language` | string | no       | e.g. `nl`, `en`                                       |

**Response** `201 Created`

```json
{"id": 42, "status": "new"}
```

---

### `GET /keys/scopes` — list available scopes

Public endpoint. Useful for client tooling.

```json
{
  "scopes": {
    "messages:write": "Create new messages",
    "messages:read":  "Retrieve metadata for messages you created",
    "...": "..."
  }
}
```

---

### `GET /keys` — list your own API keys

Scope: `messages:read`. Returns metadata (never the plaintext key).

---

## Versioning

The API is versioned in the URL (`/api/v1`). Breaking changes will be shipped
under `/api/v2` and announced in `CHANGELOG.md`. Non-breaking additions can
land in v1 without notice.

Browser usage of the same endpoints lives at `/m/*` and uses session+CSRF
auth instead of API keys.
