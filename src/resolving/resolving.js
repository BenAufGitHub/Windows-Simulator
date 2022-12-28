"use strict";

const {ipcRenderer} = require('electron');
const querystring = require('querystring')

const WINDOW_API = {
    getInfo: async (actionID) => ipcRenderer.invoke("getWindowResolveInfo", actionID),
    showWindow: async (handle) => ipcRenderer.invoke("request", "showWindow", handle),
    sendResults: (result, actionID) => ipcRenderer.send("windowResolveResults", result, actionID),
    get_selected_simulation: async () => ipcRenderer.invoke("get-simulation", null),
}

const input = document.getElementById('num-input');
const info = document.getElementById('info');
const submit = document.getElementById('submit');
const selectionDiv = document.getElementById('radio-selection');
let langPack = null;

function processData(actionID) {
    submit.onclick = () => {}
    let num = document.querySelector('input[name="window-matching"]:checked')?.value;
    num = +num
    if(!num && num !== 0) num = -1;
    WINDOW_API.sendResults(num, actionID)
}

function customizeSubmit(actionID) {
    submit.style["marginBottom"] = "20px";
    submit.onclick = () => processData(actionID);
}

function customizeInfo(information) {
    displayInformation(information.process_name, information.recorded, information.selection, information.winNo, information.z_index)
}

async function displayInformation(process, recorded, selection, number, z_index) {
    info.appendChild(await generateTitle());
    info.appendChild(await generateRecordingInformation(recorded, z_index, process, number));
    createRadiobuttons(selection);
}

async function loadImage(z_index) {
    let div = document.createElement('div');
    let img = document.createElement('img');
    img.id = "capture-image"
    img.src = "./../../resources/screenshots/" + await get_sim() +'/'+ z_index + ".jpg"
    img.alt = await getText("image-alt");
    div.appendChild(img)
    return div
}

async function get_sim () {
    let answerObj = await WINDOW_API.get_selected_simulation();
    if(answerObj.isSuccessful && answerObj.answer)
        return answerObj.answer;
    return "";
}

async function generateRecordingInformation(recorded, z_index, process, number) {
    let div = document.createElement('div');
    div.classList.add('content');
    div.id = "rec-information";

    div.appendChild(await createParagraph(recorded, process, number));
    div.appendChild(await loadImage(z_index));
    return div;
}

async function createParagraph(recorded, process, number) {
    let p = document.createElement('p');

    let header = document.createElement('h6');
    header.innerHTML = await getText('p-header');
    header.style.textDecoration = "underline";
    header.style["marginTop"] = "5px";

    p.appendChild(header);
    p.innerHTML += `${await getText('p-process')}<strong>${process}</strong><br>`;
    p.innerHTML += `${await getText('p-win-num')}<strong>${number}</strong><br>`;
    p.innerHTML += `${await getText('p-title')}<strong>${recorded}</strong><br>`;
    p.innerHTML += `${await getText('p-capture')}<br>`;
    p.style["marginBottom"] = "2px";
    return p;
}

async function generateTitle() {
    let title = document.createElement('h3');
    title.classList.add('title');
    title.style.marginTop = "10px";
    title.innerHTML = await getText("info-title");
    return title;
}

async function createRadiobuttons(selection) {
    let p = document.getElementById('pick-info');
    p.innerHTML = p.innerHTML += ` ${selection.length} ${await getText('found-amount')}`
    let form = document.getElementById("form")
    selection.forEach(async (element, i) => {
        let div = document.createElement('div');
        div.classList.add('column');

        let radio = createRadioOption(i, i);
        if(i === 0)
            radio.setAttribute("checked", "checked");
        div.appendChild(radio);
        div.appendChild(createRadioLabel(radio.id, element[0]));
        div.appendChild(await createShowButton(element[1]));
        form.appendChild(div);
    })
}

const createShowButton = async (handle) => {
    let button = document.createElement('button');
    button.type = 'button';
    button.style["marginLeft"] = "10px";
    button.style["marginBottom"] = "7px";
    button.classList.add('button');
    button.classList.add('is-link');
    button.classList.add('is-small');
    button.classList.add('is-outlined');
    button.innerHTML = await getText('show');
    
    button.onclick = () => {
        WINDOW_API.showWindow(handle).then((data)=> {
            if(!data.isSuccessful)
                return console.log(`Error occured: ${data.answer}`);
            console.log(data.answer)
        },
        (error) => console.log(`Error occured: ${error}`));
    }
    return button;
}

const customizeSkip = (actionID) => {
    let skip = document.getElementById('skip');
    skip.style["marginBottom"] = "20px";
    skip.onclick = () => {
        WINDOW_API.sendResults(-1, actionID);
    }
}

const createRadioLabel = (id, text) => {
    let label = document.createElement('label');
    label.htmlFor = id;
    label.innerHTML = `'${text}'`;
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


async function customizeRetry(actionID) {
    submit.style["marginBottom"] = "20px";
    submit.innerHTML = await getText('retry');
    submit.onclick = () => WINDOW_API.sendResults(true, actionID);
}

async function customizeSkipEmpty (actionID) {
    let skip = document.getElementById('skip');
    skip.innerHTML = await getText('skip-empty');
    skip.style["marginBottom"] = "20px";
    skip.onclick = () => {
        WINDOW_API.sendResults(false, actionID);
    }
}


function extractID () {
    let query = querystring.parse(global.location.search);
    let data = query['?data']
    return data
}


const main = async () => {
    await addInnerHTML();
    let actionID = extractID();
    let info = await WINDOW_API.getInfo(actionID);
    if(info["query"]==="selection"){
        customizeSubmit(actionID);
        customizeInfo(info);
        customizeSkip(actionID);
        return;
    }
    customizeRetry(actionID);
    customizeInfo(info);
    customizeSkipEmpty(actionID);
}


const addText = async (id) => {
    document.getElementById(id).innerHTML = await getText(id);
}

const getText = async (id) => {
    return (await getLangPack())[id];
}

const getLangPack = async () => {
    if(!langPack)
        langPack = await ipcRenderer.invoke('get-lang-pack', null);
    return langPack["resolving"];
}

async function addInnerHTML () {
    await addText('title');
    await addText('pick-info');
    await addText('skip');
    await addText('submit');
}


_main:
{
    main();
}