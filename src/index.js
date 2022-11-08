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
    deleteRecording: async (filename) => ipcRenderer.invoke('delete-recording', filename), 
    get_selected_recording: async () => ipcRenderer.invoke("get-recording", null),
    get_record_list: async () => ipcRenderer.invoke('get-record-list', null),

    get_selected_simulation: async () => ipcRenderer.invoke("get-simulation", null),
    get_sim_list: async () => ipcRenderer.invoke('get-simulation-list', null),
    setSimulation: async (filename) => ipcRenderer.invoke('set-simulation', filename),
}


const isRecSelected = async () => {
    let selectedRecord = await WINDOW_API.get_selected_recording();
    return selectedRecord.answer && selectedRecord.isSuccessful;
}


const startRecording = async () => {
    record.setAttribute("disabled", "");
    let inputOff = record_input.hasAttribute("disabled");
    if( await isRecSelected() && inputOff )
        return WINDOW_API.start("record");
    setRecordWarning("Select a recording slot first.")
    record.removeAttribute("disabled");
}


const startSimulate = async () => {
    simulate.setAttribute("disabled", "");
    let selectedSim = await WINDOW_API.get_selected_simulation();
    if( selectedSim.answer && selectedSim.isSuccessful)
        return WINDOW_API.start("simulate")
    setSimWarning("Select a simulation first.")
    simulate.removeAttribute("disabled");
}

const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
    expand.onclick = expandRecordFiles;

    document.getElementById('expand-sims').onclick = expandSimFiles;
    document.getElementById('approve-new').onclick = evaluateNewRecording;
    document.getElementById('settings-rec').onclick = toggleDeleteOption;
    record_input.onfocus = hideDeleteOption;
    document.getElementById('delete-recording').onclick = deleteRecording;
    
    document.getElementById('settings-sim').onclick = toggleDetailsOption;
}



// ==== resolve ===>

function resolveChooseRecordFile (result, filenames) {
    removeSelectOptions();
    if(result==0)
        return createNewRecording();
    selectRecording(filenames[result]);
}

