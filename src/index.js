const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const record = document.getElementById("record")
const expand = document.getElementById("expand-saves");
let input = document.getElementById("save-input");


// ============================= functionality ===================================


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

const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
    expand.onclick = expandRecordFiles;
}

function resolveChooseRecordFile (result, filenames) {
    removeRecordSelectOptions();
    if(result==0)
        createNewRecording();
    else
        selectRecording(filenames[result]);
}

function getRecordFiles () {
    // TODO
    return ["Boba Fett", "Tyrannus Saurus Rex.exe", "Stevosaurus TV", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m"];
}


// ============================= Responsiveness =====================================


// Popups disappear on blur
window.addEventListener('mouseup', function(e){
    if (e.target.classList.contains('expand-button-option') || e.target.classList.contains('floating-top-right')) return;
    removeRecordSelectOptions();
})


// ===== record creation ====>

const expandRecordFiles = () => {
    let filenames = getRecordFiles();
    filenames.unshift("----&#60;new&#62;----");
    let optionButtions = createButtons(filenames, resolveChooseRecordFile);
    container = createRecordContainer();
    addRecordExpansionToDocument(container, optionButtions);
    container.focus();
}

const addRecordExpansionToDocument = (container, children) => {
    children.forEach(element => {
        container.append(element);
    });
    let parent = document.getElementById("input-field");
    parent.appendChild(container);
}


// ======= record removal ====>

function selectRecording (filename) {
    input.setAttribute("disabled", "");
    //TODO actually set Recording
    setRecordFileInput(filename);
}

function setRecordFileInput (text) {
    input['value'] = text;
}

function removeRecordSelectOptions () {
    let recMenu = document.getElementById('input-field');
    let container = document.getElementById('record-select-container');
    if(!container) return;
    recMenu.removeChild(container);
}

function createNewRecording() {
    setRecordFileInput("");
    input.removeAttribute("disabled");
    input.focus()
}


// ============================ DOM-Elements =========================================

// ============= RecordOptionButtons ==>

function createButtons (filenames, callbackResultFunc) {
    let buttons = [];
    for(let i=0; i<filenames.length; i++){
        let b = createNewButton(i, filenames, callbackResultFunc);
        buttons.push(b);
    }
    buttons[0].classList.add("new-recording-option")
    return buttons;
}

const createNewButton = (i, filenames, callbackResultFunc) => {
    let b = document.createElement("button");
    b.classList.add("expand-button-option");
    if(i+1==filenames.length)
        b.classList.add("no-border");
    else
        b.classList.add("record-option-border");
    b.onclick = () => callbackResultFunc(i, filenames);
    b.innerHTML = filenames[i];
    return b;
}

// ============== Option Container =============>

function createRecordContainer () {
    let container = document.createElement("span");
    container.id = "record-select-container";
    container.classList.add("floating-top-right");
    container.setAttribute("contentEditable", "");
    container.setAttribute("spellcheck", "false");
    i = document.getElementById("input-field")
    return container;
}



main:
{
    addClickEvents();
    setRecordFileInput("Select recording");
}
