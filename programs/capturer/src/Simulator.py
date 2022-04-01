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
import timing

import functools
print = functools.partial(print, flush=True)

_data = None
listeners = None
_on_pause = False
_ending = False
_timer = None


def read_file():
	with open(_data.filename, "r") as file:
		content = file.read()
		_data.storage = json.loads(content)


# --------------------- Key Listener ----------------------------


def run_key_thread():
	threading.Thread(target=check_stop_event, daemon=True).start()


def on_release(key):
	if type(key) == keyboard.Key and key == keyboard.Key["f1"]:
		request("stop")
	if type(key) == keyboard.Key and key == keyboard.Key["f2"]:
		request("resume") if _on_pause else request("pause")


def check_stop_event():
	# activating thread
	with keyboard.Listener(on_release=on_release) as listener:
		global listeners
		listeners = listener
		listener.join()



# ------------------------- IPC ---------------------------------


def request(cmd: str):
	global _ending
	if cmd == 'pause' and not _on_pause:
		pause()
	if cmd == 'resume' and _on_pause:
		resume()
	if cmd == 'stop' and not _ending:
		_ending = True
		request("pause")
		end()


def pause():
	global _on_pause
	_on_pause = True
	_timer.register_pause()
	print("pause")

def resume():
	global _on_pause
	_on_pause = False
	_timer.register_resume()
	print("resume")


# ---------------------- simulation -----------------------------

def simulate_behaviour():
	global _timer
	_timer = timing.TimeKeeper()
	delay = 0
	index = 0
	while index < len(_data.storage):
		if(_on_pause): continue
		if(_ending): break
		delay = time_exec_instruction(_data.storage[index], delay)
		index += 1


# returns the delay of this operation relativ to start of programm
def time_exec_instruction(instruction, delay):
	out_time = instruction["time"]-_timer.get_exec_time()
	delay = instruction["time"]
	_timer.sleep_until_ready(max(out_time, 0))
	simulate_instruction(instruction)
	return delay


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
	# set_configs()
	config_monitor()
	read_file()
	run_key_thread()
	simulate_behaviour()
	request("stop")


def end():
	Unpress.key_press_warnings(_data.keyboard_controller)
	listeners.stop()
	print("stop")


if __name__ == '__main__':
	main()






