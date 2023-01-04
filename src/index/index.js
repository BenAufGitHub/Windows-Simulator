const {ipcRenderer, contextBridge} = require("electron")


const simulate = document.getElementById("simulate")
const record = document.getElementById("record")
const expand = document.getElementById("expand-saves");
let record_input = document.getElementById("save-input");


// ============================= functionality ===================================


let lang_pack = null;


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
    get_sim_info: async () => ipcRenderer.invoke('get-sim-info', null),
    setSimulation: async (filename) => ipcRenderer.invoke('set-simulation', filename),

    getLangPack: async () => ipcRenderer.invoke('get-lang-pack', null)
}


async function getText(key)  {
    if(!lang_pack)
        lang_pack = (await WINDOW_API.getLangPack())["index"];
    return lang_pack[key]
}


const standardRecordText = async () => getText('std-rec-text');
const standardSimulationText = async () => getText('std-sim-text');


const isRecSelected = async () => {
    let selectedRecord = await WINDOW_API.get_selected_recording();
    return selectedRecord.answer && selectedRecord.isSuccessful;
}


const startRecording = async () => {
    record.setAttribute("disabled", "");
    let inputOff = record_input.hasAttribute("disabled");
    if( await isRecSelected() && inputOff )
        return WINDOW_API.start("record");
    setRecordWarning(await getText('rec-warning-1')) 
    record.removeAttribute("disabled");
}


const startSimulate = async () => {
    simulate.setAttribute("disabled", "");
    let selectedSim = await WINDOW_API.get_selected_simulation();
    if( selectedSim.answer && selectedSim.isSuccessful)
        return WINDOW_API.start("simulate")
    setSimWarning(await getText('sim-warning-1'))
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
    addRecordInputEnterEvent();
    document.getElementById('delete-recording').onclick = deleteRecording;
    
    document.getElementById('settings-sim').onclick = toggleDetailsOption;
    document.getElementById('show-details').onclick = expandDetails;
    document.getElementById('button-to-settings').onclick = () => ipcRenderer.send("show-settings", null);
    document.getElementById('button-to-info').onclick = () => ipcRenderer.send("change-win", "info");
}


function addRecordInputEnterEvent () {
    record_input.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            if(record_input.disabled) return;
            evaluateNewRecording();
        }
   });
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


async function evaluateNewRecording() {
    result = record_input.value;
    if(await warn_if_not_valid(result)) return;
    hideRecordWarning();
    selectRecording(result.trim());
}

async function warn_if_not_valid(save) {
    save = save.trim();
    if(save.length <4 || save.length>20){
        setRecordWarning(await getText("rec-warning-2"));
        return true;
    }
    regex = /^[0-9a-zA-Z-_ ]+$/g
    if(!save.match(regex)){
        setRecordWarning(await getText("rec-warning-3"));
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
        setRecordFileInput(await standardRecordText())
}

async function put_selected_simulation () {
    let answerObj = await WINDOW_API.get_selected_simulation()
    if(answerObj.isSuccessful && answerObj.answer)
        setSimFileInput(answerObj.answer)
    else
        setSimFileInput(await standardSimulationText())
}


async function deleteRecording () {
    let recordingName = record_input.value;
    hideDeleteOption();
    hideDetailsButton();

    // delete shown details table if it is associated with this recording 
    if (recordingName == (await WINDOW_API.get_selected_simulation()).answer)
        clearDetails();

    let result = await WINDOW_API.deleteRecording(recordingName);
    if (!result.isSuccessful)
        return (result.answer) ? setRecordWarning(`${await getText("rec-warning-4")}: ${result.answer}`) : setRecordWarning(await getText("rec-warning-5"));

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
    filenames.unshift(`--------&#60; ${await getText("new-rec")} &#62;--------`); // new-rec
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
        return setRecordWarning(await getText("rec-warning-6"));
    }
    setRecordFileInput(filename);
    toggleRecWarning(answer == 'Careful');
    hideDeleteOption();
    hideCheckmark();
}

async function toggleRecWarning(needsWarning){
    if(needsWarning)
        setRecordWarning(await getText("rec-warning-7"));
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
    let options = (filenames.length) ? createButtons(filenames, resolveChooseSimFile, "hover-sim") : [await getNoOptionsPanel()];
    container = createContainer("simulate");
    addRecordExpansionToDocument(container, options, "display-field");
    container.focus();
}

