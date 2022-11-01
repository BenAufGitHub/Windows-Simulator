"use strict";

const {ipcRenderer} = require('electron');

const WINDOW_API = {
    getInfo: async () => ipcRenderer.invoke("getWindowResolveInfo", null),
    showWindow: async (handle) => ipcRenderer.invoke("request", "showWindow", handle),
    sendResults: (result) => ipcRenderer.send("windowResolveResults", result),
    get_selected_simulation: async () => ipcRenderer.invoke("get-simulation", null),
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

async function displayInformation(process, recorded, selection, number, z_index) {
    info.appendChild(generateTitle(`Matching windows for process <strong>'${process}'<strong> (#${number})<br>`));
    info.appendChild(await generateRecordingInformation(recorded, z_index));
    createRadiobuttons(selection);
}

async function loadImage(z_index) {
    let div = document.createElement('div');
    let img = document.createElement('img');

    img.src = "./../resources/screenshots/" + await get_sim() +'/'+ z_index + ".jpg"
    img.alt = "Nothing to see here :("
    img.style["marginTop"] = "2px";
    div.style["marginLeft"] = "7px";
    div.style["marginRight"] = "7px";
    div.style["marginTop"] = "2px";
    div.appendChild(img)
    return div
}

async function get_sim () {
    let answerObj = await WINDOW_API.get_selected_simulation();
    if(answerObj.isSuccessful && answerObj.answer)
        return answerObj.answer;
    return "";
}

async function generateRecordingInformation(recorded, z_index) {
    let div = document.createElement('div');
    div.classList.add('content');
    div.style.border = "2px solid black";
    div.style.marginLeft = "10%";
    div.style.marginRight = "10%";

    div.appendChild(createParagraph(recorded));
    div.appendChild(await loadImage(z_index));
    return div;
}

function createParagraph(recorded) {
    let p = document.createElement('p');

    let header = document.createElement('h6');
    header.innerHTML = "Recording information:";
    header.style.textDecoration = "underline";
    header.style["marginTop"] = "5px";

    p.appendChild(header);
    p.innerHTML += `Window title: <strong>${recorded}</strong><br>`;
    p.innerHTML += "Capture from first interaction:<br>";
    p.style["marginBottom"] = "2px";
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
    let p = document.getElementById('pick-info');
    p.innerHTML = p.innerHTML += ` ${selection.length} found:`
    let form = document.getElementById("form")
    selection.forEach((element, i) => {
        let div = document.createElement('div');
        div.classList.add('column');

        let radio = createRadioOption(i, i);
        if(i === 0)
            radio.setAttribute("checked", "checked");
        div.appendChild(radio);
        div.appendChild(createRadioLabel(radio.id, element[0]));
        div.appendChild(createShowButton(element[1]));
        form.appendChild(div);
    })
}

const createShowButton = (handle) => {
    let button = document.createElement('button');
    button.type = 'button';
    button.style["marginLeft"] = "10px";
    button.style["marginBottom"] = "7px";
    button.classList.add('button');
    button.classList.add('is-link');
    button.classList.add('is-small');
    button.classList.add('is-outlined');
    button.innerHTML = "show";
    
    button.onclick = () => {
        WINDOW_API.showWindow(handle).then((msg)=>console.log(msg), (error) => console.log(`Error occured: ${error}`));
    }
    return button;
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