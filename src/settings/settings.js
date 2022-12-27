"use strict";

const {ipcRenderer} = require('electron');

function saveSettings(lang, screenshots, checkWins) {
    ipcRenderer.send('save-settings', lang, screenshots, checkWins)
}


function closeSettings () {
    ipcRenderer.send('kill-settings', null);
}

function main () {
    document.getElementById('save-back').onclick = saveAndBack;
    setupButtonCMDS();
    controlInputs();
}

async function controlInputs () {
    let configs = await ipcRenderer.invoke('get-app-settings', null);
    preToggleInputs(configs);
}


function preToggleInputs (configs) {
    document.getElementById('lang-in').checked = (configs["customizable"]["language"] == 'german')
    document.getElementById('toggle-screen').checked = configs["customizable"]["takeScreenshots"]
    document.getElementById('toggle-check').checked = configs["customizable"]["controlWindows"]
}


const getSelectedLang = () => {
    if(document.getElementById('lang-in').checked)
        return 'german';
    return 'english';
}

const isToggleScreen = () => {
    return document.getElementById('toggle-screen').checked;
}

const isToggleCheck = () => {
    return document.getElementById('toggle-check').checked;
}

function saveAndBack () {
    let lang = getSelectedLang();
    let screenshots = isToggleScreen();
    let checkWins = isToggleCheck();
    saveSettings(lang, screenshots, checkWins);
    closeSettings();
}

function setupButtonCMDS () {
    document.getElementById('del-saves').onclick = () => deleteSaves();
    document.getElementById('del-cache').onclick = () => deleteCache();
}

/* state:*/
function toggleButtons(activate) {
    document.getElementById('del-saves').disabled = !activate;
    document.getElementById('del-cache').disabled = !activate;
}

async function deleteSaves () {
    toggleButtons(false);
    let answer = await ipcRenderer.invoke('delete-all-saves', null);
    toggleButtons(true);
}

async function deleteCache () {
    toggleButtons(false);
    let answer = await ipcRenderer.invoke('delete-cache', null);
    toggleButtons(true);
}

window.onbeforeunload = () => {
    closeSettings();
}


main:
{
    main()
}
