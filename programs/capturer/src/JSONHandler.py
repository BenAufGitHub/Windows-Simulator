from pynput.mouse import Controller, Button
from pynput.keyboard import Key
from pynput import mouse, keyboard
import threading, time
import json

class MetaData:
    def __init__(self, recording: bool):
        self.filename = "./resources/recording.json"
        self.auto_time = 0.1
        self.lock = _lock = threading.Lock()
        self.start_time = time.time()
        if recording:
            self.storage = JSONStorage()
        else:
            self.mouse_controller = Controller()
            self.keyboard_controller = keyboard.Controller()
            self.storage = []


class JSONStorage:

    def __init__(self):
        mouse_clicks, mouse_scrolls, mouse_moves, key_presses = [], [], [], []
        self.containers = ["mouse_clicks", "mouse_scrolls", "mouse_moves", "key_presses"]
        self.data = [mouse_clicks, mouse_scrolls, mouse_moves, key_presses]
        self.controller = Controller()

    def add_mouse_click(self, button: str, time: float, pressed: bool, point: (int, int)):
        click_instance = {"action": "click", "name": button, "time": time, "args": [pressed, point[0], point[1]]}
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
    indices = [0,0,0,0]
    times = [None, None, None, None]
    for i in range(4):
        times[i] = storage._get_time(i, indices[i])
    index = _compare_min(*times)
    while not index is None:
        merged.append(storage.data[index][indices[index]])
        indices[index] = indices[index] + 1
        for i in range(4):
            times[i] = storage._get_time(i, indices[i])
            index = _compare_min(*times)
    return merged


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
    _append_release_pressed(storage, pressed, container)


def _append_release_pressed(storage: JSONStorage, pressed, container: str):
    for button in pressed:
        is_mouse, name = button
        if is_mouse:
            storage.add_mouse_click(button, 0, False, storage.controller.position)
        else:
            storage.add_key_stroke(name, 0, name in Key.__members__, False)


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
    data_set = merge_containers(storage)
    json_string = json.dumps(data_set)
    write_file(json_string, filename)

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

def mouse_move(controller, x, y):
    controller.position = (x, y)


# Return: functions and args that match the json instruction.
def get_function_from_mouse_object(obj: dict, controller):
    action = obj["action"]
    if action == "click":
        args = [controller, obj["args"][1], obj["args"][2], obj["name"]]
        return (mouse_press, args) if obj["args"][0] else (mouse_release, args)
    elif action == "move":
        return mouse_move, [controller, obj["args"][0], obj["args"][1]]
    elif action == "scroll":
        return mouse_scroll, [controller, obj["args"][0], obj["args"][1]]


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