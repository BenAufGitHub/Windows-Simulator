import sys, functools, traceback, threading
from typing import Tuple

from requests import request
import InnerProcess, request_lib
print = functools.partial(print, flush=True)

starter_commands = ["simulate", "record"]
state = "idle"
possible_states = ["running", "paused", "idle"]
process_actions = ["pause", "resume", "stop"]
requests = ["exit", "spit"]

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
def return_failure(id, reason):
    print(f'{id} 1 {reason}')


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
            input = sys.stdin.readline().rstrip()
            processIn(input)
    except InputStop:
        pass


def processIn(input):
    if not is_valid_input(input):
        return print_info("Not a valid input") # None
    id, cmd, body = split_input(input)
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




# only identifiers from 2 upwards, since 0 and 1 are used for outgoing signals (python -> electron)
def is_valid_input(input):
    if not isinstance(input, str): return False
    words = input.split()
    if not words[1].isnumeric() or int(words[1]) + 3 > len(words): return False
    return words[0].isnumeric() and int(words[0]) > 1


# returns id (first word) and cmd (rest)
def split_input(input: str) -> Tuple[int, str]:
    arr = input.split()
    if int(arr[1]) > 0:
        return split_body_input(arr)
    return arr[0], arr[2], None


def split_body_input(input_arr):
    body_begin= len(input_arr) - int(input_arr[1])
    body = request_lib.get_input_body_object(' '.join(input_arr[body_begin:]))
    return input_arr[0], ' '.join(input_arr[2:body_begin]), body
 

def main():
    read_in()


if __name__ == '__main__':
    main()
