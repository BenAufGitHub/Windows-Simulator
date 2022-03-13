const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const select = document.getElementById("videoSelectBtn")
const record = document.getElementById("record")

const WINDOW_API = {
    pause: (application) => ipcRenderer.send("pause", application),
    start: (application) => ipcRenderer.send("start", application),
    resume: (application) => ipcRenderer.send("resume", application),
}

const startRecording = () => WINDOW_API.start("record")
const startSimulate = () => WINDOW_API.start("simulate")

const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
}

main:
{
    addClickEvents();
}
