"use strict";

const {ipcRenderer} = require('electron');

const WINDOW_API = {
    getInfo: async () => ipcRenderer.invoke("getWindowResolveInfo", null),
    sendResults: (result) => ipcRenderer.send("windowResolveResults", result)
}

const input = document.getElementById('num-input');
const info = document.getElementById('info');
const submit = document.getElementById('submit');
const selectionDiv = document.getElementById('radio-selection');

function processData() {
    submit.onclick = () => {}
    let num = document.querySelector('input[name="window-matching"]:checked')?.value;
    if(!num) num = -1;
    WINDOW_API.sendResults(num)
}

function customizeSubmit() {
    submit.onclick = processData;
}

async function customizeInfo() {
    let information = await WINDOW_API.getInfo()
    displayInformation(information.process, information.recorded, information.selection)
}

function displayInformation(process, recorded, selection) {
    info.innerHTML = `Matching windows for process ${process}<br>`;
    info.innerHTML += `Recorded window named: ${recorded}<br>`;
    createRadiobuttons(selection);
}

function createRadiobuttons(selection) {
    let form = document.getElementById("form")
    selection.forEach((element, i) => {
        let radio = createRadioOption(i, i);
        if(i === 0)
            radio.setAttribute("checked", "checked");
        form.appendChild(radio);
        createRadioLabel(radio.id, element);
    })
    addNothingOption(form, selection.length);
}

const addNothingOption = (form, position) => {
    let radio = createRadioOption(-1, position);
    form.appendChild(radio);
    createRadioLabel(radio.id, "Nothing");
}

const createRadioLabel = (id, text) => {
    form.innerHTML += `<label for="${id}">${text}</label><br>`;
}

function createRadioOption(value, elementNumber) {
    let radio = document.createElement('input');
    radio.name = "window-matching";
    radio.type = 'radio';
    radio.id = `checkbox-${elementNumber}`;
    radio.value = value;
    return radio;
}


customizeSubmit();
customizeInfo();