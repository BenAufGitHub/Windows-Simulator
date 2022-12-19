"use strict";

const {ipcRenderer} = require('electron')

document.getElementById('save-back').onclick = () => ipcRenderer.send("change-win", "index")