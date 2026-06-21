"""Desktop UI — Cursor clone: Explorer (left) | Chat (center) | Editor (right)."""

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fusion Fable</title>
<style>
  :root {
    color-scheme: dark;
    --bg:#1e1e1e; --bg-sidebar:#181818; --bg-panel:#252526; --bg-input:#2b2b2b;
    --bg-hover:#2a2d2e; --bg-active:#37373d; --row-selected:rgba(255,255,255,.06);
    --border:#2b2b2b; --border-strong:#3c3c3c;
    --text:#e4e4e4; --text-muted:#9d9d9d; --text-subtle:#6e6e6e;
    --accent:#0078d4; --accent-hover:#1a86d9; --accent-soft:rgba(0,120,212,.15);
    --success:#3fb950; --warning:#cca700; --danger:#f14c4c;
    --font-ui:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
    --font-mono:Consolas,"Courier New",monospace;
    --ed-line:19px;
    --titlebar:35px; --explorer-w:260px; --editor-w:480px;
  }
  * { box-sizing:border-box; scrollbar-width:thin; scrollbar-color:#424242 transparent; }
  ::-webkit-scrollbar { width:8px; height:8px; }
  ::-webkit-scrollbar-thumb { background:#424242; border-radius:4px; }
  ::-webkit-scrollbar-thumb:hover { background:#4f4f4f; }
  ::selection { background:rgba(0,120,212,.35); }
  html,body { margin:0; width:100%; height:100%; overflow:hidden; }
  body { background:var(--bg); color:var(--text); font-family:var(--font-ui); font-size:13px; }
  button,input,textarea,select { font:inherit; }
  :focus-visible { outline:1px solid var(--accent); outline-offset:-1px; }
  .hidden { display:none !important; }

  .workbench { display:flex; flex-direction:column; height:100vh; }

  /* titlebar */
  .titlebar { display:flex; align-items:center; height:var(--titlebar); padding:0 10px;
              background:var(--bg-sidebar); border-bottom:1px solid var(--border); flex-shrink:0; gap:10px; }
  .titlebar .brand { font-size:12px; font-weight:500; color:var(--text-muted); }
  .titlebar .proj { flex:1; text-align:center; font-size:12px; color:var(--text-subtle);
                     overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .titlebar .status { font-size:11px; color:var(--text-subtle); }
  .icon-btn { width:28px; height:28px; border:0; border-radius:4px; background:transparent;
              color:var(--text-muted); cursor:pointer; font-size:15px; }
  .icon-btn:hover { background:var(--bg-hover); color:var(--text); }

  /* 3-column resizable layout */
  .main-row { flex:1; display:flex; min-height:0; overflow:hidden; }

  .panel { display:flex; flex-direction:column; min-height:0; overflow:hidden; background:var(--bg); }
  .panel.explorer { width:var(--explorer-w); min-width:140px; max-width:520px; flex-shrink:0;
                    background:var(--bg-sidebar); border-right:1px solid var(--border); }
  .panel.chat { flex:1; min-width:240px; background:var(--bg); }
  .panel.editor { width:var(--editor-w); min-width:180px; max-width:75vw; flex-shrink:0;
                  background:var(--bg); border-left:1px solid var(--border); }
  .panel.editor.closed { width:0 !important; min-width:0 !important; border:none; overflow:hidden; }

  .sash { width:4px; flex-shrink:0; cursor:col-resize; background:transparent; transition:background .15s; z-index:5; }
  .sash:hover, .sash.dragging { background:var(--accent); }
  .sash.closed { width:0; pointer-events:none; }

  /* explorer */
  .ex-head { display:flex; align-items:center; justify-content:space-between; height:35px;
             padding:0 10px; font-size:11px; font-weight:600; letter-spacing:.04em;
             text-transform:uppercase; color:var(--text-subtle); flex-shrink:0; }
  .ex-actions { display:flex; gap:2px; }
  .ex-actions button { width:24px; height:24px; border:0; border-radius:4px; background:transparent;
                       color:var(--text-subtle); cursor:pointer; font-size:14px; }
  .ex-actions button:hover { background:var(--bg-hover); color:var(--text); }
  .folder-path { padding:4px 10px 6px; font-size:11px; color:var(--text-subtle);
                 overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border-bottom:1px solid var(--border); }
  .file-list { flex:1; overflow:auto; padding:4px 0; }

  .trow { display:flex; align-items:center; gap:4px; height:22px; padding:0 8px;
          color:var(--text-muted); font-size:12px; cursor:pointer; white-space:nowrap; user-select:none; }
  .trow:hover { background:var(--bg-hover); color:var(--text); }
  .trow .chev { width:12px; font-size:9px; color:var(--text-subtle); flex-shrink:0; }
  .trow .ic { width:16px; text-align:center; flex-shrink:0; font-size:11px; opacity:.8; }
  .trow .nm { overflow:hidden; text-overflow:ellipsis; }
  .trow.open { background:var(--row-selected); color:var(--text); }
  .trow .fdot { margin-left:auto; width:6px; height:6px; border-radius:50%; background:var(--warning); opacity:0; }
  .trow.dirty .fdot { opacity:1; }

  /* chat — full center like Cursor Agent */
  .chat-toolbar { display:flex; align-items:center; justify-content:space-between; height:35px;
                  padding:0 16px; border-bottom:1px solid var(--border); flex-shrink:0; background:var(--bg); }
  .chat-toolbar .left { display:flex; align-items:center; gap:8px; }
  .chat-toolbar h1 { margin:0; font-size:13px; font-weight:500; color:var(--text); }
  .chat-toolbar .actions { display:flex; gap:4px; }
  .chat-toolbar .actions button { height:26px; padding:0 10px; border:1px solid var(--border-strong);
    border-radius:6px; background:transparent; color:var(--text-muted); font-size:12px; cursor:pointer; }
  .chat-toolbar .actions button:hover { background:var(--bg-hover); color:var(--text); }
  .chat-dropdown { max-height:140px; overflow:auto; border-bottom:1px solid var(--border); background:var(--bg-panel); }
  .chat-list { padding:4px; }
  .chat-row { display:grid; grid-template-columns:1fr 22px; align-items:center; height:28px;
              padding:0 8px; border-radius:4px; color:var(--text-muted); font-size:12px; cursor:pointer; }
  .chat-row:hover { background:var(--bg-hover); color:var(--text); }
  .chat-row.active { background:var(--accent-soft); color:var(--text); }
  .chat-row span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .chat-row .del { border:0; background:none; color:inherit; opacity:.4; cursor:pointer; font-size:14px; }
  .chat-row .del:hover { opacity:1; }

  .messages-wrap { flex:1; overflow:auto; min-height:0; }
  .messages { max-width:780px; margin:0 auto; padding:24px 20px 32px; }
  .msg { margin-bottom:28px; }
  .msg.user .label { font-size:11px; font-weight:600; color:var(--text-subtle); margin-bottom:6px; }
  .msg.user .body { color:var(--text); line-height:1.65; font-size:14px; white-space:pre-wrap; }
  .msg.bot .label { font-size:11px; font-weight:600; color:var(--text-subtle); margin-bottom:6px; }
  .msg.bot .body { color:var(--text); line-height:1.65; font-size:14px; }
  .msg.bot .body { white-space:pre-wrap; }
  .progress-line .body { color:var(--text-muted); font-style:italic; }
  .progress-line.active .body { color:var(--accent); }
  .bubble.err .body { color:var(--danger); }
  .typing-caret::after { content:"▋"; animation:blink .8s step-end infinite; color:var(--accent); margin-left:2px; }
  @keyframes blink { 50% { opacity:0; } }
  .body h1,.body h2,.body h3 { margin:.6em 0 .35em; font-weight:600; }
  .body code.inline { background:var(--bg-panel); padding:2px 5px; border-radius:4px; font-family:var(--font-mono); font-size:12px; }
  .body a { color:#4daafc; }
  .code { margin:14px 0; border:1px solid var(--border-strong); border-radius:8px; overflow:hidden; background:#141414; }
  .codebar { display:flex; justify-content:space-between; align-items:center; height:32px; padding:0 12px;
             background:#1a1a1a; border-bottom:1px solid var(--border); font-family:var(--font-mono); font-size:11px; color:var(--text-subtle); }
  .codebar button { border:0; background:transparent; color:var(--text-subtle); cursor:pointer; font-size:11px; padding:4px 8px; border-radius:4px; }
  .codebar button:hover { background:var(--bg-hover); color:var(--text); }
  .code pre { margin:0; padding:14px; overflow:auto; font-family:var(--font-mono); font-size:12px; line-height:1.55; color:#d4d4d4; }

  .empty-state { padding:20px 16px; color:var(--text-subtle); font-size:13px; line-height:1.6; }
  .empty-state b { display:block; color:var(--text); font-weight:500; margin-bottom:8px; font-size:14px; }
  .welcome-cta { text-align:center; padding:60px 24px; }
  .welcome-cta b { font-size:18px; font-weight:500; color:var(--text); display:block; margin-bottom:10px; }
  .welcome-cta p { color:var(--text-muted); margin:0 0 24px; font-size:14px; }
  .welcome-cta button { height:34px; padding:0 18px; border:0; border-radius:6px; background:var(--accent);
    color:#fff; font-weight:500; cursor:pointer; font-size:13px; }
  .welcome-cta button:hover { background:var(--accent-hover); }
  .hint-list { list-style:none; padding:0; margin:24px auto 0; max-width:320px; text-align:left; font-size:13px; color:var(--text-subtle); line-height:2; }
  .hint-list li::before { content:"· "; color:var(--accent); }

  /* composer — Cursor style */
  .composer-wrap { flex-shrink:0; padding:0 16px 16px; background:var(--bg); }
  .composer-box { max-width:780px; margin:0 auto; border:1px solid var(--border-strong); border-radius:12px;
                   background:var(--bg-input); overflow:hidden; }
  .composer-box:focus-within { border-color:#555; box-shadow:0 0 0 1px rgba(255,255,255,.06); }
  .ctx-bar { display:flex; flex-wrap:wrap; gap:4px; padding:8px 12px 0; }
  .ctx-bar.hidden { display:none; }
  .ctx-chip { height:22px; padding:0 8px; border-radius:4px; font-size:11px; display:inline-flex; align-items:center;
              background:var(--accent-soft); color:#9cdcfe; border:1px solid rgba(0,120,212,.25); }
  .ctx-chip.muted { background:var(--bg-panel); color:var(--text-subtle); border-color:var(--border); }
  #composer { display:block; width:100%; min-height:52px; max-height:200px; padding:12px 14px 8px;
              border:0; outline:0; resize:none; background:transparent; color:var(--text); font-size:14px; line-height:1.5; }
  #composer::placeholder { color:var(--text-subtle); }
  .composer-foot { display:flex; align-items:center; justify-content:space-between; padding:4px 10px 10px; }
  .composer-foot .hint { font-size:11px; color:var(--text-subtle); }
  .composer-foot .right { display:flex; align-items:center; gap:8px; }
  .agent-badge { height:24px; padding:0 10px; border-radius:6px; border:1px solid var(--border-strong);
                 background:var(--bg-panel); color:var(--text-muted); font-size:11px; display:inline-flex; align-items:center; gap:4px; }
  #sendBtn { height:28px; padding:0 14px; border:0; border-radius:6px; background:var(--text); color:var(--bg);
             font-size:12px; font-weight:600; cursor:pointer; }
  #sendBtn:hover { background:#fff; }
  #sendBtn:disabled { background:var(--bg-active); color:var(--text-subtle); cursor:not-allowed; }

  /* editor — right panel */
  .tab-bar { display:flex; align-items:stretch; height:35px; background:var(--bg-sidebar);
             border-bottom:1px solid var(--border); flex-shrink:0; overflow-x:auto; }
  .tab { display:flex; align-items:center; gap:6px; height:35px; padding:0 12px; font-size:12px;
         color:var(--text-muted); border-right:1px solid var(--border); cursor:default; white-space:nowrap; background:var(--bg); }
  .tab.active { color:var(--text); border-top:2px solid var(--accent); }
  .tab .dot { color:var(--warning); font-size:10px; }
  .tab .close { margin-left:4px; border:0; background:none; color:var(--text-subtle); cursor:pointer;
                font-size:14px; line-height:1; padding:0 2px; border-radius:3px; }
  .tab .close:hover { background:var(--bg-hover); color:var(--text); }

  .editor-body-wrap { flex:1; display:flex; flex-direction:column; min-height:0; overflow:hidden; position:relative; }
  .ed-wrap { display:grid; grid-template-columns:48px minmax(0,1fr); flex:1; min-height:0; }
  .ed-gutter { overflow:hidden; padding:8px 6px 8px 0; text-align:right; color:#5a5a5a; background:var(--bg);
               font-family:var(--font-mono); font-size:12px; line-height:var(--ed-line); white-space:pre;
               user-select:none; border-right:1px solid var(--border); }
  .ed-scroll { position:relative; min-width:0; min-height:0; flex:1; }
  #edHighlight, #edArea { position:absolute; inset:0; margin:0; padding:8px 12px; border:0;
        font-family:var(--font-mono); font-size:12.5px; line-height:var(--ed-line); tab-size:2;
        white-space:pre; overflow:auto; }
  #edHighlight { z-index:1; color:#d4d4d4; pointer-events:none; overflow:hidden; }
  #edArea { z-index:2; background:transparent; color:transparent; caret-color:#fff; resize:none; outline:0; }
  .t-comment{color:#6a9955;font-style:italic}.t-string{color:#ce9178}.t-number{color:#b5cea8}
  .t-keyword{color:#569cd6}.t-func{color:#dcdcaa}.t-tag{color:#569cd6}.t-attr{color:#9cdcfe}
  .ed-image { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; padding:16px; overflow:auto; }
  .ed-image img { max-width:100%; max-height:100%; border-radius:4px; }
  .editor-status { display:flex; justify-content:space-between; height:22px; padding:0 10px; font-size:11px;
                   background:var(--accent); color:#fff; flex-shrink:0; }
  #edToast { opacity:0; transition:opacity .2s; color:#b5ffb5; } #edToast.show { opacity:1; }
  .runbar { display:none; }

  /* settings modal */
  .modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.6); display:flex; align-items:center;
                    justify-content:center; z-index:100; }
  .modal-backdrop.hidden { display:none; }
  .modal { width:min(540px,calc(100vw - 32px)); max-height:90vh; overflow:auto; background:var(--bg-panel);
           border:1px solid var(--border-strong); border-radius:8px; padding:20px; }
  .modal h2 { margin:0 0 16px; font-size:16px; font-weight:500; }
  .modal label { display:block; font-size:12px; color:var(--text-muted); margin:12px 0 4px; }
  .modal label.ck { display:flex; gap:6px; align-items:center; color:var(--text); }
  .modal input[type=text],.modal input[type=password],.modal select {
    width:100%; height:32px; padding:0 10px; border:1px solid var(--border-strong); border-radius:6px;
    background:var(--bg-input); color:var(--text); }
  .modal-btns { display:flex; gap:8px; justify-content:flex-end; margin-top:20px; }
  .modal-btns button { height:32px; padding:0 16px; border-radius:6px; border:1px solid var(--border-strong);
    background:var(--bg-input); color:var(--text); cursor:pointer; }
  .modal-btns button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  #setErr { color:var(--danger); font-size:12px; margin-top:10px; }
  .set-section-title { font-size:11px; color:var(--text-subtle); text-transform:uppercase; letter-spacing:.05em; margin-bottom:8px; }
  .prov { border:1px solid var(--border); border-radius:6px; padding:8px; margin-bottom:8px; }
  .prov .line { display:grid; grid-template-columns:120px 1fr 26px; gap:6px; }
  .prov select,.prov input { height:30px; border:1px solid var(--border); border-radius:4px; background:var(--bg-input); color:var(--text); padding:0 8px; width:100%; }
  .prov .p-models,.prov .p-base { margin-top:6px; }
  .prov .p-del { height:26px; width:26px; border:1px solid var(--border); border-radius:4px; background:transparent; cursor:pointer; color:var(--text-subtle); }
  .add-prov { width:100%; height:30px; border:1px dashed var(--border-strong); border-radius:6px; background:transparent; color:var(--text-muted); cursor:pointer; margin-bottom:8px; }
</style>
</head>
<body>
<div class="workbench" id="appShell">
  <header class="titlebar">
    <span class="brand">Fusion Fable</span>
    <span class="proj" id="projName">เปิดโปรเจกตเพื่อเริ่ม</span>
    <span class="status" id="statusText">Ready</span>
    <button class="icon-btn" id="settingsBtn" title="Settings">⚙</button>
  </header>

  <div class="main-row" id="mainRow">
    <aside class="panel explorer" id="panelExplorer">
      <div class="ex-head">
        <span>Explorer</span>
        <div class="ex-actions">
          <button id="openFolder" title="เปิดโปรเจกต">📂</button>
          <span class="file-count" id="fileCount" style="font-size:11px;color:var(--text-subtle)"></span>
        </div>
      </div>
      <div class="folder-path" id="folderPath">ยังไม่ได้เปิดโปรเจกต</div>
      <div class="file-list" id="fileList"></div>
    </aside>

    <div class="sash" id="sashExplorer" title="ลากปรับขนาด"></div>

    <main class="panel chat" id="panelChat">
      <div class="chat-toolbar">
        <div class="left"><h1 id="chatTitle">New Chat</h1></div>
        <div class="actions">
          <button id="toggleChats" type="button">ประวัติ</button>
          <button id="newChat" type="button">+ New</button>
        </div>
      </div>
      <div class="chat-dropdown hidden" id="chatDropdown"><div class="chat-list" id="chatList"></div></div>
      <section class="runbar hidden">
        <input type="checkbox" id="optCompress"><input type="checkbox" id="optEnsemble"><input type="checkbox" id="optCache">
        <input type="text" id="optModels">
      </section>
      <div class="messages-wrap"><section class="messages" id="messages"></section></div>
      <footer class="composer-wrap">
        <div class="composer-box">
          <div class="ctx-bar hidden" id="ctxBar"></div>
          <textarea id="composer" placeholder="Plan, @ for context…" rows="2"></textarea>
          <div class="composer-foot">
            <span class="hint">Enter ส่ง · Shift+Enter บรรทัดใหม่</span>
            <div class="right">
              <span class="agent-badge">∞ Agent</span>
              <button id="sendBtn" type="button">↑</button>
            </div>
          </div>
        </div>
      </footer>
    </main>

    <div class="sash closed" id="sashEditor" title="ลากปรับขนาด"></div>

    <section class="panel editor closed" id="panelEditor">
      <div class="tab-bar" id="tabBar"></div>
      <div class="editor-body-wrap">
        <div class="ed-wrap hidden" id="edWrap">
          <div class="ed-gutter" id="edGutter"></div>
          <div class="ed-scroll">
            <pre class="ed-highlight" id="edHighlight"><code id="edCode"></code></pre>
            <textarea id="edArea" spellcheck="false" wrap="off"></textarea>
          </div>
        </div>
        <div class="ed-image hidden" id="edImage"><img id="edImg" alt=""></div>
      </div>
      <div class="editor-status"><span id="edInfo"></span><span id="edToast">Saved</span></div>
      <span class="hidden"><span id="edPath"></span><span id="edReadonly"></span><button id="edSave"></button><button id="edClose"></button></span>
    </section>
  </div>
</div>

<div class="modal-backdrop hidden" id="settingsModal">
  <div class="modal">
    <h2>Settings</h2>
    <div class="set-section-title">Providers &amp; API keys</div>
    <div id="provList"></div>
    <button id="addProv" class="add-prov">+ Add provider</button>
    <label for="setJudge">Judge / synthesizer model</label>
    <input id="setJudge" type="text" placeholder="blank = first model">
    <label class="ck"><input type="checkbox" id="setCompress"> Compress prompts</label>
    <div class="modal-btns"><button id="setCancel">Cancel</button><button id="setSave" class="primary">Save</button></div>
    <div id="setErr"></div>
  </div>
</div>

<script>
window.addEventListener('error', e=>{ try{ document.title='JS: '+e.message; }catch(_){} });
const $ = id => document.getElementById(id);
const messages=$('messages'), composer=$('composer'), sendBtn=$('sendBtn'), chatList=$('chatList'), statusText=$('statusText');
let currentConvId=null, busy=false, configured=false;
let projectRoot=null, fileList=[], fileMap={};

function esc(s){ const d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }
function escCode(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function api(){ return (window.pywebview && window.pywebview.api) || null; }

/* ── resizable panels ── */
function initSash(sashEl, onDrag){
  if(!sashEl) return;
  sashEl.addEventListener('mousedown', e=>{
    e.preventDefault();
    sashEl.classList.add('dragging');
    document.body.style.cursor='col-resize';
    document.body.style.userSelect='none';
    const move=ev=> onDrag(ev.clientX - e.clientX);
    const up=()=>{
      sashEl.classList.remove('dragging');
      document.body.style.cursor='';
      document.body.style.userSelect='';
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', up);
      try{ localStorage.setItem('ff-layout', JSON.stringify({
        explorer: $('panelExplorer').offsetWidth,
        editor: $('panelEditor').classList.contains('closed') ? 0 : $('panelEditor').offsetWidth
      })); }catch(_){}
    };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
  });
}
function applyLayout(){
  try{
    const s=JSON.parse(localStorage.getItem('ff-layout')||'{}');
    if(s.explorer) $('panelExplorer').style.width=Math.max(140,Math.min(520,s.explorer))+'px';
    if(s.editor && s.editor>0 && !$('panelEditor').classList.contains('closed'))
      $('panelEditor').style.width=Math.max(180,Math.min(window.innerWidth*.75,s.editor))+'px';
  }catch(_){}
}
initSash($('sashExplorer'), dx=>{
  const p=$('panelExplorer');
  p.style.width=Math.max(140,Math.min(520,p.offsetWidth+dx))+'px';
});
initSash($('sashEditor'), dx=>{
  const p=$('panelEditor');
  p.style.width=Math.max(180,Math.min(window.innerWidth*.75,p.offsetWidth-dx))+'px';
});
applyLayout();

function showEditorPanel(){
  $('panelEditor').classList.remove('closed');
  $('sashEditor').classList.remove('closed');
  applyLayout();
}
function hideEditorPanel(){
  $('panelEditor').classList.add('closed');
  $('sashEditor').classList.add('closed');
}

/* ── markdown ── */
function copyCode(btn){ let t; try{ t=decodeURIComponent(btn.dataset.c); }catch(e){ return; }
  const done=()=>{ btn.textContent='Copied'; setTimeout(()=>btn.textContent='Copy',1200); };
  if(navigator.clipboard&&navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(done,()=>fb(t,done));
  else fb(t,done); }
function fb(t,done){ const ta=document.createElement('textarea'); ta.value=t; document.body.appendChild(ta); ta.select();
  try{document.execCommand('copy');}catch(e){} ta.remove(); done(); }
window.copyCode=copyCode;
function mdToHtml(src){ const blocks=[];
  src=src.replace(/```(\w*)\n?([\s\S]*?)```/g,(m,lang,code)=>{ blocks.push({lang,code}); return '@@B'+(blocks.length-1)+'@@'; });
  let h=esc(src);
  h=h.replace(/^### (.*)$/gm,'<h3>$1</h3>').replace(/^## (.*)$/gm,'<h2>$1</h2>').replace(/^# (.*)$/gm,'<h1>$1</h1>');
  h=h.replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>').replace(/`([^`]+)`/g,'<code class="inline">$1</code>');
  h=h.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  h=h.replace(/\n/g,'<br>');
  h=h.replace(/@@B(\d+)@@/g,(m,i)=>{ const b=blocks[i]; if(!b)return m;
    return '<div class="code"><div class="codebar"><span>'+esc(b.lang||'code')+'</span><button onclick="copyCode(this)" data-c="'+encodeURIComponent(b.code)+'">Copy</button></div><pre><code>'+escCode(b.code)+'</code></pre></div>'; });
  return h; }

/* ── chat ── */
function showMessagesEmpty(){
  if(projectRoot){
    messages.innerHTML='<div class="empty-state"><b>พร้อมแล้ว</b>พิมพ์สั่งงาน — AI จะอ่านโปรเจกตและแก้ไฟล์ให้อัตโนมัติ<ul class="hint-list"><li>แก้บั๊กใน main.py</li><li>เพิ่มฟังก์ชัน login</li><li>@ชื่อไฟล์ อ้างอิงไฟล์</li></ul></div>';
  } else {
    messages.innerHTML='<div class="welcome-cta"><b>Fusion Fable</b><p>เปิดโฟลเดอร์โปรเจกต แล้วสั่ง AI แก้ไฟล์ได้เหมือน Cursor</p><button type="button" id="welcomeOpen">เปิดโปรเจกต</button><ul class="hint-list"><li>แชทเต็มจอ — คลิกไฟล์ซ้ายเพื่อเปิด editor ขวา</li><li>ลากขอบ panel ปรับขนาดได้</li></ul></div>';
    const btn=$('welcomeOpen'); if(btn) btn.onclick=openFolder;
  }
  updateCtxBar();
}
function clearEmpty(){ messages.querySelectorAll('.empty-state,.welcome-cta').forEach(e=>e.remove()); }
function addMsg(role, cls){
  clearEmpty();
  const row=document.createElement('div');
  row.className='msg '+(role==='user'?'user':'bot');
  const label=document.createElement('div'); label.className='label'; label.textContent=role==='user'?'You':'Agent';
  const body=document.createElement('div'); body.className='body';
  if(cls) row.classList.add(cls.split(' ')[0]);
  row.appendChild(label); row.appendChild(body);
  messages.appendChild(row);
  $('messages').parentElement.scrollTop=99999;
  return body;
}
function addUser(t){ const b=addMsg('user'); b.textContent=t; return b; }

function parseMentions(text){
  const out=[]; if(!text) return out;
  for(const m of text.matchAll(/@([^\s@]+)/g)){
    const q=m[1].toLowerCase();
    const hit=fileList.find(f=>!f.binary&&(f.path.toLowerCase()===q||f.path.toLowerCase().endsWith('/'+q)||f.path.split('/').pop().toLowerCase()===q));
    if(hit) out.push(hit.path);
  }
  return [...new Set(out)];
}
function editorOverrides(){
  const o={};
  if(editor.path&&!editor.image&&editor.dirty) o[editor.path]=edArea.value;
  return o;
}
function updateCtxBar(){
  const bar=$('ctxBar'); if(!bar) return;
  if(!projectRoot){ bar.classList.add('hidden'); bar.innerHTML=''; return; }
  bar.classList.remove('hidden');
  const chips=['<span class="ctx-chip">📁 '+fileList.filter(f=>!f.binary).length+' files</span>'];
  if(editor.path&&!editor.image) chips.push('<span class="ctx-chip">'+esc(editor.path)+'</span>');
  parseMentions(composer.value).forEach(p=>chips.push('<span class="ctx-chip muted">@'+esc(p)+'</span>'));
  bar.innerHTML=chips.join('');
}
function typeInto(body, text, done){
  body.classList.add('typing-caret'); let i=0;
  const step=Math.max(2,Math.round(text.length/120));
  const t=setInterval(()=>{
    i+=step; body.textContent=text.slice(0,i);
    messages.parentElement.scrollTop=99999;
    if(i>=text.length){ clearInterval(t); body.classList.remove('typing-caret'); body.innerHTML=mdToHtml(text); done&&done(); }
  },10);
}
window.ffProgress=function(ev){
  if(window.__prog&&ev.stage!=='done') window.__prog.textContent='กำลังคิด…';
  statusText.textContent=ev.stage==='done'?'Ready':'Thinking';
};
async function afterEdits(r){
  if(!r.edits||!r.edits.length||!projectRoot) return;
  const ok=r.edits.filter(e=>e.ok).map(e=>e.path);
  if(!ok.length) return;
  try{ const lr=await api().list_files(projectRoot); if(lr.files){ fileList=lr.files; fileMap={}; fileList.forEach(f=>fileMap[f.path]=f); renderTree(); } }catch(e){}
  if(editor.path&&ok.includes(editor.path)) await openText(editor.path);
  else if(ok.length) await openText(ok[0]);
}
async function ask(){
  const text=composer.value.trim(); if(!text||busy||!api()) return;
  if(!projectRoot){
    addUser(text); composer.value='';
    addMsg('bot').textContent='เปิดโปรเจกตก่อน — กด 📂 ใน Explorer ด้านซ้าย';
    openFolder(); return;
  }
  busy=true; sendBtn.disabled=true; statusText.textContent='Thinking';
  addUser(text); composer.value=''; updateCtxBar();
  const progBody=addMsg('bot','progress-line active'); progBody.textContent='กำลังคิด…'; window.__prog=progBody;
  const payload={ question:text, conversation_id:currentConvId, project_root:projectRoot };
  try{
    const cx=await api().read_context({ root:projectRoot, all_paths:fileList.filter(f=>!f.binary).map(f=>f.path),
      open_path:(editor.path&&!editor.image)?editor.path:'', mentioned:parseMentions(text), overrides:editorOverrides() });
    if(cx&&cx.context) payload.context=cx.context;
  }catch(e){}
  let r; try{ r=await api().ask(payload); }catch(e){ r={error:String(e)}; }
  window.__prog=null; progBody.parentElement.remove();
  statusText.textContent='Ready'; sendBtn.disabled=false;
  if(!r||r.error){ addMsg('bot','bubble err').textContent='⚠ '+(r&&r.error||'Request failed'); busy=false; return; }
  currentConvId=r.conversation_id;
  typeInto(addMsg('bot'), r.answer, ()=>{ afterEdits(r).then(()=>{ refreshChats(); busy=false; composer.focus(); updateCtxBar(); }); });
}
async function refreshChats(){
  if(!api()) return;
  let list=[]; try{ list=await api().list_conversations(); }catch(e){ return; }
  chatList.innerHTML='';
  if(!list.length){ chatList.innerHTML='<div class="empty-state">ยังไม่มีแชท</div>'; return; }
  list.forEach(c=>{
    const it=document.createElement('div'); it.className='chat-row'+(c.id===currentConvId?' active':'');
    it.innerHTML='<span></span><button class="del">×</button>';
    it.querySelector('span').textContent=c.title;
    it.querySelector('span').onclick=()=>loadConv(c.id);
    it.querySelector('.del').onclick=async e=>{ e.stopPropagation(); await api().delete_conversation(c.id);
      if(currentConvId===c.id) newChat(); else refreshChats(); };
    chatList.appendChild(it);
  });
}
async function loadConv(id){
  if(!api()) return;
  let c; try{ c=await api().load_conversation(id); }catch(e){ return; }
  currentConvId=id; messages.innerHTML='';
  if(!c||!c.messages.length) showMessagesEmpty();
  else c.messages.forEach(m=>{
    if(m.role==='user') addUser(m.content);
    else { const b=addMsg('bot'); b.innerHTML=mdToHtml(m.content); }
  });
  $('chatTitle').textContent=c&&c.title||'Chat';
  refreshChats();
}
function newChat(){ currentConvId=null; $('chatTitle').textContent='New Chat'; showMessagesEmpty(); refreshChats(); composer.focus(); }
function toggleChatDropdown(){ $('chatDropdown').classList.toggle('hidden'); }

/* ── file tree ── */
const expanded=new Set();
function buildTree(files){
  const root={dirs:{},files:[]};
  files.forEach(f=>{ const parts=f.path.split('/'); let node=root;
    for(let i=0;i<parts.length-1;i++){ const d=parts[i], p=parts.slice(0,i+1).join('/');
      node.dirs[d]=node.dirs[d]||{dirs:{},files:[],path:p}; node=node.dirs[d]; }
    node.files.push(f); });
  return root;
}
function renderNode(node, depth, out){
  Object.keys(node.dirs).sort().forEach(name=>{
    const dir=node.dirs[name], isOpen=expanded.has(dir.path);
    const row=document.createElement('div'); row.className='trow dir';
    row.style.paddingLeft=(depth*10+8)+'px';
    row.innerHTML='<span class="chev">'+(isOpen?'▾':'▸')+'</span><span class="ic">'+(isOpen?'📂':'📁')+'</span><span class="nm">'+esc(name)+'</span>';
    row.onclick=()=>{ isOpen?expanded.delete(dir.path):expanded.add(dir.path); renderTree(); };
    out.appendChild(row);
    if(isOpen) renderNode(dir, depth+1, out);
  });
  node.files.slice().sort((a,b)=>a.path.localeCompare(b.path)).forEach(f=>{
    const name=f.path.split('/').pop();
    const row=document.createElement('div'); row.dataset.path=f.path;
    row.className='trow file'+(editor.path===f.path?' open':'')+(editor.path===f.path&&editor.dirty?' dirty':'');
    row.style.paddingLeft=(depth*10+20)+'px';
    row.innerHTML='<span class="ic">'+(f.image?'🖼':(f.binary?'▫':'📄'))+'</span><span class="nm">'+esc(name)+'</span><span class="fdot"></span>';
    row.onclick=()=>openFile(f.path);
    out.appendChild(row);
  });
}
function renderTree(){
  const el=$('fileList'); el.innerHTML='';
  if(!projectRoot){ el.innerHTML='<div class="empty-state"><b>เปิดโฟลเดอร์</b>คลิกไฟล์ 1 ครั้ง → เปิด editor ขวา</div>'; updateFileCount(); return; }
  if(!fileList.length){ el.innerHTML='<div class="empty-state">ไม่พบไฟล์</div>'; updateFileCount(); return; }
  renderNode(buildTree(fileList), 0, el); updateFileCount();
}
function updateFileCount(){
  $('fileCount').textContent=projectRoot?fileList.filter(f=>!f.binary).length+'':'';
  updateCtxBar();
}
async function openFolder(){
  if(editor.dirty&&!confirm('มีการแก้ไขที่ยังไม่ได้บันทึก เปิดโฟลเดอร์ใหม่?')) return;
  if(!api()) return;
  statusText.textContent='Opening…';
  let r; try{ r=await api().pick_folder(); }catch(e){ statusText.textContent='Error'; return; }
  if(!r||r.error||!r.path){ statusText.textContent='Ready'; return; }
  closeEditor(true); newChat();
  projectRoot=r.path; fileList=r.files||[]; fileMap={}; fileList.forEach(f=>fileMap[f.path]=f); expanded.clear();
  const fname=r.path.split(/[\\/]/).filter(Boolean).pop()||r.path;
  $('folderPath').textContent=fname; $('projName').textContent=fname;
  document.title=fname+' — Fusion Fable';
  renderTree(); showMessagesEmpty(); statusText.textContent='Ready';
}

/* ── editor (right panel) ── */
const edArea=$('edArea'), edCode=$('edCode'), edHi=$('edHighlight'), edGutter=$('edGutter'),
      edImage=$('edImage'), edImg=$('edImg'), edWrap=$('edWrap'),
      edPath=$('edPath'), edSave=$('edSave'), edInfo=$('edInfo'), edToast=$('edToast');
const editor={ path:null, original:'', dirty:false, readonly:false, image:false, lang:'' };
const KW={ py:'def class return if elif else for while import from as try except finally with lambda yield async await pass break continue in is not and or None True False',
  js:'function return if else for while var let const new class extends import export from default try catch finally throw typeof await async null true false undefined',
  json:'true false null', html:'', sh:'if then else fi for while export local return', md:'', _:'' };
function langOf(p){ const e=(p.split('.').pop()||'').toLowerCase();
  if(e==='py')return'py'; if(['js','jsx','ts','tsx'].includes(e))return'js'; if(e==='json')return'json';
  if(['html','htm','xml'].includes(e))return'html'; if(['yml','yaml','toml','sh'].includes(e))return'sh'; if(e==='md')return'md'; return'_'; }
function buildHL(lang){
  const parts=[['comment','(?://|#).*'],['comment','/\\*[\\s\\S]*?\\*/'],
    ['string','"(?:\\\\.|[^"\\\\])*"'],['string',"'(?:\\\\.|[^'\\\\])*'"],['number','\\b\\d+\\b']];
  const kw=(KW[lang]||'').trim(); if(kw) parts.push(['keyword','\\b(?:'+kw.split(/\s+/).join('|')+')\\b']);
  parts.push(['func','\\b[A-Za-z_]\\w*(?=\\s*\\()']);
  return { re:new RegExp(parts.map(p=>'('+p[1]+')').join('|'),'g'), classes:parts.map(p=>p[0]) };
}
let HLDEF=buildHL('_');
function highlight(code){ const def=HLDEF; def.re.lastIndex=0; let out='',last=0,m;
  while((m=def.re.exec(code))){ out+=escCode(code.slice(last,m.index)); let cls='plain';
    for(let g=1;g<m.length;g++) if(m[g]!==undefined){ cls=def.classes[g-1]; break; }
    out+='<span class="t-'+cls+'">'+escCode(m[0])+'</span>'; last=m.index+m[0].length; }
  return out+escCode(code.slice(last)); }
let paintTimer=null;
function paint(){
  edCode.innerHTML=highlight(edArea.value);
  const n=edArea.value.split('\n').length;
  edGutter.textContent=Array.from({length:n},(_,i)=>i+1).join('\n');
  syncScroll();
  edInfo.textContent=editor.path?(n+' ln · '+(editor.lang==='_'?'text':editor.lang)):'';
}
function schedulePaint(){ if(paintTimer) cancelAnimationFrame(paintTimer); paintTimer=requestAnimationFrame(paint); }
function syncScroll(){ edHi.scrollTop=edArea.scrollTop; edHi.scrollLeft=edArea.scrollLeft; edGutter.scrollTop=edArea.scrollTop; }
function setDirty(d){
  editor.dirty=d; edSave.disabled=!d||editor.readonly||editor.image;
  updateTabBar();
  const sel=editor.path&&(window.CSS&&CSS.escape?CSS.escape(editor.path):editor.path);
  const row=sel&&$('fileList').querySelector('.trow[data-path="'+sel+'"]');
  if(row) row.classList.toggle('dirty',d);
}
function updateTabBar(){
  const bar=$('tabBar'); if(!bar) return;
  if(!editor.path){ bar.innerHTML=''; return; }
  const name=editor.path.split('/').pop()||editor.path;
  const dot=editor.dirty?'<span class="dot">●</span>':'';
  bar.innerHTML='<div class="tab active">'+dot+esc(name)+'<button class="close" id="tabClose" title="ปิด">×</button></div>';
  $('tabClose').onclick=e=>{ e.stopPropagation(); closeEditor(); };
}
function showMode(mode){
  edWrap.classList.toggle('hidden', mode!=='text');
  edImage.classList.toggle('hidden', mode!=='image');
}
async function openFile(path){
  const f=fileMap[path]; if(!f) return;
  if(editor.dirty&&editor.path!==path&&!confirm('ทิ้งการแก้ไข '+editor.path+'?')) return;
  if(f.image) return openImage(path);
  if(f.binary){ statusText.textContent='Binary file'; return; }
  return openText(path);
}
async function openText(path){
  if(!api()) return;
  let r; try{ r=await api().open_file({root:projectRoot, path}); }catch(e){ r={error:String(e)}; }
  if(!r||r.error){ statusText.textContent='Cannot open'; return; }
  editor.path=path; editor.original=r.content; editor.readonly=!!r.readonly; editor.image=false;
  editor.lang=langOf(path); HLDEF=buildHL(editor.lang);
  edArea.value=r.content; edArea.readOnly=editor.readonly;
  showEditorPanel(); showMode('text'); updateTabBar(); setDirty(false); paint();
  [...$('fileList').querySelectorAll('.trow.open')].forEach(x=>x.classList.remove('open'));
  const sel=window.CSS&&CSS.escape?CSS.escape(path):path;
  const row=$('fileList').querySelector('.trow[data-path="'+sel+'"]'); if(row) row.classList.add('open');
  updateCtxBar(); if(!editor.readonly) edArea.focus();
}
async function openImage(path){
  if(!api()) return;
  let r; try{ r=await api().read_image({root:projectRoot, path}); }catch(e){ r={error:String(e)}; }
  if(!r||r.error) return;
  editor.path=path; editor.image=true; editor.readonly=true; editor.dirty=false;
  edImg.src=r.data_uri; showEditorPanel(); showMode('image'); updateTabBar(); paint();
}
function closeEditor(force){
  if(!force&&editor.dirty&&!confirm('ทิ้งการแก้ไข?')) return;
  editor.path=null; editor.original=''; editor.dirty=false; editor.image=false;
  edArea.value=''; edInfo.textContent='';
  [...$('fileList').querySelectorAll('.trow.open,.trow.dirty')].forEach(x=>x.classList.remove('open','dirty'));
  hideEditorPanel(); updateTabBar(); updateCtxBar();
}
async function saveEditor(){
  if(!editor.path||editor.readonly||editor.image||!editor.dirty) return;
  let r; try{ r=await api().save_file({root:projectRoot, path:editor.path, content:edArea.value}); }catch(e){ r={ok:false}; }
  if(!r||!r.ok) return;
  editor.original=edArea.value; setDirty(false);
  edToast.classList.add('show'); setTimeout(()=>edToast.classList.remove('show'),1200);
}
edArea.addEventListener('input',()=>{ setDirty(edArea.value!==editor.original); schedulePaint(); });
edArea.addEventListener('scroll', syncScroll);
edArea.addEventListener('keydown', e=>{
  if(e.key==='Tab'){ e.preventDefault(); const s=edArea.selectionStart;
    edArea.value=edArea.value.slice(0,s)+'  '+edArea.value.slice(edArea.selectionEnd);
    edArea.selectionStart=edArea.selectionEnd=s+2; setDirty(edArea.value!==editor.original); schedulePaint(); }
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){ e.preventDefault(); saveEditor(); }
});
edSave.onclick=saveEditor; $('edClose').onclick=()=>closeEditor();

/* ── settings ── */
const modal=$('settingsModal'), provList=$('provList'); let gateways=[];
function makeProvRow(data){
  data=data||{}; const row=document.createElement('div'); row.className='prov';
  const opts=gateways.concat(['custom']).map(g=>'<option value="'+esc(g)+'">'+esc(g)+'</option>').join('');
  row.innerHTML='<div class="line"><select class="p-gw">'+opts+'</select><input class="p-key" type="password" placeholder="'+(data.has_key?'•••• saved':'API key')+'"><button class="p-del">×</button></div><input class="p-base hidden" type="text" placeholder="base URL"><input class="p-models" type="text" placeholder="models, comma-separated">';
  const gw=row.querySelector('.p-gw'), base=row.querySelector('.p-base');
  gw.value=data.gateway||'openrouter'; if(data.gateway&&!gateways.includes(data.gateway)) gw.value='custom';
  const syncBase=()=>base.classList.toggle('hidden', gw.value!=='custom');
  syncBase(); gw.onchange=syncBase; if(gw.value==='custom') base.value=data.base_url||'';
  row.querySelector('.p-key').value=data.api_key||'';
  row.querySelector('.p-models').value=(data.models||[]).join(', ');
  row.querySelector('.p-del').onclick=()=>{ row.remove(); if(!provList.children.length) makeProvRow(); };
  provList.appendChild(row);
}
function collectProviders(){
  return [...provList.querySelectorAll('.prov')].map(row=>({
    gateway:row.querySelector('.p-gw').value, base_url:row.querySelector('.p-base').value,
    api_key:row.querySelector('.p-key').value, models:row.querySelector('.p-models').value }));
}
async function openSettings(){
  if(!api()) return;
  let st; try{ st=await api().get_status(); }catch(e){ modal.classList.remove('hidden'); return; }
  gateways=st.gateways||[]; provList.innerHTML='';
  (st.providers&&st.providers.length?st.providers:[{gateway:'openrouter'}]).forEach(p=>makeProvRow(p));
  $('setJudge').value=st.judge_model||''; $('setCompress').checked=!!st.compress;
  $('setErr').textContent=''; modal.classList.remove('hidden');
}
async function saveSettings(){
  const payload={ providers:collectProviders(), judge_model:$('setJudge').value, compress:$('setCompress').checked };
  let r; try{ r=await api().save_settings(payload); }catch(e){ r={ok:false,error:String(e)}; }
  if(!r.ok){ $('setErr').textContent='⚠ '+(r.error||'Save failed'); return; }
  if(!r.configured){ $('setErr').textContent='⚠ ต้องมี API key และ model อย่างน้อย 1'; return; }
  configured=true; modal.classList.add('hidden'); sendBtn.disabled=false; statusText.textContent='Ready';
}
function applyDefaults(st){
  if($('optEnsemble')) $('optEnsemble').checked=(st.fusion_mode||'ensemble')==='ensemble';
  if($('optCompress')) $('optCompress').checked=!!st.compress;
  if($('optCache')) $('optCache').checked=!!st.cache;
}
async function checkStatus(){
  if(!api()){ setTimeout(checkStatus,250); return; }
  let st; try{ st=await api().get_status(); }catch(e){ setTimeout(checkStatus,250); return; }
  configured=st.configured; applyDefaults(st); refreshChats(); renderTree(); showMessagesEmpty();
  if(!configured){ sendBtn.disabled=true; statusText.textContent='Setup required'; openSettings(); }
}

/* ── wiring ── */
$('openFolder').onclick=openFolder;
$('newChat').onclick=newChat;
$('toggleChats').onclick=toggleChatDropdown;
$('settingsBtn').onclick=openSettings;
$('addProv').onclick=()=>makeProvRow();
$('setCancel').onclick=()=>{ if(configured) modal.classList.add('hidden'); };
$('setSave').onclick=saveSettings;
sendBtn.addEventListener('click', ask);
composer.addEventListener('input', updateCtxBar);
composer.addEventListener('keydown', e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); ask(); }});
document.addEventListener('keydown', e=>{ if(e.key==='Escape'&&configured&&!modal.classList.contains('hidden')) modal.classList.add('hidden'); });
window.addEventListener('pywebviewready', checkStatus);
setTimeout(checkStatus, 300);
composer.focus();
</script>
</body>
</html>
"""
