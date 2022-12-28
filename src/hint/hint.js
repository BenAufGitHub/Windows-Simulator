const {ipcRenderer, contextBridge} = require("electron");

const WINDOW_API = {
    loadMenu: () => ipcRenderer.send("load-menu", null),
    getSettings: async (args) => await ipcRenderer.invoke("get-settings", args),
}

let continueButton = document.getElementById("ok")
let p = document.getElementById("reason")

async function fillParagraph() {
    let reason = await WINDOW_API.getSettings("latestInfo")
    p.innerHTML = `<center>${reason}</center>`;
}

async function addInnerHTML () {
    lang_pack = await ipcRenderer.invoke('get-lang-pack', null);
    document.getElementById("title").innerHTML = lang_pack["hint"]["title"];
    document.getElementById('ok').innerHTML = lang_pack["hint"]["continue"];
}

start:
{
    fillParagraph();
    continueButton.onclick = () => WINDOW_API.loadMenu();
    addInnerHTML();
}