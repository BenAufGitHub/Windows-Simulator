from Lib.threading import Thread
import win32api, win32con

from ..desktop.utils import SimHandleOperator
from ..utils import win_utils
from ..utils.rt import stop_exec

from pynput.mouse import Button
from pynput.keyboard import Key



''' --------------------------------------- get input functions ----------------------------------------'''


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


def key_press(controller, key):
    controller.press(key)

def key_release(controller, key):
    controller.release(key)


''' ---------------------------- return task after evaluating saved input --------------------------- '''


# Return: functions and args that match the json instruction.
def get_function_from_key_object(obj: dict, controller):
    key = obj["name"] if not obj["args"][1] else Key[obj["name"]]
    if obj["args"][0]:
        return key_press, [controller, key]
    return key_release, [controller, key]


# Return: functions and args that match the json instruction.
def get_function_from_mouse_object(obj: dict, controller, simulator, _ignoreMatching=False):
    action = obj["action"] # click | scroll | move
    if action == "click":
        return get_mouse_click_func(obj, controller, simulator, _ignoreMatching=_ignoreMatching)
    else:
        scroll = action == "scroll"
        mouse_args = [controller, obj["args"][0], obj["args"][1]]
        return mouse_scroll if scroll else mouse_move, mouse_args


def get_mouse_click_func(obj, controller, simulator, _ignoreMatching=False):
    # if window was ignored or not found while resolving, no click will be done
    args = [controller, obj["args"][1], obj["args"][2], obj["name"]]
    rtrn = (mouse_press, args) if obj["args"][0] else (mouse_release, args)

    if _ignoreMatching: return rtrn

    if obj["windex"]>= 0 and not SimHandleOperator.has(obj["windex"]):
        return lambda: None, []
    
    matched = is_click_matching_window(obj["windex"], obj["args"][1], obj["args"][2])
    func = lambda: stop_exec(not matched, simulator, "4")
    Thread(target=func).start()

    return rtrn



def is_click_matching_window(original_windex, x, y):
    found_handle = win_utils.get_top_from_point(x, y).handle
    return SimHandleOperator().is_handle_match(original_windex, found_handle)
