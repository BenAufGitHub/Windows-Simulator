const { app, BrowserWindow, ipcMain, remote} = require('electron');
const { fork } = require("child_process")
const path = require('path');
let window = null;

const settings = {
  state: "menu",              // menu / recording / simulating
  processState: null,         // going / idle
  selectedWindow: 'index',    // index / recording / pause
  process: null,              // the pyBridge
}


function configureSetup() {
  app.disableHardwareAcceleration()
}

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require('electron-squirrel-startup')) {
  // eslint-disable-line global-require
  app.quit();
}


function createWindow (filename) {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
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
    sendToChild(null, "pause")
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
app.on('ready', createFirstWindow);


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
ipcMain.on("tell-process", sendToChild)

/** args: 'pause', 'resume' or 'stop' */
function sendToChild (event, args) {
  if(settings?.process)
    settings.process.send(args)
}


// ------------------------ reaction to pyBridge -------------------------------------------


function _initProcess (event, args) {
  if(!["record", "simulate"].includes(args)) throw `Illegal Argument ${args}`;
  if (settings.process)
    settings.process.send(args)
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
}


function pauseProcess() {
  if(settings.selectedWindow === 'pause') return;
  settings.selectedWindow = 'pause'
  settings.processState = "idle"
  open("pause.html")
  window.restore()
}



ipcMain.handle("get-settings", (event, args) => {
  return settings[args]
})


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
    switch (m) {
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
        console.log(`A message from child: ${m}`)
    }
  })
}



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