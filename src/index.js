const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const record = document.getElementById("record")
const expand = document.getElementById("expand-saves");
let record_input = document.getElementById("save-input");

const standardRecordText = "Select recording";
standardSimulationText = "Select Simulation";

// ============================= functionality ===================================


const WINDOW_API = {
    pause: (application) => ipcRenderer.send("pause", application),
    start: (application) => ipcRenderer.send("start", application),
    resume: (application) => ipcRenderer.send("resume", application),
    getInfo: async (request, body) => ipcRenderer.invoke("request", request, body),
    setRecording: async (filename) => ipcRenderer.invoke("set-recording", filename),
    get_selected_recording: async () => ipcRenderer.invoke("get-recording", null),
    get_record_list: async () => ipcRenderer.invoke('get-record-list', null),
    get_selected_simulation: async () => ipcRenderer.invoke("get-simulation", null),
    get_sim_list: async () => ipcRenderer.invoke('get-simulation-list', null),
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
    document.getElementById('expand-sims').onclick = async () => console.log(await WINDOW_API.get_sim_list())
    document.getElementById('approve-new').onclick = evaluateNewRecording;
}

function resolveChooseRecordFile (result, filenames) {
    removeRecordSelectOptions();
    if(result==0)
        return createNewRecording();
    selectRecording(filenames[result]);
}

async function getRecordFiles () {
    let obj = await WINDOW_API.get_record_list();
    if(!obj.isSuccessful) return [];
    return obj.answer;
}

async function registerRecording(filename) {
    return await WINDOW_API.setRecording(filename);
}


function evaluateNewRecording() {
    result = record_input.value;
    if(warn_if_not_valid(result)) return;
    hideRecordWarning();
    selectRecording(result.trim());
}

function warn_if_not_valid(save) {
    save = save.trim();
    if(save.length <4 || save.length>20){
        setRecordWarning("Save must contain between 4 and 20 characters.");
        return true;
    }
    regex = /^[0-9a-zA-Z-_ ]+$/g
    if(!save.match(regex)){
        setRecordWarning("Save must only contain A-Z, a-z, 0-9, '-', '_' and spaces.");
        return true
    }
    return false
}

async function put_selected_recording () {
    let answerObj = await WINDOW_API.get_selected_recording()
    if(answerObj.isSuccessful && answerObj.answer)
        setRecordFileInput(answerObj.answer)
    else
        setRecordFileInput(standardRecordText)
}

async function put_selected_simulation () {
    let answerObj = await WINDOW_API.get_selected_simulation()
    if(answerObj.isSuccessful && answerObj.answer)
        setSimFileInput(answerObj.answer)
    else
        setSimFileInput(standardSimulationText)
}

// ============================= Responsiveness =====================================


// Popups disappear on blur
window.addEventListener('mouseup', function(e){
    if (e.target.classList.contains('expand-button-option') || e.target.classList.contains('floating-top-right')) return;
    removeRecordSelectOptions();
})


// ===== record creation ====>

const expandRecordFiles = async () => {
    hideRecordWarning();
    let filenames = await getRecordFiles();
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

async function selectRecording (filename) {
    record_input.setAttribute("disabled", "");
    let {isSuccessful, answer} = await registerRecording(filename);
    if(!isSuccessful){
        put_selected_recording()
        return setRecordWarning("Recording couldn't be selected.");
    }
    setRecordFileInput(filename);
    toggleWarning(answer == 'Careful')
    hideCheckmark();
}

async function toggleWarning(needsWarning){
    if(needsWarning)
        setRecordWarning("Careful: This save would overwrite an existing instance.");
    else
        hideRecordWarning();
}

function setRecordFileInput (text) {
    record_input['value'] = text;
}

function setSimFileInput (text) {
    let sim_in = document.getElementById('save-display');
    sim_in['value'] = text;
}

function removeRecordSelectOptions () {
    let recMenu = document.getElementById('input-field');
    let container = document.getElementById('record-select-container');
    if(!container) return;
    recMenu.removeChild(container);
}

function createNewRecording() {
    setRecordFileInput("");
    record_input.removeAttribute("disabled");
    record_input.focus()
    hideRecordWarning();
    showCheckmark();
}

function setRecordWarning (text) {
    let p = document.getElementById('warning-recording');
    p.removeAttribute("hidden");
    p.innerHTML = text;
}

function hideRecordWarning () {
    let p = document.getElementById('warning-recording');
    p.setAttribute("hidden", "");
}


function showCheckmark () {
    let b = document.getElementById('approve-new');
    b.removeAttribute('hidden');
}

function hideCheckmark () {
    let b = document.getElementById('approve-new');
    b.setAttribute('hidden', '');
}

// ============================ DOM-Elements =========================================

// ============= RecordOptionButtons ==>

function createButtons (filenames, callbackResultFunc) {
    let buttons = [];
    for(let i=0; i<filenames.length; i++){
        let b = createNewButton(i, filenames, callbackResultFunc);
        buttons.push(b);
    }
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
    let container = document.createElement("div");
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
    put_selected_recording();
    put_selected_simulation();
}
