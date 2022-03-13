const {ipcRenderer} = require("electron")

const WIN_API = {
    pause: () => ipcRenderer.send("tell-process", "pause")
}

const btn = document.getElementById("pause")
btn.onclick = WIN_API.pause