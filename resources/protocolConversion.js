class FormatError extends Error {
    constructor(message) {
      super(message);
      this.name = "FormatError";
    }
}

// -1 for can't fetch ID of faulty request format
function tryGetID(msg) {
    msg = msg.trim()
    if(!msg) return -1
    let words = msg.split(' ')
    let id = parseInt(words[0])
    return (!isNaN(id)) ? id : -1
}

// --------------------------------- to protocol format ---------------------------------

// args: floors integers
function getFormattedBody(args) {
    if(args==null) return 'n';
    if(!isNaN(args)) return `i ${Math.floor(args)}`
    if(typeof args == 'string') return `t ${args.length} ${args}`
    if(Array.isArray(args)) return formatListToString(args)
    throw new Error(`Illegal argument: number, string, null or array required: ${args}`)
}

function formatListToString(list) {
    let is_num_list = true;
    list.forEach(e => { if(typeof e != 'number') {is_num_list = false}})
    if(is_num_list){
        let polished_list = list.map(e => Math.floor(e))
        return `ai ${polished_list.join(' ')}`
    }
    let modified_list = list.map(e => `${String(e).length} ${String(e)}`)
    return `at ${modified_list.join('')}`
}

// -------------------------------- extract answer protocol ----------------------------------

// returns [id, errorcode, answer]
function splitAnswerMessage(msg) {
    if(!msg || !ltrim(msg)) throwFormatError(msg, "answer")
    let [id, remainder] = _seperateID(ltrim(msg))
    if(id < 2) return [id, remainder, null]
    let [errorcode, rawBody] = _seperate_errorcode(remainder)
    let body = getObjectFromRawBody(rawBody)
    return [id, errorcode, body]
}

// returns [id: number, remainder: string]
function _seperateID(msg) {
    let space = msg.search(' ')
    if(space === -1) throwFormatError(msg, "answer")
    let id = parseInt(msg.substring(0, space))
    if(isNaN(id)) throwFormatError(msg, "id")
    return [id, ltrim(msg.substring(space))]
}

function _seperate_errorcode(text) {
    if(!text.length) throwFormatError(text, "errorcode")
    let space = text.search(" ")
    if(space === -1) throwFormatError(text, "errorcode-answer")
    let ec = parseInt(text.substring(0,space))
    if(isNaN(ec)) throwFormatError(text, "errorcode")
    return [ec, ltrim(text.substring(space))]
}

function getObjectFromRawBody(rawBody) {
    let [identifier, remainder] = _split_identifier(rawBody)
    if(!["n", "t", "i", "ai", "at"].includes(identifier)) throwFormatError(rawBody, "identifier")
    if(identifier == 'n') return null
    let method_index = ['i', 't', 'ai', 'at'].indexOf(identifier)
    return [getNum, getTxt, getNumArr, getTxtArr][method_index](remainder)
}

function _split_identifier(text) {
    if(!text?.length) throwFormatError(text, "body")
    let space = text.search(" ")
    if(space === -1)
        return (text === 'n') ? text : throwFormatError(text, "body")
    let identifier = text.substring(0, space)
    return [identifier, ltrim(text.substring(space))]
}

const getNum = (remainder) => {
    let len = remainder.length
    if(remainder.search(' ') !== -1)
        len = remainder.search(' ')
    let num = parseInt(remainder.substring(0, len))
    if(isNaN(num)) throwFormatError(remainder, "number")
    return num
}

const getNumArr = (remainder) => {
    let arr = []
    while(remainder.length) {
        let num = getNum(remainder)
        let isNegative = num < 0
        arr.push(num)
        let num_length = getNumLength(num)
        remainder = ltrim(remainder.substring(num_length))
    }
    return arr
}
 
const getTxt = (remainder) => {
    let chars = getNum(remainder)
    let num_chars = getNumLength(chars)
    if(chars + num_chars + 1 > remainder.length) throwFormatError(remainder, "text")
    return remainder.substring(num_chars+1, 1+num_chars + chars)
}

const getTxtArr = (remainder) => {
    let arr = []
    while(remainder) {
        let txt = getTxt(remainder)
        arr.push(txt)
        let occupied_chars = getNumLength(txt.length) + 1 + txt.length
        remainder = ltrim(remainder.substring(occupied_chars))
    }
    return arr
}

// ---------------------------- extract request protocol ----------------------------------------

function splitRequestMessage(msg) {
    if(!msg || !ltrim(msg)) throwFormatError(msg, "request")
    let [id, remainder] = _seperateID(ltrim(msg))
    if(id === 1) return [id, remainder, null]
    let [req, rawBody] = _seperateRequest(remainder)
    let body = getObjectFromRawBody(rawBody)
    return [id, req, body]
}

function _seperateRequest(txt) {
    if(!txt.length) throwFormatError(txt, "request")
    let seperator = txt.search(" | ")
    if(seperator === -1) throwFormatError(txt, "request/body")
    return [txt.substring(0, seperator), ltrim(txt.substring(seperator+2))]
}


// ------------------------------ Assistence Methods ---------------------------------------------

function ltrim(x) {
    // This implementation removes whitespace from the left side
    // of the input string.
    return x.replace(/^\s+/gm, '');
}

function throwFormatError(msg, part){
    throw new FormatError(`Format protocol requires different ${part} input: ${msg}`)
}

function get10Log(x) {
    return Math.log(x) / Math.log(10);
}

// base 10
function getNumLength(num) {
    if(num < 0) return getNumLength(Math.abs(num)) + 1 
    if(num < 1) return 1
    return Math.floor(get10Log(num)) + 1 
}

// ---------------------- exports ------------------------

exports.FormatError = FormatError;
exports.getFormattedBody = getFormattedBody;
exports.splitAnswerMessage = splitAnswerMessage;
exports.splitRequestMessage = splitRequestMessage;
exports.tryGetID = tryGetID;