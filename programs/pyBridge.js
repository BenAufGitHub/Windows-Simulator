const {spawn} = require("child_process");
let {FormatError, splitPyMessage, getFormattedBody, tryGetID} = require("./protocolConversion.js")
const path = require("path");


let child = null;
let state = "idle";
const states = ["idle", "running", "paused", "stopped"]
const process_cmds = ["pause", "resume", "stop"]
const start_cmds = ["record", "simulate"]
const main_requests = ["wait_until_completion"]
const pyPath = './programs/capturer/src/pyCommunicator.py'

const promiseMap = new Map()
let idStack = []


function logMsg(msg, writer) {
    console.log(`${writer}: ${msg}`)
}


// ---------------------------------- mapping ids ---------------------------------------


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


// -------------------------------- python specifics ------------------------------------

function processPyMsg(msg) {
    try {
        let [id, arg1, arg2] = splitPyMessage(msg)
        if(id < 2) {
            if(id === 1)
                return processPyCommand(arg1)
            return console.log(`Pyinfo: ${arg1}`)
        }
        processPyAnswer(id, arg1, arg2)
    } catch (e) {
        if(!(e instanceof FormatError)) throw e
        let id = tryGetID(msg)
        if(id==-1) return
        if(id<2) return console.log(`Faulty py-msg, can't convert: ${msg}`)
        processPyAnswer(id, 1, "conversion failed")
    }
}


// needs to be put with promise so that commands are stacked in the correct order by the event loop if multiple messages are processed in one pass
// since answers are promises and commands would not be, these would execute the commands first (as described above)
async function processPyCommand(content) {
    await new Promise((resolve) => resolve(0))
    sendCommandUpwards(content, "py")
}

function processPyAnswer(id, state,  content) {
// DONT FORGET TO NOTIFY IF REQUESTS ARENT ORDERLY ANSWERED, TRY TO DO SO WITH QUEUE -> MAYBE SHIFT TO A WAIT QUEUE IF UNORERLY EXECUTED
    const promise = retrive_request(id)
    promise.res([id, state, content])
}



// -------------------------------- Bubbling upwards ------------------------------------

function sendCommandUpwards (cmd, caller) {
    updateState(cmd)
    logMsg(cmd, caller)
    process.send(cmd)
}

function updateState(command) {
    if(command === "start" || command === "resume")
        state = "running"
    if(command === "pause")
        state = "paused"
    if(command === "stop")
        state = "idle"
}


function processSuccessfulRequest(command, answer) {
    // process state answers are not important, only accepted or rejected
    if(start_cmds.includes(command))
        return sendCommandUpwards("start", "main")
    if(process_cmds.includes(command))
        return sendCommandUpwards(command, "main")
    handleRequestsWithAnswers(command, answer)
}


function handleRequestsWithAnswers(command, answer) {
    // TODO when main-invoking is introced
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

process.on("message", (msg) => processMainMsg(msg.toString().trim()))


async function request(req, args) {
    let id = get_rand_id()
    return new Promise((resolve, reject) => {
        saveRequest(id, resolve, reject)
        sendPy(id, req, getFormattedBody(args))
    })
}

function sendPy (id, req, body) {
    child?.stdin?.setEncoding("utf-8")
    child?.stdin?.write(`${id} ${req} | ${body}` + "\n")
}

async function processMainMsg(msg) {
    if (isEventEcho(msg)) return
    if (isInvalidRequest(msg)) throw `${msg} (main) not accepted`
    if (msg === "stop")
        state = "stopped"
    let answer = await request(msg)
    if(!isAcceptedRequest(answer))
        return
    processSuccessfulRequest(msg, answer[2])
}


// request answers: [id, 0/1, answer]
function isAcceptedRequest(requestAnswer) {
    return requestAnswer[1] === 0
}


function isInvalidRequest (req) {
    if(start_cmds.includes(req) && state != 'idle') return true
    if(process_cmds.includes(req) && (state == 'idle' || state == 'stopped') ) return true
    return false
}


// only usuable for methods comming from main, preventing the event at restoring window to fire pause or resume
function isEventEcho (msg) {
    return msg === 'pause' && ["stopped", "idle", "paused"].includes(state) || child == null && msg == 'pause'
}


main:
{
    startPyApplication()
}