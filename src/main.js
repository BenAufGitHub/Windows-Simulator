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
  latestInfo: null            // will be displayed on .\\hint\\hint.html
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
  mainWindow.once('ready-to-show', (event) => mainWindow.show())
  prepareEventListeners(mainWindow)
  return mainWindow
};


const prepareEventListeners = (window) => {
  window.on("restore", (event, args) => {
    sendCommandToBridge("pause", null)
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
  open(".\\index\\index.html")
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
ipcMain.on("tell-process", (event, args) => sendCommandToBridge(args, null));
ipcMain.on("open-err-win", (event, args) => processSpecialEnd("An error occured, head back to the menu."));
ipcMain.on("change-win", (event, args) => open(`.\\${args}\\${args}.html`))

// ------------------------ reaction to pyBridge -------------------------------------------


function _initProcess (event, args) {
  if(!["record", "simulate"].includes(args)) throw `Illegal Argument ${args}`;
    sendCommandToBridge(args, null)
}


function startProcess () {
  window.minimize();
  settings.state = 'record'
  settings.processState = "going"
  settings.selectedWindow = "recording"
  open(".\\recording\\recording.html");
  window.setSize(400, 250)
}

function resumeProcess () {
  window.minimize()
  if(settings.selectedWindow === 'recording') return;
  settings.selectedWindow = 'recording'
  settings.processState = "going"
  open('.\\recording\\recording.html')
  window.setSize(400, 250)
}


function stopProcess() {
  if(settings.selectedWindow === 'index') return;
  settings.selectedWindow = 'index'
  settings.processState = null
  settings.state = 'menu'
  open(".\\index\\index.html")
  window.restore()
  window.setSize(600, 450)
}


function pauseProcess() {
  if(settings.selectedWindow === 'pause') return;
  settings.selectedWindow = 'pause'
  settings.processState = "idle"
  open(".\\pause\\pause.html")
  window.restore()
  window.setSize(400, 250)
}


function processSpecialEnd(reason) {
  if(settings.selectedWindow === 'hint') return;
  settings.selectedWindow = 'hint'
  settings.processState = null
  settings.latestInfo = reason
  open(".\\hint\\hint.html", null, null)
  window.restore()
  window.setSize(600, 450)
}



ipcMain.handle("get-settings", (event, args) => {
  return settings[args]
})

ipcMain.handle("getWindowResolveInfo", async (event, actionID) => {
  let data = await fsPromises.readFile(`./resources/resolves/${actionID}.json`, { encoding: 'utf8' });
  // TODO might need a safe solution later (try-catch)
  info = JSON.parse(data);
  return info;
})



// ========================= Index JS Options-Requests =============================


ipcMain.handle("set-recording", async (event, filename) => {
  return getRequestNoError(request("set-recording", filename));
})

ipcMain.handle("get-recording", async (e,a) => {
  return getRequestNoError(request("get-recording", null));
})

ipcMain.handle('get-record-list', async (e,a) => {
  return getRequestNoError(request('get-record-list', null));
})

ipcMain.handle('delete-recording', async (event, filename) => {
  return getRequestNoError(request('delete-recording', filename));
})

ipcMain.handle('get-simulation', async (e,a) => {
  return getRequestNoError(request('get-simulation', null));
})

ipcMain.handle('get-simulation-list', async (e,a) => {
  return getRequestNoError(request('get-simulation-list', null));
})

ipcMain.handle('set-simulation', async (event, filename) => {
  return getRequestNoError(request('set-simulation', filename));
})

ipcMain.handle('get-sim-info', async (e,a) => {
  return getRequestNoError(getDetailsList());
})

async function getDetailsList () {
  let simulation = await request('get-simulation', null);
  if(!simulation?.isSuccessful) throw "No simulation-details to display. " + simulation?.answer?.toString();
  let raw_data = await fsPromises.readFile(`./resources/start_capture/${simulation.answer}.json`, { encoding: 'utf8' });
  capture = JSON.parse(raw_data);
  let mapped = capture.map(e => ({"title":e['name'],"process": e["process"]}));
  return {isSuccessful: true, answer: mapped};
}

async function getRequestNoError (req) {
  try {
    return await req;
  }
  catch (e) {
    return {isSuccessful: false, answer: e.toString()};
  }
}


//===========================================================


ipcMain.on("windowResolveResults", (event, answer, actionID) => {
  saveObj = {"result": answer}
  fs.writeFileSync(`./resources/resolves/r${actionID}.json`, JSON.stringify(saveObj))
  sendCommandToBridge("resolveFinished", actionID)
  window.setSize(400, 250)
  window.center()
})

async function resolveIdentifyingWindow(actionID) {
  window.restore()
  window.setSize(830, 950, true)
  window.center()
  window.loadFile("./src/resolving/resolving.html", {"query":{"data": actionID}})
}

ipcMain.on("load-menu", (event, args) => loadMenu())

const loadMenu = () => {
  settings.selectedWindow = 'index'
  settings.state = 'menu'
  open(".\\index\\index.html", 600, 450)
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
    case 'reproducer_resolve_window':
      resolveIdentifyingWindow(arg)
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
  try {
    return await request(arg1, arg2)
  }
  catch {
    return {isSuccessful: False, answer: "Internal failure."}
  }
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
function sendCommandToBridge(command, args) {
  return settings.process?.send(`1  ${command} | ${getFormattedBody(args)}`)
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
