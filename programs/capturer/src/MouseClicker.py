from pynput import mouse
from pynput import keyboard
import threading
import time
import json
import os
import Logger
import logging
import JSONHandler
import Unpress


_data = None
listeners = None


def read_file():
	with open(_data.filename, "r") as file:
		content = file.read()
		_data.storage = json.loads(content)


# --------------------- Key Listener ----------------------------


def run_key_thread():
	threading.Thread(target=check_stop_event, daemon=True).start()


def on_press(key):
	if type(key) == keyboard.Key and key == keyboard.Key["f1"]:
		end()


def check_stop_event():
	# activating thread
	with keyboard.Listener(on_press=on_press) as listener:
		global listeners
		listeners = listener
		listener.join()



# ---------------------- simulation -----------------------------

def simulate_behaviour():
	delay = 0
	for instruction in _data.storage:
		out_time = instruction["time"]-delay
		if out_time < 0:
			time.sleep(0)
		else:
			time.sleep(out_time)
			delay = instruction["time"]
		simulate_instruction(instruction)


def simulate_instruction(instruction: dict):
	if "action" in instruction:
		exec_mouse_instruction(instruction)
	else:
		exec_keyboard_instruction(instruction)


def exec_mouse_instruction(instruction: dict):
	func, args = JSONHandler.get_function_from_mouse_object(instruction, _data.mouse_controller)
	func(*args)


def exec_keyboard_instruction(instruction: dict):
	func, args = JSONHandler.get_function_from_key_object(instruction, _data.keyboard_controller)
	func(*args)


''' -------------------------------- Configurations ------------------------------------------------ '''


# very important method, influences how windows scale is perceived
def config_monitor():
	import ctypes
	awareness = ctypes.c_int()
	ctypes.windll.shcore.SetProcessDpiAwareness(2)

def set_configs():
	Logger.config_logging()
	logging.info("Type: Simulation")
	config_monitor()


def main():
	global _data
	_data = JSONHandler.MetaData(False)
	set_configs()
	read_file()
	run_key_thread()
	simulate_behaviour()
	end()


def end():
	Unpress.key_press_warnings(_data.keyboard_controller)
	listeners.stop()

if __name__ == '__main__':
	main()






