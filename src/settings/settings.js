"use strict";

const {ipcRenderer} = require('electron');

document.getElementById('save-back').onclick = () => ipcRenderer.send("kill-settings", null);