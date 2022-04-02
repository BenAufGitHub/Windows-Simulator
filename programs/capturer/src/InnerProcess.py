import ctypes, threading, json
from pynput import mouse, keyboard
import JSONHandler, timing, UnicodeReverse, Unpress
from programs.capturer.src.Recorder import iterate_special_cases


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

    # flush: whether accepted requests should be spread with print_cmd(cmd) - done so if request comes from Innerprocess itself
    def request(self, arg: str, flush=False):
        if self.state == "stop" or not self.ready: return
        paused = self.state == 'pause'
        if arg == 'pause' and not paused:
            self.pause(flush)
        if arg == 'resume' and paused:
            self.resume(flush)
        if arg == 'stop':
            self.request("pause")
            self.end(flush)

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

    def end(self, flush=False):
        self.state = 'stop'
        self.stop_threads()
        self.complete_before_end(flush)
        if flush: self.print_cmd('stop')

    # overwrite for functionality
    def complete_before_end(self):
        pass

    # overwrite to match 
    def run():
        pass

    def get_data(self, process):
        return JSONHandler.MetaData(process == 'recording')



# very important method, influences how windows scale is perceived
def config_monitor():
    ctypes.windll.shcore.SetProcessDpiAwareness(2)


class Simulator(InnerProcess):
    def __init__(self):
        super().__init__("simulating")
        self.timer = timing.TaskAwaitingTimeKeeper()
        # wait until simulation begins
        self.timer.register_pause()

    def read_file(self):
        with open(self.data.filename, "r") as file:
            content = file.read()
            self.storage = json.loads(content)

    def _check_toggle(self, key):
        if not self.ready: return
        special_key = type(key) == keyboard.Key
        name = key.char if (not special_key) else str(key)[4:]
        self.iterate_special_cases(name, False)

    def listen_to_pause_toggle(self):
        listener = keyboard.Listener(on_release=self._check_toggle)
        self.add_thread(listener)
        listener.start()
        

    def simulate_events(self):
        index = 0
        while index < len(self.storage):
            if(self.state=='pause'): continue
            if(self.state=='stop'): break
            self.time_exec_instruction(self.storage[index])
            index += 1
        self.request('stop', flush=True)


    # returns the delay of this operation relativ to start of programm
    def time_exec_instruction(self, instruction):
        out_time = instruction["time"]-self.timer.get_exec_time()
        self.timer.sleep_until_ready(max(out_time, 0))
        self.simulate_instruction(instruction)


    def simulate_instruction(self, instruction: dict):
        # action (press, release, scroll) belongs to a mouse instruction
        if "action" in instruction:
            exec_mouse_instruction(instruction, self.data.mouse_controller)
        else:
            exec_keyboard_instruction(instruction, self.data.keyboard_controller)


    def run(self):
        self.read_file()
        self.listen_to_pause_toggle()
        # timer is invoked
        self.timer.register_resume()
        self.init_simulation()
        self.ready = True

    def init_simulation(self):
        t = KillableThread(self.simulate_events)
        self.event_thread = t
        t.start()

    def complete_before_end(self, flush):
        Unpress.key_press_warnings(self.data.keyboard_controller)
        if flush:
            self.event_thread.stop()
            self.event_thread.join()



def exec_mouse_instruction(instruction: dict, controller):
	func, args = JSONHandler.get_function_from_mouse_object(instruction, controller)
	func(*args)


def exec_keyboard_instruction(instruction: dict, controller):
	func, args = JSONHandler.get_function_from_key_object(instruction, controller)
	func(*args)



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
    def complete_before_end(self, flush):
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



# class taken from https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
class KillableThread(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback
             
    def run(self):
        # target function of the thread class
        try:
            self.callback()
        finally:
            print('ended')
          
    def get_id(self):
        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id
  
    def stop(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Stop-Exception raise failure')