const getSimFiles = async () => {
    let data = await WINDOW_API.get_sim_list();
    if (!data.isSuccessful) return [];
    return data.answer;
}

async function getNoOptionsPanel() {
    let div = document.createElement('div');
    div.classList.add('empty-field');
    let text = await getText('no-options');
    div.innerHTML = text;
    return div;
}

async function selectSimulation (filename) {
    document.getElementById('display-field').setAttribute("disabled", "");
    let {isSuccessful, answer} = await registerSimulation(filename);
    hideDetailsButton();
    clearDetails();
    if(!isSuccessful){
        put_selected_simulation()
        return setSimWarning((await getText("sim-warning-2")) + answer);
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
    hasAttr = details.classList.contains('is-hidden');
    if (!hasAttr)
        return hideDetailsButton();
    let currentSim = await WINDOW_API.get_selected_simulation();
    if(currentSim?.isSuccessful && currentSim.answer)
        showDetailsButton();
}

async function hideDetailsButton () {
    let details = document.getElementById('show-details');
    let settings = document.getElementById('settings-sim');
    details.classList.add('is-hidden');
    settings.innerHTML = '&#9881;&#65039';
}

async function showDetailsButton () {
    let details = document.getElementById('show-details');
    let settings = document.getElementById('settings-sim');
    details.classList.remove('is-hidden');
    settings.innerHTML = '&#11176;';
}


async function expandDetails () {
    toggleDetailsOption();
    let sim = await WINDOW_API.get_selected_simulation()
    if (!sim?.answer) return setSimWarning(await getText('no-details'))

    let content = await WINDOW_API.get_sim_info();
    if (!content.isSuccessful)
        return (content.answer) ? setSimWarning(`${await getText('sim-warning-3')}${content.answer}`) :
                            setSimWarning(await getText('sim-warning-4'));
    showTable(content.answer)
}

async function showTable (list) {
    clearDetails();
    if(!list.length)
        list.push({"title":"-", "process":"-"})
    let div = document.createElement('div');
    let h4 = document.createElement('h4');
    let table = await createDetailsTable(list);

    div.id = 'details-table';
    h4.innerHTML = await getText('h4');
    h4.style['text-decoration'] = "underline";

    div.appendChild(h4);
    div.appendChild(table);
    document.getElementById('details-wrapper').appendChild(div);
}


const clearDetails = () => {
    document.getElementById('details-wrapper').innerHTML = '';
}


async function createDetailsTable (content) {
    let table = createTable();
    let tbody = document.createElement('tbody')
    let header = await createTableHeader();
    tbody.appendChild(header);
    content.forEach((e) => tbody.appendChild(getDetailsRow(e)), content);
    table.appendChild(tbody);
    return table;
}


// ============================ DOM-Elements =========================================

// ============= Details Table ========>


function createTable () {
    return document.createElement('table');
}


async function createTableHeader () {
    let row = document.createElement('tr');
    let title = document.createElement('th');
    let process = document.createElement('th');

    title.innerHTML = `<center>${await getText('table-title')}</center>`;
    process.innerHTML = `<center>${await getText('table-process')}</center>`
    process.style["wordBreak"] = "break-word";
    row.appendChild(title);
    row.appendChild(process);
    return row;
}


function getDetailsRow (element) {
    let row = document.createElement('tr');
    let title = document.createElement('td');
    let process = document.createElement('td');

    title.innerHTML = `<center>${element["title"]}</center>`;
    process.innerHTML = `<center>${element["process"]}</center>`;
    row.appendChild(title);
    row.appendChild(process);
    return row;
}



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


async function add_innerHTML () {
    document.getElementById('title').innerHTML = await getText('title');
    document.getElementById('record').innerHTML = await getText('record');
    document.getElementById('simulate').innerHTML = await getText('simulate');
    document.getElementById('save-slot-label').innerHTML = await getText('save-select-label');
    document.getElementById('delete-recording').innerHTML = await getText('delete');
    document.getElementById('sim-select-label').innerHTML = await getText('sim-select-label');
    document.getElementById('show-details').innerHTML = await getText('details');
}


main:
{
    addClickEvents();
    put_selected_recording();
    put_selected_simulation();
    add_innerHTML();
}
