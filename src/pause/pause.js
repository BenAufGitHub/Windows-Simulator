const {ipcRenderer, contextBridge} = require("electron")

const WINDOW_API = {
    send: args => ipcRenderer.send("tell-process", args),
    getSettings: async (args) => await ipcRenderer.invoke("get-settings", args),
}

const sendFromButton = (command) => {
    disableButtons()
    WINDOW_API.send(command)
}

const disableButtons = () => {
    resumeBtn.setAttribute("disabled", true)
    stopBtn.setAttribute("disabled", true)
}

const resumeBtn = document.getElementById("resume");
const stopBtn = document.getElementById("stop");

resumeBtn.onclick = () => sendFromButton("resume")
stopBtn.onclick = () => sendFromButton("stop")


const get = (id) => {
    return document.getElementById(id);
}


async function addInnerHTML () {
    let lang_pack = await ipcRenderer.invoke("get-lang-pack", null);
    get("title").innerHTML = lang_pack["pause"]["title"];
    get("instructions").innerHTML = `<strong>${lang_pack["pause"]["instructions"]}</strong>`;
    get("resume").innerHTML = lang_pack["pause"]["resume"];
    get("stop").innerHTML = lang_pack["pause"]["stop"];
}

addInnerHTML();