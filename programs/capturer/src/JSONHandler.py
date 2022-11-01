from pynput.mouse import Controller, Button
from pynput.keyboard import Key
import json, time
from save_status import WindowSaver, WinUtils, WindowReproducer
from threading import Thread
import win32api, win32con
from rt import ClickInfo

class MetaData:
    def __init__(self):
        self.record_path = "./resources/recordings/"
        self.window_unassigned_data = "./resources/window_unresolved.json"
        self.window_assigned_data = "./resources/window_resolved.json"
        self.auto_time = 0.1
        self.start_time = time.time()


class JSONStorage:

    def __init__(self):
        mouse_clicks, mouse_scrolls, mouse_moves, key_presses, commands = [], [], [], [], []
        self.containers = ["mouse_clicks", "mouse_scrolls", "mouse_moves", "key_presses", "commands"]
        self.data = [mouse_clicks, mouse_scrolls, mouse_moves, key_presses, commands]
        self.manual_releases = []
        self.controller = Controller()

    def add_mouse_click(self, button: str, time: float, pressed: bool, point, record_path): 
        click_instance = {"action": "click", "name": button, "time": time, "args": [pressed, point[0], point[1]]}
        Thread(target=lambda: self.append_with_windex(point, click_instance, record_path)).start()

    def append_with_windex(self, point, click_instance, record_path):
        windex = WindowSaver.get_window_number(WinUtils.get_top_from_point(point[0], point[1]).handle)
        if windex >= 0 and not ClickInfo().clicked_contains(windex):
            ClickInfo().add_clicked_windex(windex)
            Thread(target=lambda: WindowSaver().save_screenshot(windex, record_path)).start()
        click_instance["windex"] = windex
        self.data[0].append(click_instance)

    def add_mouse_scroll(self, time: float, dx: int, dy: int):
        scroll_instance = {"action": "scroll", "time": time, "args": [dx, dy]}
        self.data[1].append(scroll_instance)

    def add_mouse_move(self, time: float, pos_x: int, pos_y: int):
        move_instance = {"action": "move", "time": time, "args": [pos_x, pos_y]}
        self.data[2].append(move_instance)

    def add_key_stroke(self, name: str, time: float, special_key: bool, pressed: bool):
        stroke_instance = {"name": name, "time": time, "args": [pressed, special_key]}
        self.data[3].append(stroke_instance)

    def add_command(self, command: str, time: float, details: dict):
        details["command"] = command
        details["time"] = time
        self.data[4].append(details)


    def _get_time(self, list_index, index) -> int:
        try:
            return self.data[list_index][index]["time"]
        except IndexError as e:
            return None



''' -------------------------- data compression ------------------------------------------------------------------'''


# merges similar data together and reduces the size of stored data
def compress(storage: JSONStorage):
    trim_input(storage)
    # TODO add compressing features

def trim_input(storage: JSONStorage):
    trim_shift(storage)

# since user is encouraged to press shift + f1 to end, simulating shift in the end may have unwanted effects
def trim_shift(storage: JSONStorage):
    data = storage.data[3]
    for i in range(len(data) - 1, -1, -1):
        if data[i]["name"] == "shift":
            data.pop(i);
        else:
            return

''' -------------------------- List merging -------------------------------------------------------------------- '''


# merges all lists in the correct order of actions and returns the list
def merge_containers(storage: JSONStorage) -> list:
    merged = []
    indices = [0,0,0,0,0]
    times = [None, None, None, None, None]
    for i in range(5):
        times[i] = storage._get_time(i, indices[i])
    index = _compare_min(*times)
    while not index is None:
        merged.append(storage.data[index][indices[index]])
        indices[index] = indices[index] + 1
        for i in range(5):
            times[i] = storage._get_time(i, indices[i])
            index = _compare_min(*times)
    appendManualReleases(storage, merged)
    return merged

def appendManualReleases(storage: JSONStorage, merged):
    if not merged: return
    for entry in storage.manual_releases:
        entry["time"] = round(merged[-1]["time"] + 0.05, 3)
        merged.append(entry)

def _compare_min(*args) -> int:
    lowest = None
    min = None
    if len(args) < 1: return None
    for index, arg in enumerate(args):
        if arg is None: continue
        if lowest is None or (arg < lowest and arg is not None):
            lowest = arg
            min = index
    return min



'''  ----------------------- ensure release of buttons --------------------------------------------'''

