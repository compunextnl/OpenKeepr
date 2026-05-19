/* Composer: encrypts the message in-browser and POSTs ciphertext only. */
(function () {
  'use strict';

  var form = document.getElementById('composer');
  if (!form) return;

  // Live Markdown preview
  var textarea = document.getElementById('msg-text');
  var isMd = document.getElementById('is-markdown');
  var previewBtn = document.getElementById('preview-tab-btn');
  var preview = document.getElementById('markdown-preview');
  function renderPreview() {
    if (!preview) return;
    var src = textarea.value || '';
    if (isMd.checked && window.marked && window.DOMPurify) {
      preview.innerHTML = DOMPurify.sanitize(marked.parse(src));
    } else {
      preview.textContent = src;
    }
  }
  if (previewBtn) previewBtn.addEventListener('click', renderPreview);
  textarea.addEventListener('input', function () { /* lazy: only when previewed */ });

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var btn = document.getElementById('create-btn');
    btn.disabled = true;

    try {
      var plain = textarea.value;
      if (!plain || plain.trim().length === 0) {
        alert('Please enter a message.');
        return;
      }
      var enc = await OpenKeepr.crypto.encryptString(plain);

      var recipients = (document.getElementById('recipients').value || '')
        .split(/[,;\s]+/).map(function (s) { return s.trim(); }).filter(Boolean);

      var payload = {
        ciphertext_b64: enc.ciphertext_b64,
        iv_b64:         enc.iv_b64,
        salt_b64:       enc.salt_b64,
        is_markdown:    isMd.checked,
        expires_in_hours: parseInt(document.getElementById('expires-in').value, 10),
        max_opens:        parseInt(document.getElementById('max-opens').value, 10) || null,
        recipients:       recipients,
        use_security_code: recipients.length === 0,
      };

      var res = await OpenKeepr.fetchJSON('/m/create', { method: 'POST', body: JSON.stringify(payload) });

      var url = res.url + '#' + enc.key_b64;
      var expiry = new Date(res.expires_at).toLocaleString();
      document.getElementById('result-url').value = url;
      document.getElementById('result-expiry').value = expiry;

      var codeWrap = document.getElementById('result-code-wrap');
      var codeInput = document.getElementById('result-code');
      var codeValue = res.security_code || '';
      if (codeValue) {
        codeInput.value = codeValue;  // no dash — display the raw 6 digits
        codeWrap.classList.remove('d-none');
      } else {
        codeWrap.classList.add('d-none');
      }

      // Build the "copy-all" bundle that the user can paste straight into
      // an e-mail / chat. Keys are NOT localised — they're meant to be
      // unambiguous in any inbox.
      var bundle = 'Link: ' + url + '\nExpires: ' + expiry;
      if (codeValue) bundle += '\nVerification code: ' + codeValue;
      var bundleInput = document.getElementById('result-bundle');
      if (bundleInput) bundleInput.value = bundle;

      var modal = new bootstrap.Modal(document.getElementById('result-modal'));
      modal.show();

      // Clear the plaintext from memory
      textarea.value = '';
      if (preview) preview.innerHTML = '';
    } catch (err) {
      alert('Failed to create message: ' + (err && err.message));
    } finally {
      btn.disabled = false;
    }
  });
})();
