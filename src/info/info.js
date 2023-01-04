"use strict";

const {ipcRenderer} = require('electron');


const getDOM = (id) => document.getElementById(id);

const fillDOM = (id, texts) => {getDOM(id).innerHTML = texts[id]};


function fillTitle (texts) {
    fillDOM("title", texts);
    fillDOM("headline", texts);
}

function fillHandling (texts) {
    fillDOM("handling-title", texts);
    for(let i=1; i<=5; i++) {
        fillDOM(`handling-${i}`, texts);
    }
}

function fillNotes (texts) {
    fillDOM("notes-title", texts);
    for(let i=0; i<texts["notes-p"].length; i++) {
        let li = document.createElement("li");
        li.innerHTML = texts["notes-p"][i] + "<br>";
        getDOM("notes-p").appendChild(li);
    }
}

function fillAbout (texts) {
    fillDOM("about-title", texts);
    for(let i=0; i<texts["general-info"].length; i++) {
        let li = document.createElement("li");
        li.innerHTML = texts["general-info"][i] + "<br>";
        getDOM("general-info").appendChild(li);
    }
}

async function addInnerHTML () {
    let langPack = await ipcRenderer.invoke("get-lang-pack", null);
    let texts = langPack["info"];

    fillTitle(texts);
    fillHandling(texts);
    fillNotes(texts);
    fillAbout(texts);
}


function confBack () {
    let back = document.getElementById('back');
    back.onclick = () => ipcRenderer.send('change-win', 'index');
}


main:
{
    addInnerHTML();
    confBack();
}