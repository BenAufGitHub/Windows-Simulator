const {spawn} = require("child_process");
const path = require("path")


let child = null;
let state = null;
const commands = ["record", "simulate", "pause", "resume", "stop"]
const pyPath = './programs/capturer/src/jsBridge.py'


function logMsg(msg, writer) {
    let type = commands.includes(msg) ? "command" : "info"
    console.log(`${writer}: ${msg} \{${type}\}`)
}


/** Writer can be 'main' or 'py' */
const processMsg = (msg, writer) => {
    logMsg(msg, writer)
    if(!commands.includes(msg)) return
    if(execSpecialEvent(msg, writer)) return
    state = msg
    spreadMsg(msg, writer)
}


function spreadMsg (msg, writer) {
    if(writer !== 'py')
        sendPy(msg)
    process.send(msg)
}


/** returns true if a special case was executed */
function execSpecialEvent (msg, writer) {
    if(msg === state)
        return true
    if(msg === 'record' || msg === 'simulate')
        return initPyApplication(msg) == null
    if(msg === 'stop')
        return removeChild(writer) == null
    return false
}


function removeChild(writer) {
    spreadMsg('stop', writer)
    child = null;
    state = null;
}


function initPyApplication (application) {
    startPyApplication(pyPath, application)
    process.send("start")
}


function sendPy (msg) {
    child.stdin.setEncoding("utf-8")
    child?.stdin?.write(`${msg}` + "\n")
}


function startPyApplication(path, args) {
    if(child != null && child.connected) throw "Cannot spawn multiple processes simultaneously"
    child = spawn("python", [path, args])
    initIpcPython();
}


process.on("message", (msg) => processMsg(msg.toString().trim(), 'main'))


function initIpcPython () {
    if(child==null) throw "No child to ipc with"
    child.stdout.on("data", (data) => {
        let msg = data.toString().trim();
        processMsg(msg, 'py')
    })

    child.stderr.on("data", (data) => {
        console.log("An error occured in Python Child:")
        console.log(data.toString())
    })
}