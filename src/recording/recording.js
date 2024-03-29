const {ipcRenderer} = require("electron")

const WIN_API = {
    pause: () => ipcRenderer.send("tell-process", "pause"),
    stop: () => ipcRenderer.send("tell-process", "stop"),
    loadErr: () => ipcRenderer.send("open-err-win", null)
}

const btn = document.getElementById("pause")
const reportError = () => {
    WIN_API.stop();
    setTimeout(WIN_API.loadErr, 1000)
}

btn.onclick = () => {
    WIN_API.pause();
    btn.classList.add("is-loading");
    btn.classList.add("is-outlined");

    setTimeout(reportError, 5000);
}


async function addInnerHTML () {
    let lang_pack = await ipcRenderer.invoke('get-lang-pack', null);
    document.getElementById('title').innerHTML = lang_pack["recording"]["title"];
    document.getElementById('pause').innerHTML = lang_pack["recording"]["pause"];
}

addInnerHTML();