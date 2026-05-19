/* Core front-end glue: theme, CSRF, copy buttons, language detection. */
(function () {
  'use strict';

  // --- Theme toggle (auto → light → dark → auto) ---
  // Cycle order is chosen so each click is *visibly* different even when
  // starting from 'auto' (where the rendered theme already matches one of
  // light/dark).
  var ICONS = { auto: 'bi-circle-half', light: 'bi-sun', dark: 'bi-moon-stars' };
  var LABELS = { auto: 'Theme: auto', light: 'Theme: light', dark: 'Theme: dark' };

  function renderedTheme() {
    return document.documentElement.getAttribute('data-bs-theme') || 'light';
  }
  function applyTheme(pref) {
    var effective = pref;
    if (pref === 'auto') {
      effective = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-bs-theme', effective);
    localStorage.setItem('theme', pref);
    updateToggleUI(pref);
  }
  function updateToggleUI(pref) {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    var icon = btn.querySelector('i');
    if (icon) icon.className = 'bi ' + (ICONS[pref] || ICONS.auto);
    btn.setAttribute('title', LABELS[pref] || LABELS.auto);
    btn.setAttribute('aria-label', LABELS[pref] || LABELS.auto);
  }

  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    // Sync the icon with whatever was stored (or 'auto' on first visit)
    updateToggleUI(localStorage.getItem('theme') || 'auto');

    toggle.addEventListener('click', function () {
      var current = localStorage.getItem('theme') || 'auto';
      var next;
      if (current === 'auto') {
        // First explicit toggle: flip away from what's currently rendered
        next = renderedTheme() === 'dark' ? 'light' : 'dark';
      } else if (current === 'light') {
        next = 'dark';
      } else {
        next = 'auto';
      }
      applyTheme(next);
    });
  }

  // React to OS-level theme changes when in auto mode
  try {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
      if ((localStorage.getItem('theme') || 'auto') === 'auto') applyTheme('auto');
    });
  } catch (e) { /* older browsers */ }

  // --- Copy-to-clipboard helpers ---
  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var sel = btn.getAttribute('data-target');
      var el = sel && document.querySelector(sel);
      if (!el) return;
      var val = (el.value !== undefined) ? el.value : el.textContent;
      navigator.clipboard.writeText(val).then(function () {
        var prev = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i>';
        setTimeout(function () { btn.innerHTML = prev; }, 1200);
      });
    });
  });

  // --- Cookie banner ---
  var banner = document.getElementById('cookie-banner');
  if (banner) {
    if (!localStorage.getItem('cookie-ack')) banner.classList.remove('d-none');
    var ok = document.getElementById('cookie-accept');
    if (ok) ok.addEventListener('click', function () {
      localStorage.setItem('cookie-ack', '1');
      banner.classList.add('d-none');
    });
  }

  // --- Expose CSRF helper for fetch() callers ---
  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute('content') : '';
  }
  window.OpenKeepr = window.OpenKeepr || {};
  window.OpenKeepr.csrfToken = csrfToken;
  window.OpenKeepr.fetchJSON = async function (url, options) {
    options = options || {};
    options.headers = Object.assign(
      { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), 'Accept': 'application/json' },
      options.headers || {}
    );
    options.credentials = 'same-origin';
    var r = await fetch(url, options);
    var text = await r.text();
    var data;
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { error: 'invalid_response' }; }
    if (!r.ok) { var err = new Error(data.error || ('HTTP ' + r.status)); err.status = r.status; err.data = data; throw err; }
    return data;
  };
})();
