
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('voiceAPI', {
  transcribe: (audioBuffer) =>
    ipcRenderer.invoke('voice:transcribe', audioBuffer),
  speak: (text) => ipcRenderer.invoke('voice:speak', text),
});