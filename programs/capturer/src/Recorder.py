from pynput.keyboard import Key
from pynput.mouse import Button
from pynput import mouse
from pynput import keyboard
import os, time, logging, sys
import Logger
import UnicodeReverse
import JSONHandler

import functools
print = functools.partial(print, flush=True)



# Metadata 
_data = None

# toggle currently not enabled TODO
in_realtime = True

# when no real time, toggle this is the base time
auto_time = 0.1

# keeps track of key and mouse listener
listener = []

# bool: whether recording is paused: listeners recording, but not storing
_on_pause = False

# the time at last pause
_pause_time = None

# whether the recording is closinf out
_ending = False

# the overall time that the recording was on pause (subtracted from overall times)
_pause_differential = 0



# ------------------------- individual recording ---------------------------------

def on_click(x, y, mouse_button, pressed):
	if _on_pause: return
	with _data.lock:
		button_name = mouse_button.name
		_data.storage.add_mouse_click(button_name, get_preferred_time(), pressed, (x, y))

def on_scroll(x, y, dx, dy):
	if _on_pause: return
	with _data.lock:
		_data.storage.add_mouse_scroll(get_preferred_time(), dx, dy)

def on_move(x, y):
	if _on_pause: return
	with _data.lock:
		_data.storage.add_mouse_move(get_preferred_time(), x, y)

def on_press(key):
	with _data.lock:
		on_press_and_release(key, True)

def on_release(key):
	with _data.lock:
		on_press_and_release(key, False)

def on_press_and_release(key, pressed: bool):
	special_key = type(key) == Key
	name = key.char if (not special_key) else str(key)[4:]
	if name == None:
		return
	name = UnicodeReverse.convert_from_unicode(name)
	if not iterate_special_cases(name, pressed) and not _on_pause:
		_data.storage.add_key_stroke(name, get_preferred_time(), special_key, pressed)


# -------------------------- handling ipc input ---------------------------------------

def request(arg: str):
	if _ending: return
	if arg == 'pause' and not _on_pause:
		pause()
	if arg == 'resume' and _on_pause:
		resume()
	if arg == 'stop' and not _ending:
		request("pause")
		end()


def pause():
	global _on_pause, _pause_time
	_on_pause = True
	_pause_time = time.time()

def resume():
	global _on_pause, _pause_time, _pause_differential
	_pause_differential += time.time() - _pause_time
	_on_pause = False
	_pause_time = None


# -------------------------- program settings ---------------------------------------


# print statements used for ipc with electron app
def iterate_special_cases(name: str, pressed: bool) -> bool:
	# TODO condition for real-time toggling
	if(name == 'f2'):
		# only do stuff on release (preventing multiple activations)
		if pressed: return True
		if(_on_pause):
			resume()
			print("resume")
			return True
		pause()
		print("pause")
		return True
	return False


def toggle_realtime():
	global in_realtime
	in_realtime = not in_realtime
	

def pop_time() -> float:
	if True: # TODO add possibility to make faster
		return round(time.time() - (_data.start_time + _pause_differential) , 3)
	return diff


def get_preferred_time():
	process_time = pop_time()
	return process_time if (in_realtime) else _data.auto_time



# ------------------------------- ending ------------------------------------------------

def end():
	global _data, _ending
	_ending = True
	for l in listener:
		l.stop()
	JSONHandler.compress(_data.storage)
	JSONHandler.release_all(_data.storage)
	JSONHandler.write_storage_file(_data.storage, _data.filename)
	print("writing ended")

# ------------------------- direct main calls ----------------------------------------------

def listen():
	with keyboard.Listener(on_press=on_press, on_release=on_release) as listener1:
		with mouse.Listener(on_click=on_click, on_scroll=on_scroll, on_move=on_move) as listener2:
			listener.append(listener1)
			listener.append(listener2)
			listener1.join()
			listener2.join()


# very important method, influences how windows scale is perceived
def config_monitor():
	import ctypes
	awareness = ctypes.c_int()
	ctypes.windll.shcore.SetProcessDpiAwareness(2)


def main():
	global _data
	_data = JSONHandler.MetaData(True)
	# Logger.config_logging()
	# logging.info("Type: Recording") TODO
	config_monitor()
	listen()


if __name__=='__main__':
	main()



#