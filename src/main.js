const { app, BrowserWindow, ipcMain, remote} = require('electron');
const { fork } = require("child_process")
const fs = require("fs")
const fsPromises = require("fs/promises")
let {FormatError, splitAnswerMessage, splitRequestMessage, getFormattedBody, tryGetID} = require("../resources/protocolConversion.js")
const path = require('path');
let window = null;

const promiseMap = new Map()
let idStack = []

const settings = {
  state: "menu",              // menu / recording / simulating
  processState: null,         // going / idle
  selectedWindow: 'index',    // index / recording / pause
  process: null,              // the pyBridge
  latestInfo: null            // will be displayed on hint.html
}


function configureSetup() {
  app.disableHardwareAcceleration()
}

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  // eslint-disable-line global-require
  app.quit();
}


function createWindow () {
  const mainWindow = new BrowserWindow({
    width: 600,
    height: 450,
    webPreferences: {
      openDevTools: true,
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
    }
  });
  mainWindow.webContents.openDevTools();
  prepareEventListeners(mainWindow)
  return mainWindow
};


const prepareEventListeners = (window) => {
  window.on("restore", (event, args) => {
    sendCommandToBridge("pause")
  })
}


const open = (filename) => {
  window = window ? window : createWindow()
  window.loadFile(path.join(__dirname, filename))
  return window
};


const openURL = (url) => {
  window.loadURL(url)
}


const createFirstWindow = () => {
  open("index.html")
}


// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.on('ready', atStart);

async function atStart() {
  let data = await request("wait_until_py_initiation")
  if(!data.isSuccessful) console.log("waiting for python unsuccessful, reason:", data.answer)
  createFirstWindow()
}

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});


