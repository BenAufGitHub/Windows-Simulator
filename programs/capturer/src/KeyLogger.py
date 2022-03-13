from pynput.keyboard import Key
from pynput.mouse import Button
from pynput import mouse
from pynput import keyboard
import os, time, logging
import Logger
import UnicodeReverse
import JSONHandler



_data = None
in_realtime = True
auto_time = 0.1
tkinter = None
listener = []

_on_pause = False
_pause_time = None
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


# -------------------------- handling tkinter ---------------------------------------

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


def iterate_special_cases(name: str, pressed: bool) -> bool:
	if(name == 'f1'):
		end()
		return True
	if(name == 'f2'):
		if(_on_pause): return True
		if(True): # TODO
			pause()
			tkinter.on_call()
			return True
		if(pressed):
			toggle_realtime()
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
	global _data
	for l in listener:
		l.stop()
	JSONHandler.compress(_data.storage)
	JSONHandler.release_all(_data.storage)
	JSONHandler.write_storage_file(_data.storage, _data.filename)


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


def main(frame):
	global _data, tkinter
	tkinter = frame
	_data = JSONHandler.MetaData(True)
	Logger.config_logging()
	logging.info("Type: Recording")
	#config_monitor()
	listen()


if __name__=='__main__':
	main()