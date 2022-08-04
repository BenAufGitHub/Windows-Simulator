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
    displayInformation(information.process_name, information.recorded, information.selection, information.resolve_step_no)
}

function displayInformation(process, recorded, selection, number) {
    info.appendChild(generateTitle(`Matching windows for process <strong>'${process}'<strong> (#${number})<br>`));
    info.appendChild(generateRecordingInformation(recorded));
    createRadiobuttons(selection);
}

function generateRecordingInformation(recorded) {
    let p = document.createElement('p');
    p.classList.add('content');
    p.style.border = "2px solid black";
    p.style.marginLeft = "10%";
    p.style.marginRight = "10%";

    let header = document.createElement('h6');
    header.innerHTML = "Recording information:";
    header.style.textDecoration = "underline";

    p.appendChild(header);
    p.innerHTML += `Window title: <strong>${recorded}</strong><br>`;
    p.innerHTML += "Capture from first interaction:<br>";
    return p;
}

function generateTitle(text) {
    let title = document.createElement('h3');
    title.classList.add('title');
    title.style.marginTop = "10px";
    title.innerHTML = text;
    return title;
}

function createRadiobuttons(selection) {
    let form = document.getElementById("form")
    selection.forEach((element, i) => {
        let div = document.createElement('div');
        div.classList.add('column');

        let radio = createRadioOption(i, i);
        if(i === 0)
            radio.setAttribute("checked", "checked");
        div.appendChild(radio);
        div.appendChild(createRadioLabel(radio.id, element));
        form.appendChild(div);
    })
}

const customizeSkip = () => {
    let skip = document.getElementById('skip');
    skip.onclick = () => {
        WINDOW_API.sendResults(-1);
    }
}

const createRadioLabel = (id, text) => {
    let label = document.createElement('label');
    label.htmlFor = id;
    label.innerHTML = text;
    label.classList.add("radio");
    return label;
}

function createRadioOption(value, elementNumber) {
    let radio = document.createElement('input');
    radio.name = "window-matching";
    radio.type = 'radio';
    radio.id = `checkbox-${elementNumber}`;
    radio.value = value;
    radio.style.marginRight = "5px"; 
    return radio;
}


customizeSubmit();
customizeInfo();
customizeSkip();