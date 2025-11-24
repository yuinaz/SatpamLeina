const { app, BrowserWindow, Tray, Menu, shell, nativeImage } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const axios = require('axios');
let win, tray, online=false;

function createWindow () {
  win = new BrowserWindow({ width: 320, height: 280, resizable: false, alwaysOnTop: true, frame: false,
    webPreferences: { preload: path.join(__dirname,'preload.js') } });
  win.loadFile('index.html');
}
function setTrayStatus(ok){
  online = !!ok; if(!tray) return;
  tray.setToolTip(online? '🟢 SatpamBot' : '🔴 SatpamBot');
}
function createTray(){
  const icon = nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAAHElEQVQoka3OMQ4AIAwEwQ0s4k0pGg2Cchc1p2yE0v0G6Z2cQ9gS6n5bW0AAAAASUVORK5CYII=');
  tray = new Tray(icon);
  const ctx = Menu.buildFromTemplate([
    { label: 'Show/Hide Widget', click(){ if(win.isVisible()) win.hide(); else win.show(); } },
    { type: 'separator' },
    { label: 'Open Dashboard', click(){ shell.openExternal(process.env.WIDGET_DASHBOARD || (process.env.WIDGET_BASE || '') + '/dashboard'); } },
    { label: 'Quit', click(){ app.quit(); } },
  ]);
  tray.setContextMenu(ctx);
}
async function pollOnce(){
  try{
    const base = process.env.WIDGET_BASE || 'http://localhost:10000';
    const { data } = await axios.get(base + '/desktop-status', { timeout: 8000 });
    const ok = !!(data && data.ok);
    setTrayStatus(ok && data.bot && data.bot.ok);
    if(win && win.webContents) win.webContents.send('status-update', data);
  }catch(e){ setTrayStatus(false); if(win && win.webContents) win.webContents.send('status-update', { ok:false }); }
}
function schedulePoll(){ pollOnce(); setInterval(pollOnce, 15000); }
function setupAutoUpdate(){ if(process.env.DISABLE_AUTOUPDATE==='1') return; autoUpdater.autoDownload = true; autoUpdater.checkForUpdatesAndNotify(); setInterval(()=> autoUpdater.checkForUpdates(), 3600000); }
app.whenReady().then(()=>{ createWindow(); createTray(); schedulePoll(); setupAutoUpdate(); app.on('activate', ()=>{ if(BrowserWindow.getAllWindows().length===0) createWindow(); }); });
app.on('window-all-closed', ()=>{ if(process.platform!=='darwin') app.quit(); });
