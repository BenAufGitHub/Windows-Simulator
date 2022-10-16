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
    submit.style["marginBottom"] = "20px";
    submit.onclick = processData;
}

async function customizeInfo() {
    let information = await WINDOW_API.getInfo()
    displayInformation(information.process_name, information.recorded, information.selection, information.resolve_step_no, information.z_index)
}

function displayInformation(process, recorded, selection, number, z_index) {
    info.appendChild(generateTitle(`Matching windows for process <strong>'${process}'<strong> (#${number})<br>`));
    info.appendChild(generateRecordingInformation(recorded, z_index));
    createRadiobuttons(selection);
}

function loadImage(z_index) {
    let div = document.createElement('div');
    let img = document.createElement('img')
    img.src = "./../resources/screenshots/" + z_index + ".jpg"
    img.alt = "Nothing to see here :("
    div.style["marginLeft"] = "7px";
    div.style["marginRight"] = "7px";
    div.appendChild(img)
    return div
}

function generateRecordingInformation(recorded, z_index) {
    let div = document.createElement('div');
    div.classList.add('content');
    div.style.border = "2px solid black";
    div.style.marginLeft = "10%";
    div.style.marginRight = "10%";

    div.appendChild(createParagraph(recorded));
    div.appendChild(loadImage(z_index));
    return div;
}

function createParagraph(recorded) {
    let p = document.createElement('p');

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
    skip.style["marginBottom"] = "20px";
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