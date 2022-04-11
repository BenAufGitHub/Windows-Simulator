import sys, functools, traceback, threading
from typing import Tuple

from requests import request
import InnerProcess, request_lib
print = functools.partial(print, flush=True)

starter_commands = ["simulate", "record"]
state = "idle"
possible_states = ["running", "paused", "idle"]
process_actions = ["pause", "resume", "stop"]
requests = ["exit", "spit", "getWinNames"]

process = None
state_lock = threading.Lock()
flush_orderly_lock = threading.Lock()


# ----------------------------------- Executing bubbling --------------------------------


def execute(cmd, body):
    throw_if_not_accepted(cmd)
    if cmd in starter_commands:
        return start_process(cmd)
    if cmd in process_actions:
        return mutate_process(cmd)
    if cmd in requests:
        return answer_request(cmd, body)
    raise CommandFailure(f"Command {cmd} not found")


def throw_if_not_accepted(cmd):
    if cmd in starter_commands and get_state() != 'idle':
       raise CommandNotAccepted("A process already running")
    if cmd in process_actions and (get_state() == 'idle' or not process):
        raise CommandNotAccepted(f"No process running to {cmd} / process not found")
    if cmd in process_actions and cmd == process.state:
        raise CommandNotAccepted(f"Request to {cmd} already fulfilled")


# -------------------- Execution ---------------------------------------

def start_process(cmd):
    global process, state
    process = InnerProcess.Simulator() if (cmd == 'simulate') else InnerProcess.Recorder()
    process.print_cmd = print_cmd
    process.print_info = print_info
    process.run()
    update_state()
    return "DONE"


def mutate_process(cmd):
    if not process: raise CommandFailure("Process not found")
    if not process.request(cmd):
        raise CommandFailure(f"{cmd} request rejected")
    update_state()
    return "DONE"

def update_state():
    global state, process
    with state_lock:
        if process == None: return
        cmd = process.state
        if cmd == 'stop':
            state = 'idle'
            process = None
        else:
            state = "paused" if cmd == "pause" else "running"

def get_state():
    with state_lock:
        return state             

def answer_request(cmd, body):
    if cmd == "exit":
        return 0
    if cmd == 'spit':
        print_info(body)
        return 'DONE'
    if cmd == 'getWinNames':
        # TODO
        raise Exception("Not impplemented: getWinNames")



# ------------------- Exceptions ---------------------------------------


class InputStop(Exception):
    pass

class CommandNotAccepted(Exception):
    pass

class CommandFailure(Exception):
    pass


# --------------------------- Process bubbling ----------------------------------------

# identifier 1: outgoing command
def print_cmd(cmd: str):
    update_state()
    with flush_orderly_lock:
        if cmd in process_actions and cmd != translate_state_to_command(): return
        print(f'1 {cmd}')


# identifier 0: outgoing info
def print_info(info: str):
    print(f'0 {info}')

# 0 for success
def return_answer(id, answer, command):
    update_state()
    with flush_orderly_lock:
        if command in process_actions and command != translate_state_to_command(): return
        answer = request_lib.transform_to_output_protocol(answer)
        print(f'{id} 0 {answer}')


# 1 for failure
def return_failure(id, reason: str):
    print(f'{id} 1 t {len(reason)} {reason}')


def translate_state_to_command():
    if process == None:
        return "stop"
    if process.state in process_actions:
        return process.state
    if process.state == 'running':
        return "resume"
    return None




# ------------------------ input verification + management ------------

def read_in():
    try:
        while(True):
            input = sys.stdin.readline()
            processIn(input)
    except InputStop:
        pass


def processIn(input):
    try:
        id, cmd, body = request_lib.split_request(input)
        if id < 2: raise request_lib.InvalidRequest("ID must be greater than 1")
    except request_lib.InvalidRequest as exc:
        return print_info(f"Not a valid input: {input}, reason: {str(exc)}")
    try:
        result = execute(cmd, body) 
        return_answer(id, result, cmd)
    except (CommandNotAccepted, CommandFailure) as e:
        return_failure(id, str(e))
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        return_failure(id, "See Traceback")

    if cmd == 'exit':
        raise InputStop()

 

def main():
    print_info("starting")
    read_in()


if __name__ == '__main__':
    main()
