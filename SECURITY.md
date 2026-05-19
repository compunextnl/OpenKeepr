# Security policy

_Last updated: 2026-05-19 — v1.3.0_

## Reporting a vulnerability

If you believe you have found a security vulnerability in OpenKeepr, please
report it privately. **Do not open a public GitHub issue.**

Contact: **security@example.com** (replace with your real address before publishing).
PGP key: optional — publish on your website and link from `.well-known/security.txt`.

We will acknowledge your report within **3 business days** and aim to publish a
fix or mitigation within **30 days** for high-severity issues.

## Scope

In scope:

- The OpenKeepr codebase in this repository
- The reference deployment (`deploy/`) when used as documented

Out of scope:

- Self-hosted instances that have modified the codebase
- Social-engineering attacks against operators

## Threat model

OpenKeepr is designed so that the **server operator cannot read message
content or attachments**. Encryption happens in the browser; the AES-256-GCM
decryption key is generated client-side and only ever appears in the URL
fragment (`#…`), which browsers never transmit to servers.

### What the server *does* store

- **Message ciphertext** (AES-256-GCM, fresh IV per message).
- **Attachment ciphertext** (AES-256-GCM, fresh IV per file, encrypted with
  the same key as the message body). Filename and MIME-type are inside the
  encrypted payload — they are not stored separately. The server only sees
  opaque blobs and a byte count.
- A short random **public ID** used in the URL path.
- The **expiry timestamp** and the `max_opens` counter.
- **Keyed HMAC-SHA256** of any allowed recipient e-mail addresses, so the
  server can match a recipient without learning the address.
- An **argon2id** hash of the optional verification code.
- For accounts: e-mail address, **argon2id** password hash, and optional
  **TOTP secret + backup codes encrypted at rest** with a dedicated
  server-side key (`SERVER_ENCRYPTION_KEY`).
- A **pseudonymous audit log** (event type, hashed IP, timestamp), kept for
  180 days for abuse mitigation.

### What the server *never* stores

- The decryption key (it lives only in the URL fragment, on the client).
- Plaintext message content or plaintext attachments.
- Plaintext recipient e-mail addresses (only HMAC hashes).
- The verification code itself in plaintext form (only an argon2id hash).
- Plaintext TOTP secrets or backup codes (encrypted at rest, only decrypted
  in-process when needed for verification).

If the database is leaked, an attacker still cannot read messages or
attachments without the fragment key from the original URL.

## Operational hardening

The reference deployment ships with the following defences enabled by
default:

- **Argon2id** for all password and verification-code hashing.
- **Authenticated encryption** (AES-256-GCM) for both messages and
  attachments — tampering is detected.
- **Constant-time comparisons** on the authentication and verification
  paths.
- **Strict Content-Security-Policy** with a **per-request nonce** for
  inline scripts. Third-party or injected scripts cannot execute.
- **HTTP-only / SameSite session cookies** + Flask-WTF CSRF on every
  state-changing request.
- **HSTS** automatically enabled when the application runs over HTTPS
  (`SESSION_COOKIE_SECURE=true`).
- **Rate limiting** (Flask-Limiter) on the public message-creation,
  e-mail-code-request and login endpoints.
- **TOTP-based two-factor authentication** with one-time backup codes;
  mandatory for administrator accounts.
- **Always-on admin login URL** (configurable via `ADMIN_LOGIN_PATH`) so
  public sign-in can be disabled without locking the operator out.
- **All front-end assets are vendored** (`app/static/vendor/`) and served
  from the same origin — no CDN, no third-party requests at runtime.
- **fail2ban** profile included in `deploy/` for brute-force protection on
  the SSH and the application login endpoint.
- **Systemd hardening** (`NoNewPrivileges`, `ProtectSystem=strict`,
  `PrivateTmp=true`, …) in the supplied service unit.

## Defence-in-depth notes

- Recipients pass through a gate (e-mail allow-list + verification code, or
  anonymous code) before the server reveals ciphertext. The gate is
  server-side; passing it sets a session flag so subsequent attachment
  downloads within the same session don't re-prompt.
- Once a recipient first opens a message, no further attachments can be
  added to it — even if someone discovers the public ID.
- Burned or expired messages have their on-disk attachment blobs removed
  by a background scheduler every two minutes; explicit "burn now" actions
  purge immediately.
- The application logs only metadata (public ID, event type, hashed IP) —
  never message content, recipient addresses, or codes.

## What is **not** in the threat model

- A compromised sender or recipient device — if either end-point is
  compromised, the encryption guarantees no longer hold.
- A malicious operator who modifies the source. The zero-knowledge
  property depends on the in-browser code being honest; if the operator
  ships a backdoored version of `app.css`/`composer.js`/etc., users have
  no way to detect that purely from the protocol. **Sub-resource integrity
  on first-party assets is not in scope.** Verify the deployment binary or
  pin it.
- Traffic-analysis attacks on TLS metadata (timing, sizes, frequencies).

## Supported versions

Only the latest minor release receives security updates. See
[CHANGELOG.md](CHANGELOG.md).
