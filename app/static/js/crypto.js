/* ---------------------------------------------------------------------------
 * OpenKeepr — client-side crypto (WebCrypto)
 *
 * AES-256-GCM. The 256-bit key is generated in the browser, exported as raw
 * bytes, base64-url encoded, and placed in the URL fragment. It is NEVER
 * sent to the server.
 *
 * Layout in the fragment:
 *
 *   https://host/m/<id>#<base64url(key)>
 *
 * For backward compatibility, an optional `:code` suffix lets the sender
 * pre-fill the 6-digit security code (handy when sharing both via the same
 * channel — usually NOT recommended).
 *
 *   https://host/m/<id>#<base64url(key)>:<code>
 * --------------------------------------------------------------------------- */

(function (global) {
  'use strict';

  const enc = new TextEncoder();
  const dec = new TextDecoder();

  function b64urlEncode(bytes) {
    let s = btoa(String.fromCharCode.apply(null, bytes));
    return s.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function b64urlDecode(str) {
    str = String(str).replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) str += '=';
    const bin = atob(str);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  async function generateKey() {
    return crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt']);
  }
  async function exportRawKey(key) {
    const raw = await crypto.subtle.exportKey('raw', key);
    return new Uint8Array(raw);
  }
  async function importRawKey(bytes) {
    return crypto.subtle.importKey('raw', bytes, { name: 'AES-GCM' }, true, ['encrypt', 'decrypt']);
  }

  async function encryptString(plaintext) {
    const key = await generateKey();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const salt = crypto.getRandomValues(new Uint8Array(16)); // reserved for future KDF use
    const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, enc.encode(plaintext));
    const rawKey = await exportRawKey(key);
    return {
      ciphertext_b64: b64urlEncode(new Uint8Array(ct)),
      iv_b64: b64urlEncode(iv),
      salt_b64: b64urlEncode(salt),
      key_b64: b64urlEncode(rawKey),  // returned to caller — placed in URL fragment
    };
  }

  async function decryptString(ciphertext_b64, iv_b64, key_b64) {
    const key = await importRawKey(b64urlDecode(key_b64));
    const iv = b64urlDecode(iv_b64);
    const ct = b64urlDecode(ciphertext_b64);
    const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: iv }, key, ct);
    return dec.decode(pt);
  }

  function parseFragment(fragment) {
    // Strip leading '#'
    if (!fragment) return { key: null, code: null };
    const raw = fragment.replace(/^#/, '');
    if (!raw) return { key: null, code: null };
    const idx = raw.indexOf(':');
    if (idx === -1) return { key: raw, code: null };
    return { key: raw.slice(0, idx), code: raw.slice(idx + 1) };
  }

  global.OpenKeepr = global.OpenKeepr || {};
  global.OpenKeepr.crypto = {
    encryptString,
    decryptString,
    parseFragment,
    b64urlEncode,
    b64urlDecode,
  };
})(window);
