"""UI ของหน้าต่าง desktop (HTML/CSS/JS ฝังในไฟล์เดียว — ไม่พึ่ง network)."""

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fuse Fable</title>
<style>
  :root { --bg:#0f1115; --panel:#171a21; --panel2:#1f2430; --line:#2a3040;
          --text:#e6e9ef; --muted:#8b93a7; --accent:#5b9cff; --green:#3fb950; }
  * { box-sizing:border-box; }
  html,body { margin:0; height:100%; }
  body { background:var(--bg); color:var(--text); font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;
         display:flex; flex-direction:column; }
  header { padding:12px 16px; border-bottom:1px solid var(--line); display:flex;
           align-items:center; gap:10px; background:var(--panel); }
  header .dot { width:9px; height:9px; border-radius:50%; background:var(--green); }
  header h1 { font-size:15px; margin:0; font-weight:600; }
  header .sub { color:var(--muted); font-size:12px; margin-left:auto; }
  #opts { display:flex; gap:14px; align-items:center; flex-wrap:wrap;
          padding:8px 16px; border-bottom:1px solid var(--line); background:var(--panel);
          font-size:13px; color:var(--muted); }
  #opts label { display:flex; gap:5px; align-items:center; cursor:pointer; }
  #opts input[type=text] { background:var(--panel2); border:1px solid var(--line);
          color:var(--text); border-radius:6px; padding:4px 8px; font-size:12px; width:200px; }
  #msgs { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px; }
  .bubble { max-width:88%; padding:10px 13px; border-radius:12px; white-space:pre-wrap;
            word-wrap:break-word; }
  .user { align-self:flex-end; background:var(--accent); color:#fff; border-bottom-right-radius:3px; }
  .bot { align-self:flex-start; background:var(--panel2); border:1px solid var(--line);
         border-bottom-left-radius:3px; }
  .meta { color:var(--muted); font-size:12px; margin-top:7px; padding-top:7px;
          border-top:1px solid var(--line); }
  .err { background:#3a1d1d; border-color:#5c2b2b; color:#ffb4b4; }
  details { margin-top:6px; } summary { cursor:pointer; color:var(--accent); font-size:12px; }
  details pre { background:var(--bg); padding:8px; border-radius:6px; overflow:auto;
                font-size:12px; border:1px solid var(--line); }
  #inbar { display:flex; gap:8px; padding:12px 16px; border-top:1px solid var(--line);
           background:var(--panel); }
  #q { flex:1; resize:none; height:44px; max-height:160px; background:var(--panel2);
       border:1px solid var(--line); color:var(--text); border-radius:8px; padding:10px 12px;
       font:14px inherit; }
  #send { background:var(--accent); color:#fff; border:0; border-radius:8px; padding:0 18px;
          font-weight:600; cursor:pointer; }
  #send:disabled { opacity:.5; cursor:default; }
  .spin { color:var(--muted); font-size:13px; }
</style>
</head>
<body>
  <header>
    <span class="dot"></span><h1>Fuse Fable</h1>
    <span class="sub">fan-out · judge/ensemble · best answer</span>
  </header>
  <div id="opts">
    <label><input type="checkbox" id="compress"> compress</label>
    <label><input type="checkbox" id="ensemble"> ensemble</label>
    <label><input type="checkbox" id="cache"> cache</label>
    <input type="text" id="models" placeholder="models (comma, ว่าง=ทุกตัว)">
  </div>
  <div id="msgs"></div>
  <div id="inbar">
    <textarea id="q" placeholder="พิมพ์คำถาม… (Enter ส่ง, Shift+Enter ขึ้นบรรทัด)"></textarea>
    <button id="send">Send</button>
  </div>
<script>
  const msgs = document.getElementById('msgs');
  const q = document.getElementById('q');
  const send = document.getElementById('send');

  function esc(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
  function add(cls, html){ const el=document.createElement('div'); el.className='bubble '+cls;
    el.innerHTML=html; msgs.appendChild(el); msgs.scrollTop=msgs.scrollHeight; return el; }

  function renderBot(r){
    if(r.error){ add('bot err', '⚠️ '+esc(r.error)); return; }
    let meta = [];
    meta.push(r.chosen_model==='ensemble' ? 'ensemble' : 'from '+esc(r.chosen_model));
    meta.push(r.cached ? 'cached, $0' : '$'+(r.cost_usd||0).toFixed(4));
    if(r.compression) meta.push('compressed '+r.compression.original_chars+'→'+
        r.compression.final_chars+' (~'+r.compression.saved_pct+'%)');
    let cand = '';
    if(r.candidates && r.candidates.length){
      cand = '<details><summary>'+r.candidates.length+' candidates</summary>'+
        r.candidates.map(c=>'<div><b>'+esc(c.model)+'</b><pre>'+esc(c.text)+'</pre></div>').join('')+
        '</details>';
    }
    let warn = r.budget_warning ? '<div class="meta">⚠️ '+esc(r.budget_warning)+'</div>' : '';
    add('bot', esc(r.answer) + warn + '<div class="meta">'+meta.join(' · ')+'</div>' + cand);
  }

  async function ask(){
    const text = q.value.trim(); if(!text) return;
    add('user', esc(text)); q.value='';
    send.disabled=true;
    const spin = add('bot spin', 'กำลังฟิวชั่นหลายโมเดล…');
    const payload = { question:text,
      compress:document.getElementById('compress').checked,
      ensemble:document.getElementById('ensemble').checked,
      cache:document.getElementById('cache').checked,
      models:document.getElementById('models').value };
    try {
      const r = await window.pywebview.api.ask(payload);
      spin.remove(); renderBot(r);
    } catch(e){ spin.remove(); add('bot err','⚠️ '+esc(String(e))); }
    send.disabled=false; q.focus();
  }

  send.addEventListener('click', ask);
  q.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); ask(); }});
  q.focus();
</script>
</body>
</html>
"""
