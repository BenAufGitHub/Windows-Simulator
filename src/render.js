const {ipcRenderer, contextBridge} = require("electron")

const simulate = document.getElementById("simulate")
const record = document.getElementById("record")

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



const addClickEvents = () => {
    record.onclick = startRecording;
    simulate.onclick = startSimulate;
}



main:
{
    addClickEvents();
}
