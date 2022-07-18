"use strict";

const {ipcRenderer} = require('electron');

const WINDOW_API = {
    getInfo: async () => ipcRenderer.invoke("getWindowResolveInfo", null),
    sendResults: (result) => ipcRenderer.send("windowResolveResults", result)
}

const input = document.getElementById('num-input');
const info = document.getElementById('info');
const submit = document.getElementById('submit');

function processData() {
    submit.onclick = () => {}
    let num = input?.value
    WINDOW_API.sendResults(num)
}

function customizeSubmit() {
    submit.onclick = processData;
}

async function customizeInfo() {
    let information = await WINDOW_API.getInfo()
    info.innerHTML = JSON.stringify(information)
}


customizeSubmit();
customizeInfo();