const {spawn} = require("child_process");
let {FormatError, splitRequestMessage, splitAnswerMessage, getFormattedBody, tryGetID} = require("../resources/protocolConversion.js")
const path = require("path");

const pyCall = "./programs/python3.10/python"
const pyMain = './programs/capturer/src/pyCommunicator.py'

// subprogramm coordination in terms of command and state management
let child = null;
let state = "idle";
const states = ["idle", "running", "paused", "stopped"]
const process_cmds = ["pause", "resume", "stop"]
const start_cmds = ["record", "simulate"]
const other_one_way_information = ["resolveFinished"]

// shallow request don't go into the python subprogramm
const mainShallowRequests = ["wait_until_py_initiation"]
// deep requests go into python subprograms
const mainDeepRequests = ["getWinNames", "exit", "showWindow", "spit", "set-recording", "get-recording", "get-record-list", "get-simulation", "get-simulation-list",
"set-simulation"]

// promise-resolving, can be triggered when certain things happen in this process, main can check for these events to complete with awaiting those
const awaitingEvents = new Map()
// ipc handling: when sending a request the promise-resolve is stored under an id, which will be fetched
// if py application answers with that id
const promiseMap = new Map()
let idStack = []


function logMsg(msg, writer) {
    console.log(`${writer}: ${msg}`)
}


// important notes:
// the term 'command' is used for one way operations that do not await an answer
// commands from main refer to telling python programm how to act, see 'process_cmds' or 'start_cmds'
// commands from py indicates which commands python HAS enacted (in correct order), which is bubbled to main to show the user
// note that python can enact commands itself with keyboard input
// race condition/ verifying is handled in python, because the bubbling happens in correct order, there should not be any major problems

// requests expect an answer and await it with a promise
// sending commands to py is a request to see whether they get accepted
// main can also send requests (may be bubbled into python) which can expect a return value


// -------------------------------------- main handling --------------------------------------------------


// here is where messages from main get picked up
process.on("message", (msg) => processMainMsg(msg.toString()))

async function processMainMsg(msg) {
    let [id, arg1, arg2] = splitRequestMessage(msg)
    if(id===1)
        return processMainCommand(arg1)
    processMainRequest(id, arg1, arg2)
}

            // ------------------ Command handling ---------------------------

async function processMainCommand(command) {
    if (isEventEcho(command)) return
    if (isInvalidCommandRequest(command)) return informOfRequestError();
    if (command === "stop")
        state = "stopped"
    try {
        let answer = await requestToPy(command)
        if(!isAcceptedRequest(answer)) return
        processSuccessfulRequest(command, answer[2])
    } catch (e){
        process.send(`1 special-end Following error occured while running: ${e}`)
        try {
            await requestToPy(command)
            updateState("stop")
        } catch {}
    }
}

async function informOfRequestError() {
    let text = "special-end Command could not be processed correctly."
    sendCommandUpwards(text, "main")
}

// request answers: [id, 0/1, answer]
function isAcceptedRequest(requestAnswer) {
    return requestAnswer[1] === 0
}


function isInvalidCommandRequest (req) {
    if(start_cmds.includes(req) && state != 'idle') return true
    if(process_cmds.includes(req) && (state == 'idle' || state == 'stopped') ) return true
    return false
}

// only usuable for methods comming from main, preventing the event at restoring window to fire pause or resume
function isEventEcho (msg) {
    return msg === 'pause' && ["stopped", "idle", "paused"].includes(state) || child == null && msg == 'pause'
}


            // ------------------- request handling ---------------------------


async function processMainRequest(id, req, body) {
    try {
        let result = await handleRequest(req, body)
        process.send(`${id} 0 ${getFormattedBody(result)}`)
    } catch (e) {
        process.send(`${id} 1 ${getFormattedBody(e.toString())}`)
    }
    if(req === 'exit') process.disconnect()
}

async function handleRequest(req, body) {
  if(mainShallowRequests.includes(req))
    return answerShallowRequest(req, body)
  if(mainDeepRequests.includes(req)){
    let data = await requestToPy(req, body)
    if(data[1] !== 0) throw data[2]
    return data[2]
  }
  return null
}

async function answerShallowRequest (req, body) {
    if(req === "wait_until_py_initiation"){
        if(child != null) return
        return await new Promise((resolve, reject) => {
            awaitingEvents.set("wait_until_py_initiation", resolve)
        })
      }
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

function get_rand_id() {
    for(let i=2; i<32; i++){
        if(!idStack.includes(i))
            return i
    }
    throw "Request-Stackoverflow, max is 30"
}


async function requestToPy(req, args) {
    let id = get_rand_id()
    return new Promise((resolve, reject) => {
        saveRequest(id, resolve, reject)
        sendPy(id, req, getFormattedBody(args))
    })
}



// -------------------------------- Python initialization -------------------------------


function startPyApplication() {
    if(child != null && child.connected) throw "Cannot spawn multiple processes simultaneously"
    child = spawn(pyCall, [pyMain])
    initIpcPython();
    awaitingEvents.get("wait_until_py_initiation")?.()
}


function initIpcPython () {
    if(child==null) throw "No child to ipc with"
    child.stdout.on("data", (data) => {
        let msg = data.toString();
        let cmds = msg.split(/\r\n|\n|\r/)
        cmds.forEach(element => {
            if(element?.trim().length)
                processPyMsg(element)
        });
    })

    child.stderr.on("data", (data) => {
        console.log("An error occured in Python Child:")
        console.log(data.toString())
    })
}

function sendPy (id, req, body) {
    child?.stdin?.setEncoding("utf-8")
    child?.stdin?.write(`${id} ${req} | ${body}` + "\n")
}


// -------------------------------- python specifics ------------------------------------

function processPyMsg(msg) {
    try {
        let [id, arg1, arg2] = splitAnswerMessage(msg)
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
    process.send(`1 ${cmd}`)
}

function updateState(command) {
    if(command === "start" || command === "resume")
        state = "running"
    if(command === "pause")
        state = "paused"
    if(command === "stop" || command.indexOf("special-end") != -1)
        state = "idle"
}


function processSuccessfulRequest(command, answer) {
    // process state answers are not important, only accepted or rejected
    if(command === "record")
        return sendCommandUpwards("start", "main")
    if(process_cmds.includes(command))
        return sendCommandUpwards(command, "main")
}



main:
{
    startPyApplication()
}