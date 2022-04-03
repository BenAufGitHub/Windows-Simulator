const {spawn} = require("child_process");
const path = require("path")


let child = null;
let state = null;
const commands = ["record", "simulate", "pause", "resume", "stop"]
const pyPath = './programs/capturer/src/pyCommunicator.py'


function logMsg(msg, writer) {
    let type = commands.includes(msg) ? "command" : "info"
    console.log(`${writer}: ${msg}`)
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
    if(isEventEcho(msg, writer))
        return true
    return false
}


// -------------------------------- python specifics ------------------------------------

function processPyMsg(msg) {
    let words = msg.split(" ")
    if(words.length < 2 || !isNan(words[0]))
        return console.log("Message from py invalid: ", msg)
    let content = words.slice(1, words.length).join(' ')
    if(words[0] == 0)
        console.log(`Pyinfo: ${content}`)
    if(words[0] == 1)
        processPyCommand(parseInt(words[0]), content)
    processPyAnswer(parseInt(words[0]), content)
}


function processPyCommand(id, content) {

}

function processPyAnswer(id, content) {

}


function sendPy (msg) {
    child?.stdin?.setEncoding("utf-8")
    child?.stdin?.write(`${msg}` + "\n")
}


// -------------------------------- Python initialization -------------------------------


function startPyApplication() {
    if(child != null && child.connected) throw "Cannot spawn multiple processes simultaneously"
    child = spawn("py", [pyPath])
    initIpcPython();
}


function initIpcPython () {
    if(child==null) throw "No child to ipc with"
    child.stdout.on("data", (data) => {
        let msg = data.toString().trim();
        let cmds = msg.split(/\r\n|\n|\r/)
        cmds.forEach(element => {
            processPyMsg(element)
        });
    })

    child.stderr.on("data", (data) => {
        console.log("An error occured in Python Child:")
        console.log(data.toString())
    })
}


// -------------------------------------- main handling --------------------------------------------------

process.on("message", (msg) => processMsg(msg.toString().trim(), 'main'))


function isEventEcho (msg, writer) {
    return writer === 'main' && msg === 'pause' && state === 'stop' || child == null && msg == 'pause'
}


main:
{
    startPyApplication()
}