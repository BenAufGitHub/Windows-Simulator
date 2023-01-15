"use strict";

const {ipcRenderer} = require("electron");

let english = document.getElementById('english');
let german = document.getElementById('german');


const sendResult = (language) => ipcRenderer.send("init-with-configs", language)


function blurElems () {
    english.blur()
    german.blur()
}

function disableElems () {
    english.setAttribute("disabled", "");
    german.setAttribute("disabled", "");
}

function setInfo (lang) {
    let p = document.getElementById('info-text');
    p.removeAttribute('hidden');
    if(lang=='en')
        return p.innerHTML = `Hint: Click \u{1F6C8} in the menu to see all necessary information.`
    p.innerHTML = `Hinweis: Klicke \u{1F6C8} im Men&uuml; zum Einsehen aller wichtigen Informationen.`
}

function setInfo2 (lang) {
    let p = document.getElementById('info-text');
    p.removeAttribute('hidden');
    if(lang=='en')
        return p.innerHTML = `'F2' is an important key: Use it to stop your recordings.`
    p.innerHTML = `'F2' ist eine m&auml;chtige Taste: Nutze es, um Aufnahmen zu beenden.`
}

function processResults (lang, source) {
    disableElems();
    source.classList.add("is-loading");
    setInfo(lang)
    setTimeout(()=>setInfo2(lang), 5000);
    setTimeout(()=>sendResult(lang), 10000);
}

function addClickEvents () {
    english.onclick = () => processResults("en", english);
    german.onclick = () => processResults("de", german);
}

function main () {
    blurElems();
    addClickEvents();
}

main()