async function resolveChooseSimFile(result, filenames) {
    removeSelectOptions();
    selectSimulation(filenames[result]);
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
    if(answerObj.isSuccessful && answerObj.answer) {
        setRecordFileInput(answerObj.answer)
        let {answer} = await registerRecording(answerObj.answer);
        toggleRecWarning(answer == 'Careful')
    }
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


async function deleteRecording () {
    let recordingName = record_input.value;
    hideDeleteOption()
    let result = await WINDOW_API.deleteRecording(recordingName);
    if (!result.isSuccessful)
        return (result.answer) ? setRecordWarning(`Error: ${result.answer}`) : setRecordWarning(`An internal error occured.`);
    removeSelectOptions();
    setRecordWarning('');
    setSimWarning('');
    put_selected_recording();
    put_selected_simulation();
}

// ============================= Responsiveness =====================================


// Popups disappear on blur
window.addEventListener('mouseup', function(e){
    if (e.target.classList.contains('expand-button-option') || e.target.classList.contains('floating-top-right')) return;
    removeSelectOptions();
})


// ===== record creation ====>

const expandRecordFiles = async () => {
    hideRecordWarning();
    let filenames = await getRecordFiles();
    filenames.unshift("----&#60;new&#62;----");
    let optionButtions = createButtons(filenames, resolveChooseRecordFile, "hover-rec");
    container = createContainer("record");
    addRecordExpansionToDocument(container, optionButtions, "input-field");
    container.focus();
}

const addRecordExpansionToDocument = (container, children, parentID) => {
    children.forEach(element => {
        container.append(element);
    });
    let parent = document.getElementById(parentID);
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
    toggleRecWarning(answer == 'Careful');
    hideDeleteOption();
    hideCheckmark();
}

async function toggleRecWarning(needsWarning){
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

function removeSelectOptions () {
    let elems = document.getElementsByClassName("floating-top-right");
    for(let i=0; i<elems.length; i++){
        let e = elems[i];
        e.parentElement.removeChild(e)
    }
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


// ===== expand sim files ======>


const expandSimFiles = async () => {
    hideSimWarning();
    let filenames = await getSimFiles();
    let options = (filenames.length) ? createButtons(filenames, resolveChooseSimFile, "hover-sim") : [getNoOptionsPanel()];
    container = createContainer("simulate");
    addRecordExpansionToDocument(container, options, "display-field");
    container.focus();
}

const getSimFiles = async () => {
    let data = await WINDOW_API.get_sim_list();
    if (!data.isSuccessful) return [];
    return data.answer;
}

function getNoOptionsPanel() {
    let div = document.createElement('div');
    div.classList.add('empty-field');
    div.innerHTML = 'Nothing to see here :/';
    return div;
}

async function selectSimulation (filename) {
    document.getElementById('display-field').setAttribute("disabled", "");
    let {isSuccessful, answer} = await registerSimulation(filename);
    if(!isSuccessful){
        put_selected_simulation()
        return setSimWarning("Simulation couldn't be selected.");
    }
    setSimFileInput(filename);
    hideSimWarning();
}

async function registerSimulation (filename) {
    return await WINDOW_API.setSimulation(filename);
}

function setSimWarning (text) {
    let p = document.getElementById('warning-simulation');
    p.removeAttribute("hidden");
    p.innerHTML = text;
}

function hideSimWarning () {
    let p = document.getElementById('warning-simulation');
    p.setAttribute("hidden", "");
}


// ======= toggle delete button =====>

async function toggleDeleteOption() {
    let del = document.getElementById('delete-recording');
    hasAttr = del.classList.contains('is-hidden');
    if(!hasAttr || !record_input.hasAttribute('disabled') || !(await isRecSelected()))
        return hideDeleteOption();
    showDeleteOption();
}

function showDeleteOption() {
    let del = document.getElementById('delete-recording');
    let settings = document.getElementById('settings-rec');
    del.classList.remove('is-hidden');
    settings.innerHTML = '&#11176;';
}

function hideDeleteOption () {
    let del = document.getElementById('delete-recording');
    let settings = document.getElementById('settings-rec');
    del.classList.add('is-hidden')
    settings.innerHTML = '&#9881;&#65039';
}


// ====== toggle details button =====>

async function toggleDetailsOption() {
    let details = document.getElementById('show-details');
    let settings = document.getElementById('settings-sim');
    hasAttr = details.classList.contains('is-hidden');
    if (!hasAttr)
        return hideDetailsButton(details, settings);
    showDetailsButton(details, settings);
}

async function hideDetailsButton (details, settings) {
    details.classList.add('is-hidden');
    settings.innerHTML = '&#9881;&#65039';
}

async function showDetailsButton (details, settings) {
    details.classList.remove('is-hidden');
    settings.innerHTML = '&#11176;';
}

// ============================ DOM-Elements =========================================

// ============= RecordOptionButtons ==>

function createButtons (filenames, callbackResultFunc, hoverClass) {
    let buttons = [];
    for(let i=0; i<filenames.length; i++){
        let b = createNewButton(i, filenames, callbackResultFunc, hoverClass);
        buttons.push(b);
    }
    return buttons;
}

const createNewButton = (i, filenames, callbackResultFunc, hoverClass) => {
    let b = document.createElement("button");
    b.classList.add("expand-button-option");
    b.classList.add(hoverClass);
    if(i+1==filenames.length)
        b.classList.add("no-border");
    else
        b.classList.add("expand-option-border");
    b.onclick = () => callbackResultFunc(i, filenames);
    b.innerHTML = filenames[i];
    return b;
}

// ============== Option Container =============>

function createContainer (purpose) {
    let container = document.createElement("div");
    container.id = `${purpose}-select-container`;
    container.classList.add("floating-top-right");
    container.setAttribute("contentEditable", "");
    container.setAttribute("spellcheck", "false");
    return container;
}



main:
{
    addClickEvents();
    put_selected_recording();
    put_selected_simulation();
}
