import sys, functools, traceback, threading
from typing import Tuple
import InnerProcess
print = functools.partial(print, flush=True)

starter_commands = ["simulate", "record"]
state = "idle"
possible_states = ["running", "paused", "idle"]
process_actions = ["pause", "resume"]
requests = []

process = None
lock = threading.Lock()


# ----------------------------------- Executing bubbling --------------------------------


def execute(cmd):
    throw_if_not_accepted(cmd)
    if cmd in starter_commands:
        return start_process(cmd)
    if cmd in process_actions:
        return mutate_process(cmd)
    if cmd in requests:
        return answer_request(cmd)
    raise CommandFailure("Command {cmd} not found")


def throw_if_not_accepted(cmd):
    if cmd in starter_commands and state != 'idle':
       raise CommandNotAccepted("A process already running")
    if cmd in process_actions and (state == 'idle' or not process):
        raise CommandNotAccepted(f"No process running to {cmd} / process not found")
    if cmd in process_actions and cmd == process.state:
        raise CommandNotAccepted(f"Request to {cmd} already fulfilled")


# -------------------- Execution ---------------------------------------

def start_process(cmd):
    global process, state
    process = InnerProcess.Simulator() if (cmd == 'simulate') else InnerProcess.Recorder()
    process.run()
    state = "running"
    return "DONE"


def mutate_process(cmd):
    if not process: raise CommandFailure("Process not found")
    if not process.request(cmd):
        raise CommandFailure(f"{cmd} request rejected")
    update_state(cmd)
    return "DONE"

def update_state():
    global state, process
    with lock:
        if process == None: return
        cmd = process.state
        if cmd == 'stop':
            state = 'idle'
            process = None
        else:
            state = "paused" if cmd == "pause" else "running"

def answer_request(cmd):
    pass
        


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
    update_state(cmd)
    print(f'1 {cmd}')


# identifier 0: outgoing info
def print_info(info: str):
    print(f'0 {info}')

# 0 for success
def return_answer(id, answer):
    print(f'{id} 0 {answer}')

# 1 for failure
def return_failure(id, reason):
    print(f'{id} 1 {reason}')


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
    id, cmd = split_input()
    try:
        result = execute(cmd) 
        return_answer(id, result)
    except (CommandNotAccepted, CommandFailure) as e:
        return_failure(id, str(e))
    except Exception as e:
        sys.stderr.write(traceback.extract_stack())
        return_failure(id, "See Traceback")

    if input == 'exit':
        raise InputStop()




# only identifiers from 2 upwards, since 0 and 1 are used for outgoing signals (python -> electron)
def is_valid_input(input):
    if not isinstance(input, str): return False
    words = input.split()
    if len(words) < 2: return False
    return words[0].isnumeric() and int(words[0]) > 1


# returns id (first word) and cmd (rest)
def split_input(input: str) -> Tuple[int, str]:
    arr = input.split()
    cmd = ' '.join(arr[1:])
    return arr[0], cmd



 
def main():
    read_in()


if __name__ == '__main__':
    main()
