/* Viewer: fetches ciphertext after passing the gate, then decrypts in-browser. */
(function () {
  'use strict';

  var card = document.querySelector('[data-public-id]');
  if (!card) return;
  var publicId    = card.dataset.publicId;
  var reqEmail    = card.dataset.requiresEmail === 'true';
  var reqCode     = card.dataset.requiresCode === 'true';
  var isMarkdown  = card.dataset.isMarkdown === 'true';
  var maxOpens    = parseInt(card.dataset.maxOpens || '0', 10) || null;

  var parsed = OpenKeepr.crypto.parseFragment(window.location.hash);
  if (!parsed.key) {
    document.getElementById('missing-key').classList.remove('d-none');
    return;
  }
  // Remove the fragment from the URL bar so casual screen-sharers don't leak the key
  history.replaceState(null, '', window.location.pathname + window.location.search);

  // Pick the right gate
  var stepEmail  = document.getElementById('email-form');
  var stepCode   = document.getElementById('code-form');
  var stepDirect = document.getElementById('direct-form');
  var revealed   = document.getElementById('revealed');
  var contentEl  = document.getElementById('content');
  var errorEl    = document.getElementById('error');
  var meta       = document.getElementById('meta-line');
  if (meta) meta.textContent = isMarkdown ? 'Markdown' : 'plain text';

  if (reqEmail) {
    stepEmail.classList.remove('d-none');
  } else if (reqCode) {
    stepCode.classList.remove('d-none');
    if (parsed.code) document.getElementById('code-input').value = parsed.code.replace(/\D/g, '').slice(0, 6);
    document.getElementById('code-instructions').textContent = 'Enter the 6-digit verification code the sender shared with you.';
  } else {
    stepDirect.classList.remove('d-none');
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove('d-none');
  }
  function hideError() { errorEl.classList.add('d-none'); }

  if (stepEmail) stepEmail.addEventListener('submit', async function (e) {
    e.preventDefault();
    hideError();
    var email = document.getElementById('email-input').value.trim();
    try {
      await OpenKeepr.fetchJSON('/m/' + publicId + '/request-code', { method: 'POST', body: JSON.stringify({ email: email }) });
      stepEmail.classList.add('d-none');
      stepCode.classList.remove('d-none');
      document.getElementById('code-instructions').textContent = 'A 6-digit code has been sent if your e-mail is allowed.';
      // Remember the e-mail for the next step
      stepCode.dataset.email = email;
    } catch (err) { showError('Could not request a code.'); }
  });

  async function reveal(email, code) {
    var body = {};
    if (email) body.email = email;
    if (code) body.code = code;
    body.burn_after = document.getElementById('auto-burn') ? document.getElementById('auto-burn').checked : false;

    var data = await OpenKeepr.fetchJSON('/m/' + publicId + '/reveal', { method: 'POST', body: JSON.stringify(body) });
    var plain = await OpenKeepr.crypto.decryptString(data.ciphertext_b64, data.iv_b64, parsed.key);

    contentEl.classList.toggle('is-markdown', !!data.is_markdown);
    if (data.is_markdown && window.marked && window.DOMPurify) {
      contentEl.innerHTML = DOMPurify.sanitize(marked.parse(plain));
    } else {
      contentEl.textContent = plain;
    }

    [stepEmail, stepCode, stepDirect].forEach(function (el) { el && el.classList.add('d-none'); });
    revealed.classList.remove('d-none');
  }

  if (stepCode) stepCode.addEventListener('submit', async function (e) {
    e.preventDefault();
    hideError();
    var code = document.getElementById('code-input').value.trim();
    var email = stepCode.dataset.email || null;
    try { await reveal(email, code); }
    catch (err) { showError(err && err.data && err.data.error === 'invalid_credentials' ? 'Invalid e-mail or verification code.' : 'Could not retrieve the message.'); }
  });

  if (stepDirect) stepDirect.addEventListener('submit', async function (e) {
    e.preventDefault();
    hideError();
    try { await reveal(null, null); }
    catch (err) { showError('Could not retrieve the message.'); }
  });

  // Copy button
  var copyBtn = document.getElementById('copy-btn');
  if (copyBtn) copyBtn.addEventListener('click', function () {
    var text = contentEl.classList.contains('is-markdown') ? contentEl.innerText : contentEl.textContent;
    navigator.clipboard.writeText(text).then(function () {
      copyBtn.innerHTML = '<i class="bi bi-check2"></i> Copied';
      setTimeout(function () { copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> Copy'; }, 1500);
    });
  });

  var burnBtn = document.getElementById('burn-btn');
  if (burnBtn) burnBtn.addEventListener('click', function () {
    OpenKeepr.fetchJSON('/m/' + publicId + '/burn', { method: 'POST', body: '{}' })
      .finally(function () { window.location.reload(); });
  });

  // Auto-burn on leave (when the checkbox is on)
  window.addEventListener('beforeunload', function () {
    var ab = document.getElementById('auto-burn');
    if (!ab || !ab.checked || !revealed || revealed.classList.contains('d-none')) return;
    // sendBeacon survives the page unload
    var blob = new Blob([JSON.stringify({})], { type: 'application/json' });
    navigator.sendBeacon('/m/' + publicId + '/burn', blob);
  });
})();
