const {spawn} = require("child_process");
const path = require("path");


let child = null;
let state = "idle"; // STATE APPORVAL STILL RIGHT? CHECK FOR FAULTY REQUESTS!!
const states = ["idle", "running", "paused", "stopped"] // stopped necessary?
const process_cmds = ["pause", "resume", "stop"]
const start_cmds = ["record", "simulate"]
const pyPath = './programs/capturer/src/pyCommunicator.py'

const promise_map = new Map()
let id_stack = []


function logMsg(msg, writer) {
    console.log(`${writer}: ${msg}`)
}


// ---------------------------------- mapping ids ---------------------------------------


function save_request(id, resolveFunc, rejectFunc) {
    promise_map.set(id, {res: resolveFunc, rej: rejectFunc})
    id_stack.push(id)
}

function retrive_request(id) {
    let obj = promise_map.get(id)
    promise_map.delete(id)
    id_stack.shift()
    return obj
}

function denyEarliestUnresolved(){
    if(id_stack.length == 0) return
    id = id_stack[0]
    retrive_request(id).res([id, '1', 'error'])
}


function get_rand_id() {
    for(let i=2; i<32; i++){
        if(!id_stack.includes(i))
            return i
    }
    throw "Request-Stackoverflow, max is 30"
}


// -------------------------------- python specifics ------------------------------------

function processPyMsg(msg) {
    let words = msg.split(" ")
    if(words.length < 2 || isNaN(words[0]))
        return console.log("Message from py invalid: ", words)
    let content = words.slice(1, words.length)
    if(words[0] === '0')
        return console.log(`Pyinfo: ${content.join(' ')}`)
    if(words[0] === '1')
        return processPyCommand(content.join(' '))
    if(content.length < 2)
        return console.log("Answer from py missing state or answer: ", content)
    processPyAnswer(parseInt(words[0]), content[0], content.slice(1, content.length).join(' '))
}


// needs to be put with promise so that commands are stacked in the correct order by the event loop if multiple messages are processed in one pass
// since answers are promises and commands would not be, these would execute the commands first (as described above)
async function processPyCommand(content) {
    await new Promise((resolve) => resolve(0))
    send_cmd_upwards(content, "py")
}

function processPyAnswer(id, state,  content) {
// DONT FORGET TO NOTIFY IF REQUESTS ARENT ORDERLY ANSWERED, TRY TO DO SO WITH QUEUE -> MAYBE SHIFT TO A WAIT QUEUE IF UNORERLY EXECUTED
    const promise = retrive_request(id)
    promise.res([id, state, content])
}



// -------------------------------- Bubbling upwards ------------------------------------

function send_cmd_upwards (cmd, caller) {
    update_state(cmd)
    logMsg(cmd, caller)
    process.send(cmd)
}

function update_state(command) {
    if(command === "start" || command === "resume")
        state = "running"
    if(command === "pause")
        state = "pausing"
    if(command === "stop")
        state = "idle"
}


function processSuccessfulRequest(command, answer) {
    // process state answers are not important, only accepted or rejected
    if(start_cmds.includes(command))
        return send_cmd_upwards("start", "main")
    if(process_cmds.includes(command))
        return send_cmd_upwards(command, "main")
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


async function request(msg) {
    let id = get_rand_id()
    return new Promise((resolve, reject) => {
        save_request(id, resolve, reject)
        sendPy(id, msg)
    })
}

function sendPy (id, msg) {
    child?.stdin?.setEncoding("utf-8")
    child?.stdin?.write(`${id} ${msg}` + "\n")
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
    return requestAnswer[1] === '0'
}


function isInvalidRequest (req) {
    if(start_cmds.includes(req) && state != 'idle') return true
    if(process_cmds.includes(req) && (state == 'idle' || state == 'stopped') ) return true
    return false
}


// only usuable for methods comming from main, preventing the event at restoring window to fire pause or resume
function isEventEcho (msg) {
    return msg === 'pause' && (state === 'stopped' || state === 'idle') || child == null && msg == 'pause'
}


main:
{
    startPyApplication()
}