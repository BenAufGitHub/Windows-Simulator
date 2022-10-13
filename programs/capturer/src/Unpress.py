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


def release_all():
    _release_modifiers()
    _release_mouse_buttons()


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
