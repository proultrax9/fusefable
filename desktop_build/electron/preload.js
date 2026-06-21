const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('fusionDesktop', {
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  pickFolder: () => ipcRenderer.invoke('pick-folder'),
  monacoPath: () => ipcRenderer.invoke('monaco-path'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
});
