import asyncio
import threading
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator, State

app = FastAPI()

_loop: asyncio.AbstractEventLoop = None
_orchestrator: Orchestrator = None
_log_lines: list[str] = []


def _start_background_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


threading.Thread(target=_start_background_loop, daemon=True).start()


def _run_async(coro):
    asyncio.run_coroutine_threadsafe(coro, _loop)


class ScrapeRequest(BaseModel):
    url: str
    task: str


@app.post("/api/start")
def start(req: ScrapeRequest):
    global _orchestrator, _log_lines
    if not req.url.strip():
        return JSONResponse({"ok": False, "error": "URL is required"})
    if not req.task.strip():
        return JSONResponse({"ok": False, "error": "Task is required"})
    _log_lines = []
    def log(msg):
        _log_lines.append(msg)
    _orchestrator = Orchestrator(log_callback=log)
    _run_async(_orchestrator.run(req.url.strip(), req.task.strip()))
    return JSONResponse({"ok": True})


@app.post("/api/stop")
def stop():
    if _orchestrator:
        _orchestrator.stop()
    return JSONResponse({"ok": True})


@app.post("/api/resume")
def resume():
    if _orchestrator:
        _orchestrator.resolve_captcha()
    return JSONResponse({"ok": True})


@app.get("/api/status")
def status():
    if not _orchestrator:
        return JSONResponse({
            "state": "idle",
            "logs": [],
            "records": 0,
            "preview": [],
            "headers": [],
            "output": None,
            "captcha": False,
        })

    # Build preview — last 10 records
    preview = []
    headers = []
    if _orchestrator.records:
        # Collect all unique keys across records
        for r in _orchestrator.records:
            for k in r.keys():
                if k not in headers:
                    headers.append(k)
        preview = _orchestrator.records[-10:]

    return JSONResponse({
        "state": _orchestrator.state.value,
        "logs": _log_lines[-100:],
        "records": len(_orchestrator.records),
        "preview": preview,
        "headers": headers,
        "output": _orchestrator.output_paths.get("csv") if _orchestrator.output_paths else None,
        "captcha": _orchestrator.state == State.PAUSED,
    })


