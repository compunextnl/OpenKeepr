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
    // Disable the submit button while in flight — protects against
    // double-clicks (which would otherwise send two e-mails).
    var submitBtn = stepEmail.querySelector('button[type="submit"]');
    var origLabel = submitBtn ? submitBtn.innerHTML : null;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }
    try {
      await OpenKeepr.fetchJSON('/m/' + publicId + '/request-code', { method: 'POST', body: JSON.stringify({ email: email }) });
      stepEmail.classList.add('d-none');
      stepCode.classList.remove('d-none');
      document.getElementById('code-instructions').textContent = 'A 6-digit code has been sent if your e-mail is allowed.';
      stepCode.dataset.email = email;
    } catch (err) {
      showError('Could not request a code.');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origLabel;
      }
    }
  });

  // Cache the gate credentials so attachment downloads can re-use them.
  var gateState = { email: null, code: null };

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

    gateState.email = email;
    gateState.code = code;

    [stepEmail, stepCode, stepDirect].forEach(function (el) { el && el.classList.add('d-none'); });
    revealed.classList.remove('d-none');

    // Show attachments (if any), now that the gate has passed.
    if (data.attachments && data.attachments.length) {
      setupAttachments(data.attachments);
    }
  }

  // ----- Attachment helpers ---------------------------------------------------

  var fmtBytes = function (n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1024 / 1024).toFixed(1) + ' MB';
  };

  // In-memory cache of decrypted attachments, so "Download all" doesn't
  // re-fetch + re-decrypt files the user already opened individually.
  var decryptedCache = {};

  async function fetchAndDecrypt(attId) {
    if (decryptedCache[attId]) return decryptedCache[attId];
    var body = { email: gateState.email, code: gateState.code };
    var resp = await fetch('/m/' + publicId + '/a/' + attId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': OpenKeepr.csrfToken() },
      credentials: 'same-origin',
      body: JSON.stringify(body)
    });
    if (!resp.ok) throw new Error('download_failed');
    var ivB64 = resp.headers.get('X-OpenKeepr-IV');
    var ct = new Uint8Array(await resp.arrayBuffer());
    var iv = OpenKeepr.crypto.b64urlDecode(ivB64);
    var plain = await OpenKeepr.crypto.decryptAttachment(parsed.key, iv, ct);
    decryptedCache[attId] = plain;
    return plain;
  }

  function triggerDownload(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = filename || 'file';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { a.remove(); URL.revokeObjectURL(url); }, 500);
  }

  function setupAttachments(list) {
    var section = document.getElementById('attachments-section');
    var ul = document.getElementById('attachments-list');
    var count = document.getElementById('att-count');
    var dlAll = document.getElementById('download-all-btn');
    if (!section || !ul) return;
    section.classList.remove('d-none');
    count.textContent = '(' + list.length + ')';
    if (list.length > 1) dlAll.classList.remove('d-none');
    ul.innerHTML = '';

    list.forEach(function (att) {
      var li = document.createElement('li');
      li.className = 'list-group-item d-flex justify-content-between align-items-center';

      var meta = document.createElement('span');
      meta.innerHTML = '<i class="bi bi-file-earmark-lock"></i> ' +
        '<span class="text-body-secondary">' + fmtBytes(att.size) + '</span>';

      var btn = document.createElement('button');
      btn.type = 'button'; btn.className = 'btn btn-sm btn-outline-primary';
      btn.innerHTML = '<i class="bi bi-download"></i> Decrypt &amp; download';

      btn.addEventListener('click', async function () {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        try {
          var plain = await fetchAndDecrypt(att.id);
          var blob = new Blob([plain.bytes], { type: plain.type || 'application/octet-stream' });
          meta.innerHTML = '<i class="bi bi-file-earmark"></i> ' +
            (plain.name.replace(/</g, '&lt;')) +
            ' <span class="text-body-secondary">(' + fmtBytes(att.size) + ')</span>';
          triggerDownload(blob, plain.name);
          btn.innerHTML = '<i class="bi bi-check2"></i> Saved';
          btn.classList.remove('btn-outline-primary'); btn.classList.add('btn-outline-success');
        } catch (err) {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-x"></i> Failed';
          btn.classList.add('btn-outline-danger');
        }
      });

      li.appendChild(meta);
      li.appendChild(btn);
      ul.appendChild(li);
    });

    if (dlAll && list.length > 1) {
      dlAll.addEventListener('click', async function () {
        dlAll.disabled = true;
        var prev = dlAll.innerHTML;
        dlAll.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Preparing…';
        try {
          var files = {};
          for (var i = 0; i < list.length; i++) {
            var p = await fetchAndDecrypt(list[i].id);
            // Avoid name collisions
            var name = p.name, n = 1;
            while (files[name]) { name = p.name.replace(/(\.[^.]+)?$/, ' (' + (++n) + ')$1'); }
            files[name] = p.bytes;
          }
          var zipped = fflate.zipSync(files);
          triggerDownload(new Blob([zipped], { type: 'application/zip' }), 'attachments.zip');
          dlAll.innerHTML = prev;
        } catch (err) {
          dlAll.innerHTML = '<i class="bi bi-x"></i> Failed';
        } finally {
          dlAll.disabled = false;
        }
      });
    }
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
