const { contextBridge, ipcRenderer, shell } = require('electron');
contextBridge.exposeInMainWorld('desk', {
  open: (url)=> shell.openExternal(url),
  onStatus: (fn)=> ipcRenderer.on('status-update', (_, data)=> fn(data)),
});
