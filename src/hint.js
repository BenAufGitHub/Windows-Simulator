const {ipcRenderer, contextBridge} = require("electron");

const WINDOW_API = {
    loadMenu: () => ipcRenderer.send("load-menu", null),
    getSettings: async (args) => await ipcRenderer.invoke("get-settings", args),
}

let continueButton = document.getElementById("ok")
let p = document.getElementById("reason")

async function fillParagraph() {
    let reason = await WINDOW_API.getSettings("latestInfo")
    p.innerHTML = reason
}

start:
{
    fillParagraph()
    continueButton.onclick = () => WINDOW_API.loadMenu()
}