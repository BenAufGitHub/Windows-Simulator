const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const record = document.getElementById("record")
const expand = document.getElementById("expand-saves");
let input = document.getElementById("save-input");

function styleButton(btn) {
    btn.style["display"] = "inline-block";
    btn.style["text-align"] = "center"
}

const WINDOW_API = {
    pause: (application) => ipcRenderer.send("pause", application),
    start: (application) => ipcRenderer.send("start", application),
    resume: (application) => ipcRenderer.send("resume", application),
    getInfo: async (request, body) => ipcRenderer.invoke("request", request, body)
}

const startRecording = () => {
    record.onclick = () => null;
    WINDOW_API.start("record")
}
const startSimulate = () => {
    simulate.onclick = () => {
        WINDOW_API.start("simulate")
    }
}


function resolveChooseRecordFile (result) {
    //TODO
}

function getRecordFiles () {
    // TODO
    return ["Boba Fett", "Tyrannus Saurus Rex.exe", "Stevosaurus TV", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"];
}

function createButtons (filenames, callbackResultFunc) {
    let buttons = [];
    for(let i=0; i<filenames.length; i++){
        let b = document.createElement("button");
        b.classList.add("expand-button-option");
        if(i+1==filenames.length)
            b.classList.add("no-border");
        else
            b.classList.add("record-option-border");
        b.onclick = () => callbackResultFunc(i);
        b.innerHTML = filenames[i];
        buttons.push(b);
    }
    buttons[0].classList.add("new-recording-option")
    return buttons;
}

function createRecordContainer () {
    let container = document.createElement("div");
    container.classList.add("floating-top-right");
    return container;
}

const expandRecordFiles = () => {
    let filenames = getRecordFiles();
    filenames.unshift("----&#60;new&#62;----");
    let optionButtions = createButtons(filenames, resolveChooseRecordFile);
    container = createRecordContainer();
    addRecordExpansionToDocument(container, optionButtions);
}

const addRecordExpansionToDocument = (container, children) => {
    children.forEach(element => {
        container.append(element);
    });
    let parent = document.getElementById("input-field");
    parent.appendChild(container);
}


function setRecordFileInput (text) {
    input['value'] = text;
}

const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
    expand.onclick = expandRecordFiles;
}



main:
{
    addClickEvents();
    setRecordFileInput("Select recording")
}
