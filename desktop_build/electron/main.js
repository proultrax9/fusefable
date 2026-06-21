const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow = null;
let backendProc = null;
let backendPort = 0;

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, '127.0.0.1', () => {
      const port = srv.address().port;
      srv.close(() => resolve(port));
    });
    srv.on('error', reject);
  });
}

function waitForHealth(port, tries = 60) {
  return new Promise((resolve, reject) => {
    let n = 0;
    const tick = () => {
      http.get(`http://127.0.0.1:${port}/api/health`, (res) => {
        if (res.statusCode === 200) resolve();
        else retry();
      }).on('error', retry);
    };
    const retry = () => {
      if (++n >= tries) reject(new Error('Backend failed to start'));
      else setTimeout(tick, 250);
    };
    tick();
  });
}

async function startBackend() {
  backendPort = await getFreePort();
  const isPackaged = app.isPackaged;
  let cmd, args, cwd;

  if (isPackaged) {
    cmd = path.join(process.resourcesPath, 'fusion-backend.exe');
    args = ['--port', String(backendPort), '--host', '127.0.0.1'];
    cwd = path.dirname(cmd);
  } else {
    cmd = process.platform === 'win32' ? 'python' : 'python3';
    args = [
      path.join(__dirname, '..', 'backend_entry.py'),
      '--port', String(backendPort),
      '--host', '127.0.0.1',
    ];
    cwd = path.join(__dirname, '..');
  }

  backendProc = spawn(cmd, args, {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });
  backendProc.on('exit', (code) => {
    if (code && code !== 0 && mainWindow) {
      dialog.showErrorBox('Fusion Fable', `Backend exited (${code})`);
    }
  });
  await waitForHealth(backendPort);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#1e1e1e',
    title: 'Fusion Fable',
    icon: path.join(__dirname, '..', 'FuseFable.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  mainWindow.setMenuBarVisibility(false);
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    createWindow();
  } catch (e) {
    dialog.showErrorBox('Fusion Fable', String(e.message || e));
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (backendProc) backendProc.kill();
  app.quit();
});

ipcMain.handle('get-backend-url', () => `http://127.0.0.1:${backendPort}`);

ipcMain.handle('pick-folder', async () => {
  const r = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
  });
  if (r.canceled || !r.filePaths.length) return null;
  return r.filePaths[0];
});

ipcMain.handle('monaco-path', () => {
  const p = path.join(__dirname, 'node_modules', 'monaco-editor', 'min', 'vs');
  return fs.existsSync(p) ? p : null;
});

ipcMain.handle('open-external', (_, url) => shell.openExternal(url));
