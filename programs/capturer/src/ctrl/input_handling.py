import json
import Lib.traceback as traceback
from Lib.threading import Thread
from Lib.sysconfig import sys

from save_status import WindowSaver
from utils.rt import ClickInfo, MetaData, stop_exec
import utils.win_utils as win_utils

from pynput.mouse import Controller
from pynput.keyboard import Key



class InputProcessor:

    def __init__(self, process, _takeScreenshots='true'):
        mouse_clicks, mouse_scrolls, mouse_moves, key_presses, commands = [], [], [], [], []
        self.containers = ["mouse_clicks", "mouse_scrolls", "mouse_moves", "key_presses", "commands"]
        self.data = [mouse_clicks, mouse_scrolls, mouse_moves, key_presses, commands]
        self.manual_releases = []
        self.controller = Controller()
        self._scr = _takeScreenshots == 'true'
        self.process = process

    
    def fail_safe(self, callback):
        try:
            callback()
        except SystemExit: pass
        except:
            Thread(target=lambda: stop_exec(True, self.process, 3), daemon=True).start()
            sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")


    def add_mouse_click(self, button: str, time: float, pressed: bool, point, record_path, _safe=False):
        click_instance = {"action": "click", "name": button, "time": time, "args": [pressed, point[0], point[1]]}
        if pressed:
            func = lambda: self.append_with_windex(point, click_instance, record_path)
            Thread(target=lambda: self.fail_safe(func)).start()
        else:
            click_instance["windex"] = -2
            self.data[0].append(click_instance)


    def append_with_windex(self, point, click_instance, record_path):
        windex = WindowSaver.get_window_number(win_utils.get_top_from_point(point[0], point[1]).handle)
        if windex >= 0 and not ClickInfo().clicked_contains(windex):
            ClickInfo().add_clicked_windex(windex)
            if not self._scr: return
            func = lambda: WindowSaver().save_screenshot(windex, record_path)
            Thread(target=lambda: self.fail_safe(func)).start()
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
def compress(container: InputProcessor):
    trim_input(container)


def trim_input(container: InputProcessor):
    trim_shift(container)


# since user is encouraged to press shift + f1 to end, simulating shift in the end may have unwanted effects
def trim_shift(container: InputProcessor):
    data = container.data[3]
    for i in range(len(data) - 1, -1, -1):
        if data[i]["name"] == "shift":
            data.pop(i)
        else:
            return

''' -------------------------- List merging -------------------------------------------------------------------- '''


# merges all lists in the correct order of actions and returns the list
def merge_containers(storage: InputProcessor) -> list:
    merged = []
    indices = [0,0,0,0,0]
    times = [None, None, None, None, None]
    
    while (index := _refresh_times(times, indices, storage)) is not None:
        merged.append(storage.data[index][indices[index]])
        indices[index] = indices[index] + 1

    appendManualReleases(storage, merged)
    return merged


def _refresh_times(times, indices, storage):
    for i in range(5):
        times[i] = storage._get_time(i, indices[i])
    return _compare_min(*times)


def appendManualReleases(storage: InputProcessor, merged):
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
def release_all(storage: InputProcessor):
    for data_set in storage.containers:
        release_container(storage, data_set)


def release_container(storage: InputProcessor, container: str):
    if container not in storage.containers: return
    index = storage.containers.index(container)
    if index != 0 and index != 3: return
    pressed = _get_pressed_buttons(storage.data[index])
    _append_release_pressed(storage, pressed)


def _append_release_pressed(storage: InputProcessor, pressed):
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


def write_storage_file(storage: InputProcessor, filename: str):
    if not filename: raise Exception('No record file specified.')

    path = f"{MetaData().record_path}{filename}.json"
    data_set = merge_containers(storage)
    json_string = json.dumps(data_set)
    write_file(json_string, path)


def write_file(json_str: str, filename: str):
    with open(filename, "w") as file:
        file.write(json_str)