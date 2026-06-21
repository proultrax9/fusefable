/* Fusion Fable desktop renderer */
(() => {
  'use strict';

  let apiBase = '';
  let projectRoot = null;
  let fileList = [];
  let fileMap = {};
  let currentConvId = null;
  let busy = false;
  let configured = false;
  let monacoEditor = null;
  let gateways = [];

  const editor = { path: null, original: '', dirty: false, readonly: false, image: false };
  const expanded = new Set();

  const $ = (id) => document.getElementById(id);

  /* ── API ── */
  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const r = await fetch(`${apiBase}${path}`, opts);
    return r.json();
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function escCode(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* ── resizable sashes ── */
  function initSash(sashEl, panelEl, invert) {
    if (!sashEl || !panelEl) return;
    sashEl.addEventListener('mousedown', (e) => {
      e.preventDefault();
      sashEl.classList.add('dragging');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      const startX = e.clientX;
      const startW = panelEl.offsetWidth;
      const move = (ev) => {
        const dx = ev.clientX - startX;
        const w = invert ? startW - dx : startW + dx;
        const min = parseInt(panelEl.style.minWidth || 120, 10);
        const max = panelEl.classList.contains('panel-editor') ? window.innerWidth * 0.8 : 600;
        panelEl.style.width = `${Math.max(min, Math.min(max, w))}px`;
      };
      const up = () => {
        sashEl.classList.remove('dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        document.removeEventListener('mousemove', move);
        document.removeEventListener('mouseup', up);
        saveLayout();
      };
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', up);
    });
  }

  function saveLayout() {
    try {
      localStorage.setItem('ff-layout', JSON.stringify({
        explorer: $('panelExplorer').offsetWidth,
        editor: $('panelEditor').classList.contains('closed') ? 0 : $('panelEditor').offsetWidth,
      }));
    } catch (_) {}
  }

  function loadLayout() {
    try {
      const s = JSON.parse(localStorage.getItem('ff-layout') || '{}');
      if (s.explorer) $('panelExplorer').style.width = `${s.explorer}px`;
      if (s.editor > 0 && !$('panelEditor').classList.contains('closed')) {
        $('panelEditor').style.width = `${s.editor}px`;
      }
    } catch (_) {}
  }

  /* ── editor panel ── */
  function showEditorPanel() {
    $('panelEditor').classList.remove('closed');
    $('sashEditor').classList.remove('closed');
    loadLayout();
    if (monacoEditor) setTimeout(() => monacoEditor.layout(), 50);
  }

  function hideEditorPanel() {
    $('panelEditor').classList.add('closed');
    $('sashEditor').classList.add('closed');
    saveLayout();
  }

  function langForPath(p) {
    const e = (p.split('.').pop() || '').toLowerCase();
    const map = { py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
      json: 'json', html: 'html', htm: 'html', css: 'css', scss: 'scss', md: 'markdown', yml: 'yaml', yaml: 'yaml',
      sh: 'shell', bash: 'shell', rs: 'rust', go: 'go', java: 'java', cpp: 'cpp', c: 'c', sql: 'sql' };
    return map[e] || 'plaintext';
  }

  function initMonaco() {
    return new Promise((resolve) => {
      require.config({ paths: { vs: '../node_modules/monaco-editor/min/vs' } });
      require(['vs/editor/editor.main'], () => {
        monacoEditor = monaco.editor.create($('editorContainer'), {
          value: '',
          language: 'plaintext',
          theme: 'vs-dark',
          fontSize: 13,
          fontFamily: "Consolas, 'Courier New', monospace",
          lineNumbers: 'on',
          minimap: { enabled: true },
          scrollBeyondLastLine: false,
          automaticLayout: true,
          wordWrap: 'off',
          padding: { top: 8 },
        });
        monacoEditor.onDidChangeModelContent(() => {
          if (!editor.path || editor.readonly) return;
          const v = monacoEditor.getValue();
          setDirty(v !== editor.original);
        });
        monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => saveEditor());
        resolve();
      });
    });
  }

  function updateEditorTabs() {
    const tabs = $('editorTabs');
    if (!editor.path) { tabs.innerHTML = ''; return; }
    const name = editor.path.split('/').pop();
    const dot = editor.dirty ? '● ' : '';
    tabs.innerHTML = `<div class="editor-tab active">${dot}${esc(name)}<button class="close-tab" id="closeTab">×</button></div>`;
    $('closeTab').onclick = () => closeEditor();
  }

  function setDirty(d) {
    editor.dirty = d;
    updateEditorTabs();
    const row = editor.path && document.querySelector(`.tree-row[data-path="${CSS.escape(editor.path)}"]`);
    if (row) row.classList.toggle('dirty', d);
  }

  async function openFile(path) {
    const f = fileMap[path];
    if (!f) return;
    if (editor.dirty && editor.path !== path && !confirm(`Discard changes in ${editor.path}?`)) return;
    if (f.binary && !f.image) { $('statusText').textContent = 'Binary file'; return; }
    if (f.image) return openImage(path);
    return openText(path);
  }

  async function openText(path) {
    const r = await api('POST', '/api/open_file', { root: projectRoot, path });
    if (r.error) return;
    editor.path = path;
    editor.original = r.content;
    editor.readonly = !!r.readonly;
    editor.image = false;
    showEditorPanel();
    if (monacoEditor) {
      monacoEditor.updateOptions({ readOnly: editor.readonly });
      monaco.editor.setModelLanguage(monacoEditor.getModel(), langForPath(path));
      monacoEditor.setValue(r.content);
    }
    setDirty(false);
    markOpenRow(path);
    updateEditorTabs();
    $('edInfo').textContent = path + (editor.readonly ? ' · read-only' : '');
    updateCtxBar();
    if (!editor.readonly) monacoEditor.focus();
  }

  async function openImage(path) {
    const r = await api('POST', '/api/read_image', { root: projectRoot, path });
    if (r.error) return;
    editor.path = path;
    editor.image = true;
    editor.readonly = true;
    showEditorPanel();
    $('editorContainer').innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;padding:16px"><img src="${r.data_uri}" style="max-width:100%;max-height:100%"></div>`;
    updateEditorTabs();
    markOpenRow(path);
  }

  function closeEditor(force) {
    if (!force && editor.dirty && !confirm('Discard unsaved changes?')) return;
    editor.path = null;
    editor.original = '';
    editor.dirty = false;
    editor.image = false;
    document.querySelectorAll('.tree-row.open,.tree-row.dirty').forEach((x) => x.classList.remove('open', 'dirty'));
    hideEditorPanel();
    updateEditorTabs();
    if (monacoEditor) {
      monacoEditor.setValue('');
      monaco.editor.setModelLanguage(monacoEditor.getModel(), 'plaintext');
    }
    $('editorContainer').innerHTML = '';
    if (monacoEditor) $('editorContainer').appendChild(monacoEditor.getDomNode());
    updateCtxBar();
  }

  async function saveEditor() {
    if (!editor.path || editor.readonly || editor.image || !editor.dirty || !monacoEditor) return;
    const content = monacoEditor.getValue();
    const r = await api('POST', '/api/save_file', { root: projectRoot, path: editor.path, content });
    if (!r.ok) return;
    editor.original = content;
    setDirty(false);
    const toast = $('edToast');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 1200);
  }

  function markOpenRow(path) {
    document.querySelectorAll('.tree-row.open').forEach((x) => x.classList.remove('open'));
    const row = document.querySelector(`.tree-row[data-path="${CSS.escape(path)}"]`);
    if (row) row.classList.add('open');
  }

  /* ── file tree ── */
  function buildTree(files) {
    const root = { dirs: {}, files: [] };
    files.forEach((f) => {
      const parts = f.path.split('/');
      let node = root;
      for (let i = 0; i < parts.length - 1; i++) {
        const d = parts[i];
        const p = parts.slice(0, i + 1).join('/');
        node.dirs[d] = node.dirs[d] || { dirs: {}, files: [], path: p };
        node = node.dirs[d];
      }
      node.files.push(f);
    });
    return root;
  }

  function renderNode(node, depth, out) {
    Object.keys(node.dirs).sort().forEach((name) => {
      const dir = node.dirs[name];
      const isOpen = expanded.has(dir.path);
      const row = document.createElement('div');
      row.className = 'tree-row';
      row.style.paddingLeft = `${depth * 12 + 4}px`;
      row.innerHTML = `<span class="chev">${isOpen ? '▾' : '▸'}</span><span class="icon">📁</span><span class="name">${esc(name)}</span>`;
      row.onclick = () => { isOpen ? expanded.delete(dir.path) : expanded.add(dir.path); renderTree(); };
      out.appendChild(row);
      if (isOpen) renderNode(dir, depth + 1, out);
    });
    node.files.slice().sort((a, b) => a.path.localeCompare(b.path)).forEach((f) => {
      const name = f.path.split('/').pop();
      const row = document.createElement('div');
      row.className = 'tree-row' + (editor.path === f.path ? ' open' : '');
      row.dataset.path = f.path;
      row.style.paddingLeft = `${depth * 12 + 16}px`;
      row.innerHTML = `<span class="chev"></span><span class="icon">${f.image ? '🖼' : f.binary ? '▫' : '📄'}</span><span class="name">${esc(name)}</span><span class="dirty"></span>`;
      row.onclick = () => openFile(f.path);
      out.appendChild(row);
    });
  }

  function renderTree() {
    const el = $('fileTree');
    el.innerHTML = '';
    if (!projectRoot) {
      el.innerHTML = '<div class="empty-tree">Open a folder to browse files.<br>Click a file once → editor opens on the right.</div>';
      return;
    }
    if (!fileList.length) {
      el.innerHTML = '<div class="empty-tree">No readable files.</div>';
      return;
    }
    renderNode(buildTree(fileList), 0, el);
    $('sbFiles').textContent = `${fileList.filter((f) => !f.binary).length} files`;
  }

  async function openFolder() {
    if (editor.dirty && !confirm('Unsaved changes — open new folder anyway?')) return;
    const path = await window.fusionDesktop.pickFolder();
    if (!path) return;
    $('statusText').textContent = 'Opening…';
    const r = await api('POST', '/api/open_project', { path });
    if (r.error) { $('statusText').textContent = 'Error'; return; }
    closeEditor(true);
    newChat();
    projectRoot = r.path;
    fileList = r.files || [];
    fileMap = {};
    fileList.forEach((f) => { fileMap[f.path] = f; });
    expanded.clear();
    const fname = path.split(/[\\/]/).filter(Boolean).pop() || path;
    $('projectLabel').textContent = fname.toUpperCase();
    $('winTitle').textContent = fname;
    $('sbProject').textContent = fname;
    document.title = `${fname} — Fusion Fable`;
    renderTree();
    showMessagesEmpty();
    $('statusText').textContent = 'Ready';
    updateCtxBar();
  }

  /* ── chat / markdown ── */
  window.copyCode = (btn) => {
    navigator.clipboard.writeText(decodeURIComponent(btn.dataset.c)).then(() => {
      btn.textContent = 'Copied';
      setTimeout(() => { btn.textContent = 'Copy'; }, 1200);
    });
  };

  function mdToHtml(src) {
    const blocks = [];
    src = src.replace(/```(\w*)\n?([\s\S]*?)```/g, (m, lang, code) => {
      blocks.push({ lang, code });
      return `@@B${blocks.length - 1}@@`;
    });
    let h = esc(src);
    h = h.replace(/^### (.*)$/gm, '<h3>$1</h3>').replace(/^## (.*)$/gm, '<h2>$1</h2>').replace(/^# (.*)$/gm, '<h1>$1</h1>');
    h = h.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>');
    h = h.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    h = h.replace(/\n/g, '<br>');
    h = h.replace(/@@B(\d+)@@/g, (m, i) => {
      const b = blocks[i];
      if (!b) return m;
      return `<div class="code-block"><div class="code-block-head"><span>${esc(b.lang || 'code')}</span><button onclick="copyCode(this)" data-c="${encodeURIComponent(b.code)}">Copy</button></div><pre>${escCode(b.code)}</pre></div>`;
    });
    return h;
  }

  function showMessagesEmpty() {
    if (projectRoot) {
      $('messages').innerHTML = '<div class="welcome"><h2>Ready</h2><p>Type a task — AI reads your project and edits files automatically.</p><ul><li>Fix bug in main.py</li><li>Add login feature</li><li>@filename to reference a file</li></ul></div>';
    } else {
      $('messages').innerHTML = `<div class="welcome"><h2>Fusion Fable</h2><p>Cursor-style AI fusion for Fable 5 — open a project to start.</p><button class="primary-btn" id="welcomeOpen">Open Folder</button><ul><li>Chat fills the center</li><li>Files on the left — click to open editor on the right</li><li>Drag panel borders to resize</li></ul></div>`;
      $('welcomeOpen').onclick = openFolder;
    }
    updateCtxBar();
  }

  function addMsg(role, extraClass) {
    $('messages').querySelector('.welcome')?.remove();
    const block = document.createElement('div');
    block.className = `msg-block ${role}${extraClass ? ' ' + extraClass : ''}`;
    block.innerHTML = `<div class="role">${role === 'user' ? 'You' : 'Agent'}</div><div class="content"></div>`;
    $('messages').appendChild(block);
    $('chatScroll').scrollTop = 99999;
    return block.querySelector('.content');
  }

  function parseMentions(text) {
    const out = [];
    if (!text) return out;
    for (const m of text.matchAll(/@([^\s@]+)/g)) {
      const q = m[1].toLowerCase();
      const hit = fileList.find((f) => !f.binary && (f.path.toLowerCase() === q || f.path.toLowerCase().endsWith('/' + q) || f.path.split('/').pop().toLowerCase() === q));
      if (hit) out.push(hit.path);
    }
    return [...new Set(out)];
  }

  function editorOverrides() {
    if (!editor.path || editor.image || !editor.dirty || !monacoEditor) return {};
    return { [editor.path]: monacoEditor.getValue() };
  }

  function updateCtxBar() {
    const bar = $('ctxBar');
    if (!projectRoot) { bar.classList.add('hidden'); return; }
    bar.classList.remove('hidden');
    const chips = [`<span class="ctx-chip">${fileList.filter((f) => !f.binary).length} files</span>`];
    if (editor.path && !editor.image) chips.push(`<span class="ctx-chip">${esc(editor.path)}</span>`);
    parseMentions($('composer').value).forEach((p) => chips.push(`<span class="ctx-chip muted">@${esc(p)}</span>`));
    bar.innerHTML = chips.join('');
  }

  async function afterEdits(r) {
    if (!r.edits?.length || !projectRoot) return;
    const ok = r.edits.filter((e) => e.ok).map((e) => e.path);
    if (!ok.length) return;
    const lr = await api('POST', '/api/list_files', { path: projectRoot });
    if (lr.files) {
      fileList = lr.files;
      fileMap = {};
      fileList.forEach((f) => { fileMap[f.path] = f; });
      renderTree();
    }
    if (editor.path && ok.includes(editor.path)) await openText(editor.path);
    else if (ok.length) await openText(ok[0]);
  }

  async function ask() {
    const text = $('composer').value.trim();
    if (!text || busy) return;
    if (!projectRoot) {
      addMsg('user').textContent = text;
      $('composer').value = '';
      addMsg('bot').textContent = 'Open a folder first — click 📂 in Explorer.';
      openFolder();
      return;
    }
    busy = true;
    $('btnSend').disabled = true;
    $('statusText').textContent = 'Thinking';
    addMsg('user').textContent = text;
    $('composer').value = '';
    updateCtxBar();
    const thinking = addMsg('bot', 'thinking');
    thinking.textContent = 'Thinking…';
    const payload = { question: text, conversation_id: currentConvId, project_root: projectRoot };
    try {
      const cx = await api('POST', '/api/read_context', {
        root: projectRoot,
        all_paths: fileList.filter((f) => !f.binary).map((f) => f.path),
        open_path: editor.path && !editor.image ? editor.path : '',
        mentioned: parseMentions(text),
        overrides: editorOverrides(),
      });
      if (cx.context) payload.context = cx.context;
    } catch (_) {}
    const r = await api('POST', '/api/ask', payload);
    thinking.parentElement.remove();
    $('statusText').textContent = 'Ready';
    $('btnSend').disabled = false;
    if (r.error) {
      addMsg('bot', 'error').textContent = '⚠ ' + r.error;
      busy = false;
      return;
    }
    currentConvId = r.conversation_id;
    const body = addMsg('bot');
    body.innerHTML = mdToHtml(r.answer);
    await afterEdits(r);
    refreshChats();
    busy = false;
    $('composer').focus();
    updateCtxBar();
    $('chatScroll').scrollTop = 99999;
  }

  async function refreshChats() {
    const list = await api('GET', '/api/conversations');
    const el = $('chatList');
    el.innerHTML = '';
    if (!list.length) { el.innerHTML = '<div class="empty-tree">No chats yet</div>'; return; }
    list.forEach((c) => {
      const it = document.createElement('div');
      it.className = 'chat-list-item' + (c.id === currentConvId ? ' active' : '');
      it.innerHTML = `<span>${esc(c.title)}</span><button class="del">×</button>`;
      it.querySelector('span').onclick = () => loadConv(c.id);
      it.querySelector('.del').onclick = async (e) => {
        e.stopPropagation();
        await api('DELETE', `/api/conversations/${c.id}`);
        if (currentConvId === c.id) newChat();
        else refreshChats();
      };
      el.appendChild(it);
    });
  }

  async function loadConv(id) {
    const c = await api('GET', `/api/conversations/${id}`);
    if (!c) return;
    currentConvId = id;
    $('messages').innerHTML = '';
    $('chatTabTitle').textContent = c.title || 'Chat';
    if (!c.messages?.length) showMessagesEmpty();
    else {
      c.messages.forEach((m) => {
        const body = addMsg(m.role === 'user' ? 'user' : 'bot');
        if (m.role === 'user') body.textContent = m.content;
        else body.innerHTML = mdToHtml(m.content);
      });
    }
    $('historyDropdown').classList.add('hidden');
    refreshChats();
  }

  function newChat() {
    currentConvId = null;
    $('chatTabTitle').textContent = 'New Chat';
    showMessagesEmpty();
    refreshChats();
    $('composer').focus();
  }

  /* ── settings ── */
  function makeProvRow(data) {
    data = data || {};
    const row = document.createElement('div');
    row.className = 'prov';
    const opts = gateways.concat(['custom']).map((g) => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
    row.innerHTML = `<div class="row"><select class="p-gw">${opts}</select><input class="p-key" type="password" placeholder="${data.has_key ? '•••• saved' : 'API key'}"><button class="p-del">×</button></div><input class="p-base extra hidden" placeholder="base URL"><input class="p-models extra" placeholder="models, comma-separated">`;
    const gw = row.querySelector('.p-gw');
    const base = row.querySelector('.p-base');
    gw.value = data.gateway || 'openrouter';
    if (data.gateway && !gateways.includes(data.gateway)) gw.value = 'custom';
    const syncBase = () => base.classList.toggle('hidden', gw.value !== 'custom');
    syncBase();
    gw.onchange = syncBase;
    if (gw.value === 'custom') base.value = data.base_url || '';
    row.querySelector('.p-key').value = data.api_key || '';
    row.querySelector('.p-models').value = (data.models || []).join(', ');
    row.querySelector('.p-del').onclick = () => { row.remove(); if (!$('provList').children.length) makeProvRow(); };
    $('provList').appendChild(row);
  }

  function collectProviders() {
    return [...$('provList').querySelectorAll('.prov')].map((row) => ({
      gateway: row.querySelector('.p-gw').value,
      base_url: row.querySelector('.p-base').value,
      api_key: row.querySelector('.p-key').value,
      models: row.querySelector('.p-models').value,
    }));
  }

  async function openSettings() {
    const st = await api('GET', '/api/status');
    gateways = st.gateways || [];
    $('provList').innerHTML = '';
    (st.providers?.length ? st.providers : [{ gateway: 'openrouter' }]).forEach(makeProvRow);
    $('setJudge').value = st.judge_model || '';
    $('setCompress').checked = !!st.compress;
    $('setErr').textContent = '';
    $('settingsModal').classList.remove('hidden');
  }

  async function testModels() {
    $('setErr').textContent = 'Testing…';
    const r = await api('GET', '/api/test_models');
    if (!r.results?.length) {
      $('setErr').textContent = 'No models configured';
      return;
    }
    const lines = r.results.map((x) => (x.ok ? `✓ ${x.model}` : `✗ ${x.model}: ${x.error}`));
    $('setErr').innerHTML = lines.map(esc).join('<br>');
    $('setErr').style.color = r.ok ? 'var(--success)' : 'var(--danger)';
  }

  async function saveSettings() {
    const r = await api('POST', '/api/settings', {
      providers: collectProviders(),
      judge_model: $('setJudge').value,
      compress: $('setCompress').checked,
    });
    if (!r.ok) { $('setErr').textContent = '⚠ ' + (r.error || 'Save failed'); return; }
    if (!r.configured) { $('setErr').textContent = '⚠ Need API key + at least one model'; return; }
    configured = true;
    $('settingsModal').classList.add('hidden');
    $('btnSend').disabled = false;
    $('statusText').textContent = 'Ready';
  }

  async function checkStatus() {
    apiBase = await window.fusionDesktop.getBackendUrl();
    const st = await api('GET', '/api/status');
    configured = st.configured;
    if ($('optEnsemble')) $('optEnsemble').checked = (st.fusion_mode || 'ensemble') === 'ensemble';
    refreshChats();
    renderTree();
    showMessagesEmpty();
    if (!configured) {
      $('btnSend').disabled = true;
      $('statusText').textContent = 'Setup required';
      openSettings();
    }
  }

  /* ── init ── */
  async function boot() {
    initSash($('sashExplorer'), $('panelExplorer'), false);
    initSash($('sashEditor'), $('panelEditor'), true);
    loadLayout();

    $('btnOpenFolder').onclick = openFolder;
    $('btnRefreshTree').onclick = async () => {
      if (!projectRoot) return;
      const r = await api('POST', '/api/list_files', { path: projectRoot });
      if (r.files) { fileList = r.files; fileMap = {}; fileList.forEach((f) => { fileMap[f.path] = f; }); renderTree(); }
    };
    $('btnNewChat').onclick = newChat;
    $('btnHistory').onclick = () => $('historyDropdown').classList.toggle('hidden');
    $('btnSend').onclick = ask;
    $('composer').addEventListener('input', updateCtxBar);
    $('composer').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); }
    });
    $('btnSettings').onclick = openSettings;
    $('abSettings').onclick = openSettings;
    $('menuSettings').onclick = openSettings;
    $('setCancel').onclick = () => { if (configured) $('settingsModal').classList.add('hidden'); };
    $('setTest').onclick = testModels;
    $('setSave').onclick = saveSettings;
    $('addProv').onclick = () => makeProvRow();
    document.querySelectorAll('[data-action="open-folder"]').forEach((b) => { b.onclick = openFolder; });
    document.querySelectorAll('[data-action="new-chat"]').forEach((b) => { b.onclick = newChat; });

    await initMonaco();
    await checkStatus();
    $('composer').focus();
  }

  boot();
})();
