const {ipcRenderer, contextBridge} = require("electron")
const fs = require('fs')

const simulate = document.getElementById("simulate")
const select = document.getElementById("videoSelectBtn")
const record = document.getElementById("record")
const showWins = document.getElementById("showOpenWindows")
const label = document.getElementById("checkBoxLabel");
const checkBox = document.getElementById("maximizeCheckbox");

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

const startRecording = () => WINDOW_API.start("record")
const startSimulate = () => WINDOW_API.start("simulate")
const getActiveWins = async () => {
    showWins.disabled = true
    const listWins = async () => {
        const winNames = await WINDOW_API.getInfo("getWinNames", null)
        createSelection(winNames, showWins)
    }
    listWins()
}

const fillLabelWithWindowName = async () => {
    const winName = await WINDOW_API.getInfo("getWindow", null)
    if(!winName) return label.innerHTML = "No window selected"
    label.innerHTML = "maximize '" + winName + "'"
}

const createSelection = (options_arr, parent) => {
    let back = document.createElement("button")
    back.innerHTML = "back"
    back.onclick = () => removeChildrenThenActivate(parent)
    parent.appendChild(back)
    addOptionButtons(options_arr, parent, async (value, parent) => {
        removeChildrenThenActivate(parent)
        isAccepted = await WINDOW_API.getInfo("setWindow", value)
        if(isAccepted)
            fillLabelWithWindowName()
    })
}

const addOptionButtons = (options, parent, callback) => {
    options.forEach((element) => {
        let option = document.createElement("button")
        option.innerHTML = element
        parent.appendChild(option)
        option.onclick = () => callback(element, parent)
    })
}

const removeChildrenThenActivate = (button) => {
    while(button.lastElementChild)
        button.removeChild(button.lastElementChild)
    setTimeout(() => button.disabled = false, 20)
}

const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
    showWins.onclick = getActiveWins;
}

const prepareOptions = () => {
    fillLabelWithWindowName();
    updateCheckBox();
    checkBox.onchange = () => {
        let session_data = JSON.parse(fs.readFileSync('./resources/session_data.json'));
        session_data.checkbox = checkBox.checked;
        fs.writeFileSync('./resources/session_data.json', JSON.stringify(session_data));
    }
}

const updateCheckBox = () => {
    let session_data = JSON.parse(fs.readFileSync('./resources/session_data.json'));
    checkBox.checked = session_data.checkbox;
}

main:
{
    styleButton(showWins)
    prepareOptions();
    addClickEvents();
}