app.on('activate', () => {
  // On OS X it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});


// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and import them here.
// require('@electron/remote/main').initialize()

// In the main process.

// ------------------------- ipcMain listeners -----------------------------------------

ipcMain.on("start", _initProcess)
ipcMain.on("tell-process", (event, args) => sendCommandToBridge(args))
ipcMain.on("open-err-win", (event, args) => processSpecialEnd("An error occured, head back to the menu."))

// ------------------------ reaction to pyBridge -------------------------------------------


function _initProcess (event, args) {
  if(!["record", "simulate"].includes(args)) throw `Illegal Argument ${args}`;
    sendCommandToBridge(args)
}


function startProcess () {
  window.minimize();
  settings.state = 'record'
  settings.processState = "going"
  settings.selectedWindow = "recording"
  open("recording.html");
}

function resumeProcess () {
  window.minimize()
  if(settings.selectedWindow === 'recording') return;
  settings.selectedWindow = 'recording'
  settings.processState = "going"
  open('recording.html')
}


function stopProcess() {
  if(settings.selectedWindow === 'index') return;
  settings.selectedWindow = 'index'
  settings.processState = null
  settings.state = 'menu'
  open("index.html")
  window.restore()
}


function pauseProcess() {
  if(settings.selectedWindow === 'pause') return;
  settings.selectedWindow = 'pause'
  settings.processState = "idle"
  open("pause.html")
  window.restore()
}


function processSpecialEnd(reason) {
  if(settings.selectedWindow === 'hint') return;
  settings.selectedWindow = 'hint'
  settings.processState = null
  settings.latestInfo = reason
  open("hint.html")
  window.restore()
}



ipcMain.handle("get-settings", (event, args) => {
  return settings[args]
})

ipcMain.handle("getWindowResolveInfo", async (event, args) => {
  let data = await fsPromises.readFile('./resources/window_unresolved.json', { encoding: 'utf8' });
  // TODO might need a safe solution later (try-catch)
  info = JSON.parse(data);
  return info;
})

ipcMain.handle("set-recording", async (event, filename) => {
  try {
    return await request("set-recording", filename);
  }
  catch{
    return {isSuccessful: false}
  }
})

ipcMain.on("windowResolveResults", (event, args) => {
  saveObj = {"selection": args}
  fs.writeFileSync("./resources/window_resolved.json", JSON.stringify(saveObj))
  sendCommandToBridge("resolveFinished", null)
})

function resolveIdentifyingWindow() {
  window.restore()
  open("resolving.html")
  // TODO
  // read file
  // make a new window
  // communicate with window
  // send response to py
}

ipcMain.on("load-menu", (event, args) => loadMenu())

const loadMenu = () => {
  settings.selectedWindow = 'index'
  settings.state = 'menu'
  open("index.html")
}


/** --------------------- python bridge ---------------------------------------- */


function startPythonBridge () {
  settings.process = fork('./programs/pyBridge.js', ['args'], {
    stdio: ['pipe', 'pipe', 'pipe', 'ipc']
  });
  settings.process.stdout.pipe(process.stdout)
  settings.process.stderr.pipe(process.stderr)
}


function configurePythonBridge () {
  settings.process?.on("message", (m) => {
    let msg = m.toString()
    let [id, arg1, arg2] = splitAnswerMessage(msg)
    if(id===1) return processCommandFromBridge(arg1)
    processAnswerFromBridge(id, arg1, arg2)
  })
}

function processAnswerFromBridge(id, errorcode, body) {
  const promise = retrive_request(id)
  answer_obj = {
    isSuccessful: errorcode==0,
    id: id,
    answer: body,
  }
  promise.res(answer_obj)
}

function processCommandFromBridge(command) {
  switch (command) {
    case 'reproducer_resolve_window':
      resolveIdentifyingWindow()
      break;
    case 'resume':
      resumeProcess()
      break;
    case 'pause':
      pauseProcess()
      break;
    case 'stop':
      stopProcess()
      break;
    case 'start':
      startProcess()
      break;
    default:
      processSecondaryCommandFromBridge(command)
  }
}

function processSecondaryCommandFromBridge(command) {
  let words = command.split(" ")
  let cmd = words[0]
  let argArray = words.slice(1, cmd.length)
  let arg = argArray.join(" ")
  switch (cmd) {
    case 'special-end':
      processSpecialEnd(arg);
      break;
    default:
      console.log(`Command from bridge not available: ${command}`)
  }
}

// -------------------------------------- mapping IDs -------------------------------------------------

function saveRequest(id, resolveFunc, rejectFunc) {
  promiseMap.set(id, {res: resolveFunc, rej: rejectFunc})
  idStack.push(id)
}

function retrive_request(id) {
  let obj = promiseMap.get(id)
  promiseMap.delete(id)
  idStack.shift()
  return obj
}

function denyEarliestUnresolved(){
  if(idStack.length == 0) return
  id = idStack[0]
  retrive_request(id).res([id, '1', 'error'])
}


function get_rand_id() {
  for(let i=2; i<32; i++){
      if(!idStack.includes(i))
          return i
  }
  throw "Request-Stackoverflow, max is 30"
}

// ------------------------------------------------------ requesting -------------------------------------------------

ipcMain.handle("request", async (event, arg1, arg2) => {
  let data = await request(arg1, arg2)
  if (!data.isSuccessful) return null
  return data.answer
})

async function request(req, args) {
  let id = get_rand_id()
  return new Promise((resolve, reject) => {
      saveRequest(id, resolve, reject)
      sendRequestToBridge(id, req, getFormattedBody(args))
  })
}

async function sendRequestToBridge(id, req, body) {
  settings.process?.send(`${id} ${req} | ${body}`)
}

// can currently command record, simulate, pause, resume, stop, resolveFinished
function sendCommandToBridge(command) {
  settings.process?.send(`1 ${command}`)
}


process.on("exit", (code) => {
  func = async function () {
    await request("exit")
    settings.process?.disconnect()
  }
  func()
})


main:
{
  configureSetup();
  startPythonBridge();
  configurePythonBridge();
}



/**
 * 
 
ipcMain.on("showVids", (event, args) => {
  console.log("bin im fernsehen")
  const {desktopCapturer, Menu} = require("electron")

  async function getVideoSources() {
    const inputSources = await desktopCapturer.getSources({
      types: ['window', 'screen']
    });
  
    const videoOptionsMenu = Menu.buildFromTemplate(
      inputSources.map(source => {
        return {
          label: source.name,
          click: () => selectSource(source)
        };
      })
    );
  
  
    videoOptionsMenu.popup();
  }
  getVideoSources()
})

function sendScreenNames () {
  const { desktopCapturer } = require('electron')

  return desktopCapturer.getSources({ types: ['window', 'screen'] }).then(async sources => {
      for (const source of sources) {
        console.log(source)
        if (source.name === 'Electron') {
          mainWindow.webContents.send('SET_SOURCE', source.id)
          return
        }
      }
    })
}


 */