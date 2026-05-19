/* Composer: encrypts the message + any attachments in-browser before upload. */
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

  // --- Recipient input validation ---
  var EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;
  var recipientsInput = document.getElementById('recipients');
  var recipientsErr = document.getElementById('recipients-error');

  function parseRecipients() {
    return (recipientsInput.value || '')
      .split(/[,;\s]+/)
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }
  function showRecipientError(msg) {
    if (!recipientsErr) return;
    recipientsErr.textContent = msg;
    recipientsErr.classList.remove('d-none');
    recipientsInput.classList.add('is-invalid');
  }
  function clearRecipientError() {
    if (!recipientsErr) return;
    recipientsErr.textContent = '';
    recipientsErr.classList.add('d-none');
    recipientsInput.classList.remove('is-invalid');
  }
  recipientsInput.addEventListener('input', function () {
    var list = parseRecipients();
    var bad = list.filter(function (e) { return !EMAIL_RE.test(e); });
    if (bad.length) showRecipientError('Invalid: ' + bad.join(', '));
    else clearRecipientError();
  });

  // --- Attachments ---
  var attachDrop = document.getElementById('attach-drop');
  var attachInput = document.getElementById('attach-input');
  var attachList = document.getElementById('attach-list');
  var picked = []; // [{file, error?}]
  // Allowed types come from the `accept` attribute the server-side template
  // rendered for us (mirrors the .env config).
  var ALLOWED = attachInput ? (attachInput.getAttribute('accept') || '').split(',').map(function (s) { return s.trim().toLowerCase(); }).filter(Boolean) : [];

  function fileMatchesAllowed(file) {
    if (!ALLOWED.length) return true;
    var name = (file.name || '').toLowerCase();
    var type = (file.type || '').toLowerCase();
    for (var i = 0; i < ALLOWED.length; i++) {
      var spec = ALLOWED[i];
      if (spec.startsWith('.')) {
        if (name.endsWith(spec)) return true;
      } else if (spec.endsWith('/*')) {
        if (type.startsWith(spec.slice(0, -1))) return true;
      } else if (type === spec) {
        return true;
      }
    }
    return false;
  }

  function fmtBytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1024 / 1024).toFixed(1) + ' MB';
  }

  function updateAttachCountBadge() {
    var badge = document.getElementById('attach-count');
    if (!badge) return;
    var n = picked.length;
    if (n === 0) badge.classList.add('d-none');
    else { badge.classList.remove('d-none'); badge.textContent = String(n); }
  }
  function ensureAttachPanelOpen() {
    var panel = document.getElementById('attach-panel');
    if (!panel || !window.bootstrap) return;
    if (!panel.classList.contains('show')) {
      bootstrap.Collapse.getOrCreateInstance(panel).show();
    }
  }
  function renderAttachList() {
    updateAttachCountBadge();
    if (!attachList) return;
    attachList.innerHTML = '';
    picked.forEach(function (entry, idx) {
      var li = document.createElement('li');
      li.className = 'list-group-item d-flex justify-content-between align-items-center px-2';
      var left = document.createElement('span');
      left.innerHTML = '<i class="bi bi-paperclip"></i> ' +
        (entry.file.name.replace(/</g, '&lt;')) +
        ' <span class="text-body-secondary">(' + fmtBytes(entry.file.size) + ')</span>';
      if (entry.error) {
        left.innerHTML += ' <span class="badge text-bg-danger ms-2">' + entry.error + '</span>';
      } else if (entry.uploaded) {
        left.innerHTML += ' <span class="badge text-bg-success ms-2"><i class="bi bi-check2"></i></span>';
      } else if (entry.progress != null) {
        left.innerHTML += ' <span class="badge text-bg-info ms-2">' + Math.round(entry.progress) + '%</span>';
      }
      var rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'btn btn-sm btn-link text-danger p-0';
      rm.innerHTML = '<i class="bi bi-x-lg"></i>';
      rm.addEventListener('click', function () {
        picked.splice(idx, 1);
        renderAttachList();
      });
      li.appendChild(left);
      li.appendChild(rm);
      attachList.appendChild(li);
    });
  }

  function addFiles(fileList) {
    if (fileList && fileList.length) ensureAttachPanelOpen();
    var maxFile = (window.__OKP_CFG && window.__OKP_CFG.maxFileBytes) || (25 * 1024 * 1024);
    var maxCount = (window.__OKP_CFG && window.__OKP_CFG.maxCount) || 10;
    var maxTotal = (window.__OKP_CFG && window.__OKP_CFG.maxTotalBytes) || (100 * 1024 * 1024);
    Array.prototype.forEach.call(fileList, function (f) {
      if (picked.length >= maxCount) {
        picked.push({ file: f, error: 'Max ' + maxCount + ' files' });
        return;
      }
      var entry = { file: f };
      if (!fileMatchesAllowed(f)) entry.error = 'Type not allowed';
      else if (f.size > maxFile) entry.error = 'Too large';
      else {
        var totalSoFar = picked.reduce(function (s, e) { return s + (e.error ? 0 : e.file.size); }, 0);
        if (totalSoFar + f.size > maxTotal) entry.error = 'Exceeds total limit';
      }
      picked.push(entry);
    });
    renderAttachList();
  }

  if (attachDrop && attachInput) {
    attachInput.addEventListener('change', function (e) {
      addFiles(e.target.files);
      attachInput.value = ''; // allow re-selecting the same file
    });
    ['dragover', 'dragenter'].forEach(function (ev) {
      attachDrop.addEventListener(ev, function (e) {
        e.preventDefault();
        attachDrop.classList.add('border-primary');
      });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
      attachDrop.addEventListener(ev, function (e) {
        e.preventDefault();
        attachDrop.classList.remove('border-primary');
      });
    });
    attachDrop.addEventListener('drop', function (e) {
      if (e.dataTransfer && e.dataTransfer.files) addFiles(e.dataTransfer.files);
    });
  }

  async function uploadAttachment(publicId, key_b64, entry) {
    var enc = await OpenKeepr.crypto.encryptAttachment(key_b64, entry.file);
    var form = new FormData();
    form.append('iv', new Blob([enc.iv]));
    form.append('ciphertext', new Blob([enc.ciphertext]));
    var csrf = OpenKeepr.csrfToken();

    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/m/' + publicId + '/attachments', true);
      xhr.setRequestHeader('X-CSRFToken', csrf);
      xhr.upload.addEventListener('progress', function (e) {
        if (e.lengthComputable) {
          entry.progress = (e.loaded / e.total) * 100;
          renderAttachList();
        }
      });
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          entry.uploaded = true; entry.progress = 100; renderAttachList();
          resolve(JSON.parse(xhr.responseText));
        } else {
          var err;
          try { err = JSON.parse(xhr.responseText); } catch (e) { err = { error: 'http_' + xhr.status }; }
          entry.error = err.error || 'upload_failed'; renderAttachList();
          reject(err);
        }
      };
      xhr.onerror = function () { entry.error = 'network'; renderAttachList(); reject({ error: 'network' }); };
      xhr.send(form);
    });
  }

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

      var recipients = parseRecipients();
      var bad = recipients.filter(function (e) { return !EMAIL_RE.test(e); });
      if (bad.length) {
        showRecipientError('Please fix the invalid e-mail addresses: ' + bad.join(', '));
        recipientsInput.focus();
        return;
      }
      clearRecipientError();

      // Filter out attachments with errors before sending
      var validAttachments = picked.filter(function (p) { return !p.error; });
      var rejectedCount = picked.length - validAttachments.length;
      if (rejectedCount > 0) {
        if (!confirm(rejectedCount + ' attachment(s) will be skipped due to validation errors. Continue?')) {
          return;
        }
      }

      var enc = await OpenKeepr.crypto.encryptString(plain);

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

      // Upload attachments one by one — keeps memory pressure low and gives
      // a per-file progress bar in the list.
      for (var i = 0; i < validAttachments.length; i++) {
        await uploadAttachment(res.public_id, enc.key_b64, validAttachments[i]);
      }

      var url = res.url + '#' + enc.key_b64;
      var expiry = new Date(res.expires_at).toLocaleString();
      document.getElementById('result-url').value = url;
      document.getElementById('result-expiry').value = expiry;

      var codeWrap = document.getElementById('result-code-wrap');
      var codeInput = document.getElementById('result-code');
      var codeValue = res.security_code || '';
      if (codeValue) {
        codeInput.value = codeValue;
        codeWrap.classList.remove('d-none');
      } else {
        codeWrap.classList.add('d-none');
      }

      var bundle = 'Link: ' + url + '\nExpires: ' + expiry;
      if (codeValue) bundle += '\nVerification code: ' + codeValue;
      var bundleInput = document.getElementById('result-bundle');
      if (bundleInput) bundleInput.value = bundle;

      var modal = new bootstrap.Modal(document.getElementById('result-modal'));
      modal.show();

      textarea.value = '';
      if (preview) preview.innerHTML = '';
      picked = []; renderAttachList();
    } catch (err) {
      if (err && err.data && err.data.error === 'invalid_recipients') {
        var list = (err.data.invalid || []).join(', ');
        showRecipientError('Server rejected these e-mail addresses: ' + list);
        recipientsInput.focus();
      } else {
        alert('Failed to create message: ' + (err && (err.message || err.error)));
      }
    } finally {
      btn.disabled = false;
    }
  });
})();
