const {ipcRenderer, contextBridge} = require("electron");
const querystring = require('querystring');

const WINDOW_API = {
    loadMenu: () => ipcRenderer.send("load-menu", null),
    getSettings: async (args) => await ipcRenderer.invoke("get-settings", args),
}

let continueButton = document.getElementById("ok")
let p = document.getElementById("reason")


async function fillParagraph(lang_pack) {
    let query = querystring.parse(global.location.search);
    let reasonID = query['?data'].toString();
    if(reasonID.length > 1)
        p.innerHTML = `<center>${lang_pack["errors"]["0"]}${reasonID}</center>`;
    else
        p.innerHTML = `<center>${lang_pack["errors"][`${reasonID}`]}</center>`;
}

async function addInnerHTML () {
    lang_pack = await ipcRenderer.invoke('get-lang-pack', null);
    document.getElementById("title").innerHTML = lang_pack["hint"]["title"];
    document.getElementById('ok').innerHTML = lang_pack["hint"]["continue"];
    fillParagraph(lang_pack)
}

start:
{
    continueButton.onclick = () => WINDOW_API.loadMenu();
    addInnerHTML();
}