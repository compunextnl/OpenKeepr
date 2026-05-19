/* Core front-end glue: theme, CSRF, copy buttons, language detection. */
(function () {
  'use strict';

  // --- Theme toggle ---
  // Initial visit: theme follows OS ('auto'). Once the user clicks, we
  // commit to an explicit light/dark choice. Clicking always flips to the
  // *opposite* of what's currently rendered — that guarantees every click
  // produces a visible change. (The old 3-state cycle could land on 'auto'
  // which silently resolved to the same theme as the current dark/light
  // pref, making the first click look like a no-op.)
  // Tiny i18n helper — looks up the key in window.__OKP_I18N (injected by
  // base.html via Jinja's _()), falls back to the English source string.
  function t(key) {
    var dict = window.__OKP_I18N;
    return (dict && Object.prototype.hasOwnProperty.call(dict, key)) ? dict[key] : key;
  }

  var ICONS = { auto: 'bi-circle-half', light: 'bi-sun', dark: 'bi-moon-stars' };
  function labelFor(pref) {
    if (pref === 'light') return t('Theme: light');
    if (pref === 'dark')  return t('Theme: dark');
    return t('Theme: auto');
  }

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
    var label = labelFor(pref);
    btn.setAttribute('title', label);
    btn.setAttribute('aria-label', label);
  }

  var toggle = document.getElementById('theme-toggle');
  if (toggle) {
    // Sync the icon with whatever was stored (or 'auto' on first visit)
    updateToggleUI(localStorage.getItem('theme') || 'auto');

    toggle.addEventListener('click', function () {
      // Always flip to the opposite of what's currently rendered.
      applyTheme(renderedTheme() === 'dark' ? 'light' : 'dark');
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
  window.OpenKeepr.t = t;
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
