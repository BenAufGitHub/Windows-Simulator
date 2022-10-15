from pynput.keyboard import Key
from pynput.mouse import Button
from pynput import keyboard, mouse
import Logger, logging
import win32api


def key_press_warnings(controller):
    with controller.modifiers as modifiers:
        for modifier in modifiers:
            print(f"Modifier still pressed: {modifier}") # TODO remove if logging is active again
            logging.warn(f"Modifier still pressed: {modifier}")
            controller.release(modifier)


# puts the cached information onto the given controller object
def rememeber_pressed(controller):
    with controller.modifiers as mods:
        controller.cached_mods = mods
    controller.right_pressed = win32api.GetKeyState(0x02)<0
    #left press might be accidentally used by clicking electron's icon, so it won't be listed here


def press_remembered(controller):
    if not hasattr(controller, "cached_mods"): return
    for modifier in controller.cached_mods:
        controller.press(modifier)
    if controller.right_pressed:
        mouse.Controller().press(Button.right)
    controller.right_pressed = False
    controller.cached_mods = []


def release_all():
    _release_modifiers()
    _release_mouse_buttons()


# if they are not pressed, they are not released: makes sense, but it really avoids much trouble :)
def _release_mouse_buttons():
    c = mouse.Controller()
    if win32api.GetKeyState(0x01)<0:
        c.release(Button.left)
    if win32api.GetKeyState(0x02)<0:
        c.release(Button.right)


def _release_modifiers():
    keys = {"cmd", "ctrl", "shift", "alt", "alt_gr"}
    c = keyboard.Controller()
    for key in keys:
        c.release(Key[key])


if __name__ == "__main__":
    Logger.config_logging()
    logging.info("Releasing")
    logging.warning("Program did not run as expected, modifier keys will be released.")
    _release_modifiers()
