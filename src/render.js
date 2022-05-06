const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const select = document.getElementById("videoSelectBtn")
const record = document.getElementById("record")
const showWins = document.getElementById("showOpenWindows")

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

const createSelection = (options_arr, parent) => {
    let back = document.createElement("button")
    back.innerHTML = "back"
    back.onclick = () => removeChildrenThenActivate(parent)
    parent.appendChild(back)
    addOptionButtons(options_arr, parent, async (value, parent) => {
        console.log("hu")
        removeChildrenThenActivate(parent)
        isAccepted = await WINDOW_API.getInfo("setWindow", value)
        console.log(isAccepted)
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
    showWins.onclick = getActiveWins
}

main:
{
    styleButton(showWins)
    addClickEvents();
}