# Should ensure no keyboard mutations and not wished side effects. TODO: handle if program crashes
def release_all(storage: JSONStorage):
    for data_set in storage.containers:
        release_container(storage, data_set)


def release_container(storage: JSONStorage, container: str):
    index = storage.containers.index(container) if container in storage.containers else -1
    if index != 0 and index != 3: return
    pressed = _get_pressed_buttons(storage.data[index])
    _append_release_pressed(storage, pressed)


def _append_release_pressed(storage: JSONStorage, pressed):
    for button in pressed:
        is_mouse, name = button
        if is_mouse:
            entry = {"action": "click", "name": name, "args": [False, storage.controller.position[0], storage.controller.position[1]], "windex": -2}
            storage.manual_releases.append(entry)
        else:
            entry = {"name": name, "args": [False, name in Key.__members__]}
            storage.manual_releases.append(entry)


# return those button's names of which are pressed but not released at end of simulation
def _get_pressed_buttons(data: list) -> set:
    pressed_buttons = set()
    for entry in data:
        entry_value = ("action" in entry, entry["name"])
        if entry_value not in pressed_buttons and entry["args"][0]:
            pressed_buttons.add(entry_value)
        if entry_value in pressed_buttons and not entry["args"][0]:
            pressed_buttons.remove(entry_value)
    return pressed_buttons


''' ------------------------------------ file writing -------------------------------------------- '''

def write_storage_file(storage: JSONStorage, filename: str):
    if not filename: raise Exception('No record file specified.')
    path = f"{MetaData().record_path}{filename}.json"
    data_set = merge_containers(storage)
    json_string = json.dumps(data_set)
    write_file(json_string, path)

def write_file(json_str: str, filename: str):
    with open(filename, "w") as file:
        file.write(json_str)


''' --------------------------------------- get functions ----------------------------------------'''

def mouse_press(controller, x, y, name):
    controller.position = (x, y)
    controller.press(Button[name])

def mouse_release(controller, x, y, name):
    controller.position = (x, y)
    controller.release(Button[name])

def mouse_scroll(controller, dx, dy):
    controller.scroll(dx, dy)


# code from https://github.com/akmalmzamri/mousemover/blob/master/mousemover/mouse_handler.py
def mouse_move(controller, x, y):
    x1, y1 = controller.position
    screen_width = win32api.GetSystemMetrics(0)
    screen_height = win32api.GetSystemMetrics(1)
    win32api.mouse_event(
            win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,
            int((x / screen_width * 65535.0) + (x-x1)),
            int((y / screen_height * 65535.0) + (y-y1))
        )
    if controller.position != (x, y):
        controller.position = (x, y)


# Return: functions and args that match the json instruction.
def get_function_from_mouse_object(obj: dict, controller, simulator):
    action = obj["action"]
    if action == "click":
        return get_mouse_click_func(obj, controller, simulator)
    elif action == "move":
        return mouse_move, [controller, obj["args"][0], obj["args"][1]]
    elif action == "scroll":
        return mouse_scroll, [controller, obj["args"][0], obj["args"][1]]


def get_mouse_click_func(obj, controller, simulator):
    # if window was ignored or not found while resolving, no click will be done
    if not WindowReproducer.has_handle(obj["windex"]):
            return lambda: None, []
    func = lambda: stop_exec(not is_click_matching_window(obj["windex"], obj["args"][1], obj["args"][2]), simulator, "Error: Wrong window position detected.")
    Thread(target=func).start()
    args = [controller, obj["args"][1], obj["args"][2], obj["name"]]
    return (mouse_press, args) if obj["args"][0] else (mouse_release, args)


def stop_exec(bool, process, reason):
    if not bool: return
    # eliminate python-side
    process.request("stop", flush=False)
    # inform front-end
    process.print_cmd(f"special-end {reason}")




def is_click_matching_window(original_windex, x, y):
    found_handle = WinUtils.get_top_from_point(x, y).handle
    return WindowReproducer().is_hwnd_match(original_windex, found_handle)

def key_press(controller, key):
    controller.press(key)

def key_release(controller, key):
    controller.release(key)


# Return: functions and args that match the json instruction.
def get_function_from_key_object(obj: dict, controller):
    key = obj["name"] if not obj["args"][1] else Key[obj["name"]]
    if obj["args"][0]:
        return key_press, [controller, key]
    return key_release, [controller, key]