const {ipcRenderer, contextBridge} = require("electron")

const WINDOW_API = {
    send: args => ipcRenderer.send("tell-process", args),
    getSettings: async (args) => await ipcRenderer.invoke("get-settings", args),
}

const changeTitle = async () => {
    const title = document.querySelector("title")
    title.innerHTML = await WINDOW_API.getSettings("pause-state")
}

const sendFromButton = (command) => {
    disableButtons()
    WINDOW_API.send(command)
}

const disableButtons = () => {
    resumeBtn.setAttribute("disabled", true)
    stopBtn.setAttribute("disabled", true)
}

changeTitle()
const resumeBtn = document.getElementById("resume");
const stopBtn = document.getElementById("stop");

resumeBtn.onclick = () => sendFromButton("resume")
stopBtn.onclick = () => sendFromButton("stop")

