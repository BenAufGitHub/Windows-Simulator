from pynput.keyboard import Controller, Key
import Logger, logging


def key_press_warnings(controller):
    with controller.modifiers as modifiers:
        for modifier in modifiers:
            print(f"Modifier still pressed: {modifier}") # TODO remove if logging is active again
            logging.warn(f"Modifier still pressed: {modifier}")
            controller.release(modifier)


def _release_modifiers():
    keys = {"cmd", "ctrl", "shift", "alt", "alt_gr"}
    c = Controller()
    for key in keys:
        c.release(Key[key])


if __name__ == "__main__":
    Logger.config_logging()
    logging.info("Releasing")
    logging.warning("Program did not run as expected, modifier keys will be released.")
    _release_modifiers()
