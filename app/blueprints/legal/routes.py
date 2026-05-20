"""Privacy / cookies / security.txt — text-only pages, no tracking.

`security.txt` is generated dynamically so its `Expires:` field stays current
(re-anchored every request to NOW + SECURITY_EXPIRES_DAYS). This way you
never need to manually rotate it — no annual reminder needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Response, current_app, render_template, url_for

from app.blueprints.legal import bp


@bp.get("/privacy")
def privacy():
    return render_template("legal/privacy.html")


@bp.get("/cookies")
def cookies():
    return render_template("legal/cookies.html")


@bp.get("/security")
def security_policy():
    """Human-readable security policy linked from security.txt."""
    return render_template("legal/security.html")


#: Crawlers that ignore robots.txt almost always; listed here for completeness
#: so the polite ones (most AI-training scrapers do honour robots.txt now) get
#: a clear signal. Hard enforcement happens at the nginx layer — see
#: deploy/nginx.conf.example.
_BAD_BOTS = [
    # AI training / scraping
    "GPTBot",            # OpenAI
    "OAI-SearchBot",     # OpenAI
    "ChatGPT-User",      # OpenAI live-fetch
    "ClaudeBot",         # Anthropic
    "Claude-Web",        # Anthropic
    "anthropic-ai",      # Anthropic (legacy UA)
    "Google-Extended",   # Google AI (NOT Googlebot — search bot remains allowed)
    "FacebookBot",       # Meta AI
    "Meta-ExternalAgent",
    "Meta-ExternalFetcher",
    "Bytespider",        # ByteDance / TikTok
    "CCBot",             # Common Crawl — feeds most LLM training sets
    "PerplexityBot",     # Perplexity
    "Applebot-Extended", # Apple AI training (NOT Applebot, that's search)
    "Diffbot",           # Content scraper for AI products
    "omgili",            # Content aggregator
    "ImagesiftBot",
    "magpie-crawler",
    "YouBot",            # You.com
    # Aggressive SEO / link scrapers
    "AhrefsBot",
    "MJ12bot",
    "SemrushBot",
    "DotBot",
    "BLEXBot",
    "DataForSeoBot",
    "PetalBot",          # Huawei
    "AspiegelBot",       # Huawei (legacy UA)
    "SeekportBot",
    "ZoominfoBot",
    "BUbiNG",
    "proximic",
    "TurnitinBot",
    "MauiBot",
]


@bp.get("/robots.txt")
def robots_txt():
    """Crawler policy — public/indexable routes plus an explicit bad-bot block.

    Two layers cooperate here:

      1. This robots.txt asks polite crawlers to stay out of private paths
         and disallows the bots listed in ``_BAD_BOTS`` entirely. AI-training
         crawlers (GPTBot, ClaudeBot, CCBot, …) generally honour this.
      2. nginx in front of the app blocks the same UAs at the HTTP layer
         (HTTP 403) and rate-limits well-behaved search crawlers. See
         ``deploy/nginx.conf.example``.

    Mirrors the per-page ``<meta name="robots">`` policy in the templates.
    """
    cfg = current_app.config
    base = cfg["BASE_URL"].rstrip("/")

    lines: list[str] = [
        "# OpenKeepr robots policy",
        "# Hard enforcement happens in nginx (deploy/nginx.conf.example).",
        "# This file is the polite-layer signal.",
        "",
        # ── Bad bots: full disallow ──────────────────────────────────────
    ]
    for bot in _BAD_BOTS:
        lines.append(f"User-agent: {bot}")
    lines += [
        "Disallow: /",
        "",
        # ── Everyone else: index public pages, stay out of private ones ─
        "User-agent: *",
        # Be gentle so even unrated bots don't hammer the public site.
        # Googlebot ignores Crawl-delay (set rate in Search Console instead),
        # but Bing / Yandex / DuckDuckGo / most others honour it.
        "Crawl-delay: 10",
        "Disallow: /m/",
        "Disallow: /admin",
        "Disallow: /admin/",
        "Disallow: /auth/",
        "Disallow: /api/",
        "Allow: /",
        "",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap_xml():
    """Tiny sitemap covering the public, indexable pages only.

    Message URLs (`/m/<id>`) are deliberately excluded — they are private,
    short-lived, and must not be discoverable by crawlers.
    """
    cfg = current_app.config
    base = cfg["BASE_URL"].rstrip("/")
    public_endpoints = [
        "main.index",
        "main.about",
        "main.api_docs",
        "main.release_notes",
        "legal.privacy",
        "legal.cookies",
        "legal.security_policy",
    ]
    urls = []
    for endpoint in public_endpoints:
        try:
            path = url_for(endpoint)
        except Exception:
            continue
        urls.append(f"{base}{path}")
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml_lines.extend(["  <url>", f"    <loc>{url}</loc>", "  </url>"])
    xml_lines.append("</urlset>\n")
    return Response("\n".join(xml_lines), mimetype="application/xml")


@bp.get("/.well-known/security.txt")
def security_txt():
    """RFC 9116 security.txt — auto-renewed each request.

    The `Expires:` line is always set to NOW + SECURITY_EXPIRES_DAYS so it
    never goes stale. Sign with PGP at deploy time if you want stricter
    integrity (out of scope for this build).
    """
    cfg = current_app.config
    expires_in = cfg["SECURITY_EXPIRES_DAYS"]
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    policy_url = cfg["SECURITY_POLICY_URL"] or (cfg["BASE_URL"].rstrip("/") + url_for("legal.security_policy"))
    lines = [
        f"Contact: {cfg['SECURITY_CONTACT']}",
        f"Expires: {expires_at}",
        f"Policy: {policy_url}",
        "Preferred-Languages: en, nl",
        f"Canonical: {cfg['BASE_URL'].rstrip('/')}/.well-known/security.txt",
        "",
        "# This file is generated dynamically; the Expires field is renewed",
        "# on every request, so it can never go stale.",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/plain")
