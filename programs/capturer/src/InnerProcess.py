import ctypes, threading
from pynput import mouse, keyboard
import JSONHandler, timing, UnicodeReverse


# structure for both Recording amd Simulation, prevents duplicate and buggy code
class InnerProcess:

    def __init__(self, process):
        self.print_info = print
        self.print_cmd = print
        self.threads = []
        self.state = "idle"
        self.state_list = ["idle", "stop", "pause", "running"]
        self.ready = False
        self.data = self.get_data(process)
        self.timer = None
        config_monitor()

    def add_thread(self, thread):
        self.threads.append(thread)

    def stop_threads(self):
        for t in self.threads:
            t.stop()
            t.join()

    def request(self, arg: str, flush=False):
        if self.state == "stop" or not self.ready: return
        paused = self.state == 'pause'
        if arg == 'pause' and not paused:
            self.pause(flush)
        if arg == 'resume' and paused:
            self.resume(flush)
        if arg == 'stop':
            self.request("pause")
            self.end()

    def iterate_special_cases(self, key_name, pressed):
        # toggling if f2 is released
        if key_name == 'f2':
            if pressed: return True
            self.request("resume", True) if self.state == 'pause' else self.request("pause", True)
            return True
        return False

    def pause(self, flush=False):
        self.state = 'pause'
        self.timer.register_pause()
        if flush: self.print_cmd(self.state)

    def resume(self, flush=False):
        self.state = 'running'
        self.timer.register_resume()
        if flush: self.print_cmd(self.state)

    # overwrite for functionality
    def end(self): pass

    # overwrite to match 
    def run():
        pass

    def get_data(self, process):
        return JSONHandler.MetaData(process == 'recording')



# very important method, influences how windows scale is perceived
def config_monitor():
    ctypes.windll.shcore.SetProcessDpiAwareness(2)


class Recorder(InnerProcess):
    def __init__(self):
        super().__init__("recording")
        self.timer = timing.SimpleTimeKeeper()
        self.in_realtime = True
        self.in_handler = InputHandler(self)
        self.round_to = 3


    def listen_to_input(self):
        ih = self.in_handler
        listener1 = keyboard.Listener(on_press=ih.on_press, on_release=ih.on_release)
        listener2 = mouse.Listener(on_click=ih.on_click, on_scroll=ih.on_scroll, on_move=ih.on_move)
        self.add_thread(listener1)
        self.add_thread(listener2)
        listener1.start()
        listener2.start()

    def save_data(self):
        JSONHandler.compress(self.data.storage)
        JSONHandler.release_all(self.data.storage)
        JSONHandler.write_storage_file(self.data.storage, self.data.filename)

    # override
    def run(self):
        self.listen_to_input()
        self.state = "running"
        self.ready = True

    # overwrite
    def end(self):
        self.state = 'stop'
        self.stop_threads()
        self.save_data()




class InputHandler:

    def __init__(self, process):
        self.process = process
        self.storage = process.data.storage
        self.lock = process.data.lock
        self.is_paused = lambda: process.state == 'pause'
        self.get_time = lambda: round(process.timer.get_exec_time(), process.round_to)


    # ------------------------- individual recording ---------------------------------

    def on_click(self, x, y, mouse_button, pressed):
        if self.is_paused(): return
        with self.lock:
            button_name = mouse_button.name
            self.storage.add_mouse_click(button_name, self.get_time(), pressed, (x, y))

    def on_scroll(self, x, y, dx, dy):
        if self.is_paused(): return
        with self.lock:
            self.storage.add_mouse_scroll(self.get_time(), dx, dy)

    def on_move(self, x, y):
        if self.is_paused(): return
        with self.lock:
            self.storage.add_mouse_move(self.get_time(), x, y)

    def on_press(self, key):
        with self.lock:
            self.on_press_and_release(key, True)

    def on_release(self, key):
        with self.lock:
            self.on_press_and_release(key, False)

    def on_press_and_release(self, key, pressed: bool):
        special_key = type(key) == keyboard.Key
        name = key.char if (not special_key) else str(key)[4:]
        if name == None:
            return
        name = UnicodeReverse.convert_from_unicode(name)
        if not self.process.iterate_special_cases(name, pressed) and not self.is_paused():
            self.storage.add_key_stroke(name, self.get_time(), special_key, pressed)
