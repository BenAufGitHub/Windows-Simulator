import sys
from Lib import functools, traceback, threading

import InnerProcess, request_helper, request_lib
from save_status import WindowSaver, PathConstants, ReproductionResolver
from utils import ConfigManager
from utils.Errors import *


print = functools.partial(print, flush=True)

starter_commands = ["simulate", "record"]
state = "idle"
possible_states = ["running", "paused", "idle"]
process_actions = ["pause", "resume", "stop"]
requests = ["exit", "spit", "getWinNames", 'showWindow', "set-recording",
"get-recording", "get-record-list", "get-simulation", "get-simulation-list", "set-simulation", "delete-recording", "clear-settings"]
information = ["resolveFinished"]

SUCCESSFUL = True
process = None
state_lock = threading.Lock()
flush_orderly_lock = threading.Lock()
in_prep_for_simulation = False
resolve_window = lambda x: None

class ExecutionContainer:
    def __init__(self):
        self.open_window = None
exec_vars = ExecutionContainer()

# ----------------------------------- Executing bubbling --------------------------------


def execute(cmd, body):
    throw_if_not_accepted(cmd)
    if cmd in starter_commands:
        return start_process(cmd, body)
    if cmd in process_actions:
        return mutate_process(cmd)
    if cmd in information:
        return processInformation(cmd, body)
    if cmd in requests:
        return answer_request(cmd, body)
    raise CommandFailure(f"Command {cmd} not found")


def throw_if_not_accepted(cmd):
    if (cmd in starter_commands or cmd in process_actions) and in_prep_for_simulation:
        raise CommandNotAccepted(f"'{cmd}' not possible while in preparation for simulation")
    if cmd in starter_commands and get_state() != 'idle':
        raise CommandNotAccepted("A process is already running")
    if cmd in process_actions and (get_state() == 'idle' or not process):
        raise CommandNotAccepted(f"No process running to execute {cmd} / process not found")
    if cmd in process_actions and cmd == process.state:
        raise CommandNotAccepted(f"Request to {cmd} already fulfilled")


# -------------------- Execution ---------------------------------------

def start_process(cmd, body):
    global process
    process = InnerProcess.Simulator(body[0]) if (cmd == 'simulate') else InnerProcess.Recorder(body[0], body[1])
    process.print_cmd = print_cmd
    process.print_info = print_info

    if cmd == "simulate" and body[0] == 'true':
        start_simulation(process)
        return "DONE"
    elif cmd == "record" and process.prepare_start() != SUCCESSFUL:
        process = None
        return "FAILED"

    process.run()
    update_state()
    return "STARTING"


def save_current_win_status(self):
        file = ConfigManager.get_recording()
        if not file: raise Exception('No recording specified.')
        path = f"{PathConstants().get_savename()}{file}.json"
        WindowSaver().save_current_win_status(path)


def start_simulation(process):
    global in_prep_for_simulation, resolve_window
    in_prep_for_simulation = True
    resolver = ReproductionResolver(print_cmd)
    resolve_window = lambda id: resolver.process_response(id)
    threading.Thread(target=lambda: threaded_simulation_start(resolver, process)).start()


def threaded_simulation_start(resolver, process):
    def initiate():
        global in_prep_for_simulation
        process.run()
        update_state()
        print_cmd("start")
        in_prep_for_simulation = False
    def cancel():
        global in_prep_for_simulation, process
        in_prep_for_simulation = False
        process = None
    _resolve_and_ready_up_windows(resolver, then=initiate, failed=cancel)


def _resolve_and_ready_up_windows(resolver: ReproductionResolver, then, failed):
    try:
        resolver.resolve_and_ready_up_windows(then, failed)
    except Exception:
        sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")
        print_cmd(f'special-end 5')
        revert_simulation_start()


def revert_simulation_start():
    global in_prep_for_simulation, process
    process = None
    update_state()
    in_prep_for_simulation = False


def mutate_process(cmd):
    if not process: raise CommandFailure("Process not found")
    if not process.request(cmd):
        raise CommandFailure(f"{cmd} request rejected")
    update_state()
    return "DONE"

def update_state():
    global state, process
    with state_lock:
        if process == None or process.state == 'stop':
            state = 'idle'
            process = None
        else:
            state = "paused" if process.state == "pause" else "running"

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
        return list(request_lib.get_filtered_window_collection())
    if cmd == 'showWindow':
        if not request_lib.show_window(body):
            raise CommandFailure('Window not existing')
        return "DONE"
    if cmd == 'set-recording':
        return ConfigManager.set_recording(body)
    if cmd == 'get-recording':
        return ConfigManager.get_recording()
    if cmd == 'get-record-list':
        return ConfigManager.get_record_list()
    if cmd == 'get-simulation':
        return ConfigManager.get_simulation()
    if cmd == 'get-simulation-list':
        return ConfigManager.get_simulation_list()
    if cmd == 'set-simulation':
        return ConfigManager.set_simulation(body)
    if cmd == 'delete-recording':
        return ConfigManager.delete_recording(body)
    if cmd == 'clear-settings':
        return ConfigManager.clear()
    

def processInformation(cmd, body):
    if cmd == "resolveFinished":
        catchSolutionToWindows(body)
        return "DONE"
    return f"{cmd} NOT FOUND"

def catchSolutionToWindows(id):
    resolve_window(id)


# --------------------------- Process bubbling ----------------------------------------

# identifier 1: outgoing command
def print_cmd(cmd: str, args=None):
    update_state()
    with flush_orderly_lock:
        if cmd in process_actions and cmd != translate_state_to_command(): return
        if args: return print(f'1 {cmd} {args}')
        print(f'1 {cmd}')


# identifier 0: outgoing info
def print_info(info: str):
    if info:
        print(f'0 {info.encode("ascii", "ignore").decode()}')
    else:
        print(f'0 {info}')

# 0 for success
def return_answer(id, answer, command):
    update_state()
    with flush_orderly_lock:
        if command in process_actions and command != translate_state_to_command(): return
        answer = request_helper.transform_to_output_protocol(answer)
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
        id, cmd, body = request_helper.split_request(input)
        if id < 2: raise request_helper.InvalidRequest("ID must be greater than 1")
    except request_helper.InvalidRequest as exc:
        input = input.strip("\n")
        return print_info(f"Not a valid input: {input}, reason: {str(exc)}")
    try:
        result = execute(cmd, body) 
        return_answer(id, result, cmd)
    except (CommandNotAccepted, CommandFailure) as e:
        return_failure(id, str(e))
    except Exception as e:
        sys.stderr.write(traceback.format_exc())
        return_failure(id, str(e))

    if cmd == 'exit':
        raise InputStop()

 

def main():
    read_in()


if __name__ == '__main__':
    main()