@app.get("/api/download")
def download():
    if not _orchestrator or not _orchestrator.output_paths:
        return JSONResponse({"error": "No file available"}, status_code=404)
    csv_path = _orchestrator.output_paths.get("csv")
    if not csv_path or not os.path.exists(csv_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=os.path.basename(csv_path)
    )


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(HTML)


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ScraperAI</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:       #0d1117;
    --surface:  #161b22;
    --surface2: #1c2333;
    --border:   #30363d;
    --blue:     #2f81f7;
    --green:    #3fb950;
    --red:      #f85149;
    --yellow:   #d29922;
    --text:     #e6edf3;
    --dim:      #8b949e;
    --r:        8px;
  }
  body {
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px; min-height: 100vh;
    display: flex; flex-direction: column;
  }
  header {
    padding: 16px 32px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 12px;
    background: var(--surface);
  }
  .logo {
    width: 32px; height: 32px; background: var(--blue);
    border-radius: 8px; display: flex; align-items: center;
    justify-content: center; font-size: 16px;
  }
  header h1 { font-size: 18px; font-weight: 600; }
  header span { color: var(--dim); font-size: 13px; margin-left: auto; }
  .container {
    max-width: 960px; margin: 0 auto; padding: 28px 24px;
    width: 100%; flex: 1; display: flex; flex-direction: column; gap: 18px;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--r); padding: 20px;
  }
  .card-title {
    font-size: 11px; font-weight: 700; color: var(--dim);
    text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 14px;
  }
  label { display: block; font-size: 13px; color: var(--dim); margin-bottom: 5px; font-weight: 500; }
  input, textarea, select {
    width: 100%; background: var(--bg); border: 1px solid var(--border);
    border-radius: var(--r); color: var(--text); font-size: 14px;
    padding: 9px 13px; outline: none; transition: border-color 0.15s;
    font-family: inherit;
  }
  input:focus, textarea:focus { border-color: var(--blue); }
  textarea { resize: vertical; min-height: 60px; }
  .input-group { margin-bottom: 12px; }
  .input-group:last-child { margin-bottom: 0; }
  .hint { font-size: 11px; color: var(--dim); margin-top: 4px; }
  .btn-row { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
  button {
    padding: 8px 18px; border-radius: var(--r); border: none;
    font-size: 13px; font-weight: 600; cursor: pointer;
    transition: opacity 0.15s, transform 0.1s;
    display: flex; align-items: center; gap: 6px;
  }
  button:active { transform: scale(0.97); }
  button:disabled { opacity: 0.35; cursor: not-allowed; }
  .btn-primary { background: var(--blue); color: #fff; }
  .btn-primary:hover:not(:disabled) { opacity: 0.85; }
  .btn-danger { background: #2d1618; color: var(--red); border: 1px solid #5a1e20; }
  .btn-danger:hover:not(:disabled) { background: #3d1e20; }
  .btn-warning { background: #2d2208; color: var(--yellow); border: 1px solid #5a4208; }
  .btn-success { background: #0d2818; color: var(--green); border: 1px solid #1a4a28; }
  .btn-success:hover { background: #1a3820; }
  /* Status */
  .status-bar {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; background: var(--surface2);
    border: 1px solid var(--border); border-radius: var(--r); font-size: 13px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .dot-idle     { background: var(--dim); }
  .dot-running  { background: var(--blue); animation: pulse 1.4s infinite; }
  .dot-paused   { background: var(--yellow); }
  .dot-complete { background: var(--green); }
  .dot-error    { background: var(--red); }
  .dot-stopped  { background: var(--dim); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .record-count { margin-left: auto; color: var(--dim); font-size: 12px; font-weight: 600; }
  /* Two column layout */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  @media(max-width: 640px) { .two-col { grid-template-columns: 1fr; } }
  /* Log */
  .log-box {
    background: var(--bg); border: 1px solid var(--border);
    border-radius: var(--r); padding: 12px;
    font-family: 'SF Mono','Fira Code',monospace; font-size: 11.5px;
    line-height: 1.75; height: 260px; overflow-y: auto; color: var(--dim);
  }
  .log-line { margin: 0; }
  .log-line.state { color: var(--blue); }
  .log-line.error { color: var(--red); }
  .log-line.cache { color: var(--green); }
  .log-line.warn  { color: var(--yellow); }
  /* Preview table */
  .table-wrap {
    overflow-x: auto; border-radius: var(--r);
    border: 1px solid var(--border); max-height: 260px; overflow-y: auto;
  }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th {
    background: var(--surface2); color: var(--dim);
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
    font-size: 10px; padding: 8px 12px; text-align: left;
    border-bottom: 1px solid var(--border); white-space: nowrap;
    position: sticky; top: 0;
  }
  td {
    padding: 7px 12px; border-bottom: 1px solid var(--border);
    color: var(--text); max-width: 220px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--surface2); }
  .empty-preview {
    text-align: center; padding: 32px; color: var(--dim); font-size: 13px;
  }
  /* Alerts */
  .alert {
    display: none; border-radius: var(--r);
    padding: 12px 16px; font-size: 13px;
    align-items: center; gap: 12px;
  }
  .alert.visible { display: flex; }
  .alert-captcha { background: #2d2208; border: 1px solid var(--yellow); color: var(--yellow); }
  .alert-download { background: #0d2818; border: 1px solid #1a4a28; color: var(--green); }
  footer {
    text-align: center; padding: 14px; color: var(--dim);
    font-size: 12px; border-top: 1px solid var(--border);
  }
</style>
</head>
<body>

<header>
  <div class="logo">🕷</div>
  <h1>ScraperAI</h1>
  <span>AI-powered web extraction</span>
</header>

<div class="container">

  <!-- Job config -->
  <div class="card">
    <div class="card-title">Scrape Job</div>
    <div class="input-group">
      <label for="url">Target URL</label>
      <input id="url" type="text" placeholder="https://example.com/directory/{a-z}" autocomplete="off">
      <div class="hint">
        Use <code>{a-z}</code> to scrape all letters A–Z &nbsp;|&nbsp;
        Use <code>{1-50}</code> to scrape pages 1–50 &nbsp;|&nbsp;
        Or enter a plain URL for single-page / auto-pagination
      </div>
    </div>
    <div class="input-group">
      <label for="task">What to extract</label>
      <textarea id="task" placeholder="Extract all company names, phone numbers, and addresses"></textarea>
    </div>
    <div class="btn-row">
      <button class="btn-primary" id="btn-start">
        <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor"><polygon points="2,1 11,6 2,11"/></svg>
        Start
      </button>
      <button class="btn-danger" id="btn-stop" disabled>
        <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor"><rect x="1" y="1" width="10" height="10" rx="1"/></svg>
        Stop
      </button>
    </div>
  </div>

  <!-- Status -->
  <div class="status-bar">
    <div class="dot dot-idle" id="dot"></div>
    <span id="state-label">Idle — ready to scrape</span>
    <span class="record-count" id="record-count"></span>
  </div>

  <!-- Captcha alert -->
  <div class="alert alert-captcha" id="captcha-alert">
    <span style="font-size:18px">⚠️</span>
    <div><strong>Captcha detected.</strong> Solve it in the browser window, then click Resume.</div>
    <button class="btn-warning" id="btn-resume" style="margin-left:auto">✓ Resume</button>
  </div>

  <!-- Download alert -->
  <div class="alert alert-download" id="download-alert">
    <span style="font-size:18px">✅</span>
    <div><strong>Results ready.</strong> Your data has been extracted.</div>
    <button class="btn-success" id="btn-download" style="margin-left:auto">↓ Download CSV</button>
  </div>

  <!-- Two column: log + preview -->
  <div class="two-col">

    <!-- Log -->
    <div class="card">
      <div class="card-title">Live Log</div>
      <div class="log-box" id="log-box">
        <p class="log-line" style="color:#444">Waiting for job to start...</p>
      </div>
    </div>

    <!-- Data preview -->
    <div class="card">
      <div class="card-title">Data Preview <span id="preview-count" style="color:var(--dim);font-weight:400;text-transform:none;letter-spacing:0"></span></div>
      <div class="table-wrap" id="table-wrap">
        <div class="empty-preview">No data yet</div>
      </div>
    </div>

  </div>

</div>

<footer>ScraperAI — AI-powered web extraction</footer>

<script>
  const urlInput     = document.getElementById('url');
  const taskInput    = document.getElementById('task');
  const btnStart     = document.getElementById('btn-start');
  const btnStop      = document.getElementById('btn-stop');
  const btnResume    = document.getElementById('btn-resume');
  const btnDownload  = document.getElementById('btn-download');
  const dot          = document.getElementById('dot');
  const stateLabel   = document.getElementById('state-label');
  const recordCount  = document.getElementById('record-count');
  const logBox       = document.getElementById('log-box');
  const captchaAlert = document.getElementById('captcha-alert');
  const downloadAlert= document.getElementById('download-alert');
  const tableWrap    = document.getElementById('table-wrap');
  const previewCount = document.getElementById('preview-count');

  let pollInterval = null;
  let lastLogCount = 0;

  const STATE_LABELS = {
    idle:     'Idle — ready to scrape',
    running:  'Running...',
    paused:   'Paused — captcha detected',
    complete: 'Complete',
    stopped:  'Stopped',
    error:    'Error',
  };

  async function post(url, body) {
    const r = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: body ? JSON.stringify(body) : undefined,
    });
    return r.json();
  }

  btnStart.addEventListener('click', async () => {
    const url  = urlInput.value.trim();
    const task = taskInput.value.trim();
    if (!url)  { alert('Please enter a URL.');  return; }
    if (!task) { alert('Please describe what to extract.'); return; }
    logBox.innerHTML = '';
    tableWrap.innerHTML = '<div class="empty-preview">No data yet</div>';
    previewCount.textContent = '';
    lastLogCount = 0;
    downloadAlert.classList.remove('visible');
    captchaAlert.classList.remove('visible');
    const res = await post('/api/start', {url, task});
    if (!res.ok) { alert(res.error); return; }
    btnStart.disabled = true;
    btnStop.disabled  = false;
    startPolling();
  });

  btnStop.addEventListener('click', async () => { await post('/api/stop'); });
  btnResume.addEventListener('click', async () => {
    await post('/api/resume');
    captchaAlert.classList.remove('visible');
  });
  btnDownload.addEventListener('click', () => { window.location.href = '/api/download'; });

  function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(poll, 1500);
  }
  function stopPolling() {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
  }

  async function poll() {
    let data;
    try { data = await (await fetch('/api/status')).json(); }
    catch { return; }

    // Dot + label
    dot.className = 'dot dot-' + data.state;
    stateLabel.textContent = STATE_LABELS[data.state] || data.state;
    recordCount.textContent = data.records > 0 ? data.records + ' records' : '';

    // Log
    if (data.logs.length !== lastLogCount) {
      logBox.innerHTML = '';
      data.logs.forEach(line => {
        const p = document.createElement('p');
        p.className = 'log-line';
        if (line.includes('[State]')) p.classList.add('state');
        if (line.includes('error') || line.includes('Error') || line.includes('Fatal')) p.classList.add('error');
        if (line.includes('cached') || line.includes('Saved') || line.includes('fallback')) p.classList.add('cache');
        if (line.includes('CAPTCHA') || line.includes('Blocked') || line.includes('outdated')) p.classList.add('warn');
        p.textContent = line;
        logBox.appendChild(p);
      });
      logBox.scrollTop = logBox.scrollHeight;
      lastLogCount = data.logs.length;
    }

    // Data preview table
    if (data.headers && data.headers.length > 0 && data.preview && data.preview.length > 0) {
      let html = '<table><thead><tr>';
      data.headers.forEach(h => { html += `<th>${h}</th>`; });
      html += '</tr></thead><tbody>';
      data.preview.forEach(row => {
        html += '<tr>';
        data.headers.forEach(h => {
          const val = row[h] != null ? row[h] : '';
          html += `<td title="${String(val).replace(/"/g,"&quot;")}">${String(val)}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody></table>';
      tableWrap.innerHTML = html;
      previewCount.textContent = `— showing last ${data.preview.length}`;
    }

    captchaAlert.classList.toggle('visible', data.captcha);

    if (['complete', 'stopped'].includes(data.state) && data.output) {
      downloadAlert.classList.add('visible');
    }

    if (['complete', 'stopped', 'error'].includes(data.state)) {
      btnStart.disabled = false;
      btnStop.disabled  = true;
      stopPolling();
    }
  }
</script>
</body>
</html>"""
