"use strict";

const {ipcRenderer} = require('electron');

function main () {
    document.getElementById('save-back').onclick = () => ipcRenderer.send("kill-settings", null);
    controlInputs();
}

async function controlInputs () {
    let configs = await ipcRenderer.invoke('get-app-settings', null);
    preToggleInputs(configs);
}


function preToggleInputs (configs) {
    document.getElementById('lang-in').checked = (configs["customizable"]["language"] == 'german')
    document.getElementById('toggle-screen').checked = configs["customizable"]["takeScreenshots"]
    document.getElementById('toggle-check').checked = configs["customizable"]["controlWindows"]
}

main:
{
    main()
}
