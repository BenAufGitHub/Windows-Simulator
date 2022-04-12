const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const select = document.getElementById("videoSelectBtn")
const record = document.getElementById("record")
const getVidBtn = document.getElementById("showOpenWindows")

const WINDOW_API = {
    pause: (application) => ipcRenderer.send("pause", application),
    start: (application) => ipcRenderer.send("start", application),
    resume: (application) => ipcRenderer.send("resume", application),
    getInfo: async (request, body) => ipcRenderer.invoke("request", request, body)
}

const startRecording = () => WINDOW_API.start("record")
const startSimulate = () => WINDOW_API.start("simulate")
const getActiveWins = async () => {
    getVidBtn.disabled = true
    const listWins = async () => {
        const winNames = await WINDOW_API.getInfo("getWinNames", null)
        createSelection(winNames, getVidBtn)
    }
    listWins()
}

const createSelection = (options_arr, parent) => {
    let back = document.createElement("button")
    back.innerHTML = "back"
    back.onclick = () => {
        while(parent.lastElementChild)
                parent.removeChild(parent.lastElementChild)
            setTimeout(() => parent.disabled = false, 20)
    }
    parent.appendChild(back)
    for(let i=0; i<options_arr.length; i++) {
        let option = document.createElement("button")
        option.innerHTML = options_arr[i]
        parent.appendChild(option)
        option.onclick = async () => {
            while(parent.lastElementChild)
                parent.removeChild(parent.lastElementChild)
            setTimeout(() => parent.disabled = false, 20)
            isAccepted = await WINDOW_API.getInfo("setWindow", option.innerHTML)
            console.log(isAccepted)
        }
    }
}

const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
    getVidBtn.onclick = getActiveWins
}

main:
{
    addClickEvents();
}
