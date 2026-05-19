# Changelog

All notable changes to OpenKeepr are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] — 2026-05-19

### Added

- **Encrypted attachments** — attach one or more files to a secure message.
  Each file is encrypted in the browser with the same AES-256-GCM key as the
  message body, using a fresh nonce per file. The server stores only opaque
  ciphertext blobs and never sees the original filename, MIME-type or
  contents.
- Drag-and-drop file picker in the composer, with per-file progress, size
  display and inline validation.
- Operator-configurable limits via `.env`: max file size, max number of
  files per message, max total size, and an allowed-types list (extensions
  and / or MIME globs). The allowed types are shown to the sender in the UI.
- Per-file decrypt-and-download in the viewer, plus a one-click
  "Download all (zip)" button (zip is assembled in the browser; the server
  is not involved).
- Inline previews in the viewer for images and PDFs (other types are
  download-only, by design).
- E-mail validation on the recipient field — invalid addresses are rejected
  client-side and server-side instead of being silently dropped.

### Changed

- Bumped admin UX: a prominent warning banner appears on the dashboard
  while the administrator has not yet enabled 2FA, and a direct
  "Two-factor authentication" entry was added to the user dropdown.
- The language switcher now uses inline SVG flags instead of regional
  emoji, so the country flags render the same way on every operating
  system (Windows included).
- Date / time columns in the admin pages respect the new `TIMEZONE`
  setting (database timestamps remain stored in UTC).

### Fixed

- Server-side defensive parsing of `.env` strings so an inline `# comment`
  after an empty value can never become a literal filename on disk.
- "Buy Me a Coffee" is shown verbatim in every language (matches the
  official product spelling).

### Security

- Attachment downloads require the same gate as the message body
  (recipient e-mail allow-list + verification code, or anonymous security
  code). After the gate is passed, a session flag avoids re-prompting the
  recipient for every file they want to download.
- Once a recipient first opens a message, no further attachments can be
  added to it (anti-tampering for anyone who happens to know the public
  ID).
- Attachment cleanup is wired into the existing 30-day retention purge —
  expired or burned messages also remove their on-disk attachment blobs.

## [1.1.0] — 2026-05-19

### Added

- **Copy-all button** in the create-message dialog: one click puts the link,
  expiry and verification code on your clipboard, ready to paste into your
  e-mail or chat program.
- **Language switcher** in the navigation now shows the country flag and the
  native language name (English, Nederlands, Français, Deutsch, Español,
  Italiano) instead of two-letter codes.
- **Runtime feature toggles** in the admin settings — administrators can turn
  the public sign-in page, account registration and the REST API on or off
  without restarting the application.
- **Always-on admin login URL** — when public sign-in is disabled, admins
  reach the login page through a separate, hard-to-guess URL that you choose
  yourself. You can never lock yourself out.
- **E-mail / SMTP test page** under *Admin → E-mail test* — validate your
  outbound mail configuration end-to-end before enabling delivery for
  recipients.
- **Customisable branding** — the application name, the GitHub link, and an
  optional "Buy Me a Coffee" support link in the footer are now all
  configurable.

### Changed

- "Security code" is now called **Verification code** consistently across
  the user interface.
- Six-digit verification codes are displayed without dashes (`123456`) so
  they're easier to paste into password managers and autofill prompts.
- The home-page tagline now reflects that both the link *and* the
  verification code are needed to read a message.
- Significantly improved **dark-mode readability** for the Markdown preview
  and the decrypted-message view.
- The theme toggle (light / dark / auto) now reacts visibly on the very
  first click and shows the active mode as an icon.

### Fixed

- The language switcher now reliably applies the chosen language to the
  user interface.
- Navigation menus no longer slide behind dashboard tiles.
- Translations for newly added text are picked up automatically on the next
  application start, without requiring a manual build step.

### Security

- Recipients no longer have to receive the verification code through the
  same channel as the link. The sender can share the code separately
  (chat, phone, in person), which closes the most common interception
  vector when a recipient's e-mail is compromised.
- Administrators can validate outbound mail in isolation before turning on
  e-mail delivery for end users, reducing the risk of misconfiguration
  leaking codes.

## [1.0.0] — 2026-05-19

### Added

- **Zero-knowledge encryption**: every message is encrypted in your browser
  with AES-256-GCM before it ever leaves your device. The decryption key
  lives in the URL fragment and is never sent to the server.
- **Recipient e-mail allow-list** — restrict a message to specific
  addresses; the recipient must authenticate with a 6-digit code.
- **Expiry controls** — messages can be set to self-destruct after a chosen
  number of hours or days. A hard cap of 30 days applies to every message.
- **Open-limit controls** — limit how many times a message may be read,
  including a "burn after reading" option.
- **Markdown messages** with a live preview while composing.
- **Light and dark themes** with automatic system detection and a manual
  override that is remembered between visits.
- **Six languages** out of the box: English, Dutch, French, German, Spanish
  and Italian.
- **REST API** at `/api/v1` with scoped, per-account API keys and per-route
  rate limiting.
- **Searchable API documentation** at `/docs/api`, kept in lockstep with
  the live code.
- **Administrator dashboard** with an audit log of security-relevant
  events, an inbox for in-app user feedback, a maintenance-mode switch
  that never locks the administrator out, and user-account management.
- **Two-factor authentication (TOTP)** with one-time backup codes for both
  administrator and user accounts.
- **In-app feedback form** with a status workflow (new → in progress →
  resolved) on the admin side.
- **`/.well-known/security.txt`** that auto-renews its `Expires` field so
  it can never go stale.

### Security

- The server stores ciphertext only; it does not have, and cannot derive,
  the key needed to decrypt a message.
- Recipient e-mail addresses are stored only as keyed HMAC-SHA256 hashes.
  A leaked database cannot be reversed back to the original addresses.
- Passwords and verification codes are hashed with **argon2id**.
- All long-lived secrets at rest (TOTP secrets, backup codes) are
  encrypted with a dedicated server-side key.
- Constant-time comparisons throughout the authentication and verification
  paths.
- Strict default Content-Security-Policy, HTTP-only / SameSite cookies, and
  CSRF protection on all state-changing requests.

[1.1.0]: https://github.com/OWNER/openkeepr/releases/tag/v1.1.0
[1.0.0]: https://github.com/OWNER/openkeepr/releases/tag/v1.0.0
