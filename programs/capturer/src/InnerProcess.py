import ctypes, json, os, sys, _ctypes
from Lib import typing, traceback, threading

from pynput import mouse, keyboard

from save_status import WindowSaver, PathConstants, WindowNotExistant, PauseDirector
import JSONHandler
from utils import  UnicodeReverse, Unpress, ConfigManager, timing
from utils.rt import ClickInfo, KillableThread


# structure for both Recording amd Simulation, prevents duplicate and buggy code
class InnerProcess:

    def __init__(self):
        self.print_info = print
        self.print_cmd = print
        self.threads = []
        self.state = "idle"
        self.state_list = ["idle", "stop", "pause", "running"]
        self.ready = False
        self.data = self.get_data()
        self.timer = None
        self._req_lock = threading.RLock()
        self.ctrlW = True
        config_monitor()

    def add_thread(self, thread):
        self.threads.append(thread)

    def stop_threads(self):
        for t in self.threads:
            try:
                t.stop()
                t.join()
            except RuntimeError: pass

    # flush: whether accepted requests should be spread with print_cmd(cmd) - done so if request comes from Innerprocess itself
    # return: bool whether accepted or not
    def request(self, arg: str, flush=False, _stop_pause=False):
        with self._req_lock:
            return self._req(arg, flush, _stop_pause)


    def _req(self, arg, flush, _stop_pause=False):
        if self.state == "stop" or not self.ready: return False
        paused = (self.state == 'pause')
        if arg == 'pause' and not paused:
            self.pause(flush, _stop_pause)
            return True
        if arg == 'resume' and paused:
            self.resume(flush)
            return True
        if arg == 'stop':
            self.request("pause", _stop_pause=True)
            self.end(flush)
            return True
        return False


    def iterate_special_cases(self, key_name, pressed):
        # toggling if f2 is released
        if key_name == 'f2':
            if pressed: return True
            self.request("resume", True) if self.state == 'pause' else self.request("pause", True)
            return True
        return False

    def pause(self, flush=False, _stop_pause=False):
        try:
            self.state = 'pause'
            self.timer.register_pause()
            if not _stop_pause and self.ctrlW:
                PauseDirector().save_windows_for_pause()
            self.on_pause(flush, _stop_pause)
            if flush: self.print_cmd(self.state)
        except _ctypes.COMError as e: 
            if e.hresult != -2147220991: raise e
            self.request('stop', False)
            self.print_cmd("special-end 8")

                
    # empty, override it with subclass
    def on_pause(self, flush, stop_pause):
        pass

    def resume(self, flush=False):
        try:
            if self.ctrlW:
                PauseDirector().reproduce_windows_after_pause()
            self.state = 'running'
            self.timer.register_resume()
            self.on_resume(flush)
            if flush: self.print_cmd("resume")
        except WindowNotExistant: 
            self.request('stop', False)
            self.print_cmd("special-end 8")

    # empty, override it with subclass
    def on_resume(self, flush):
        pass

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

    def get_data(self):
        return JSONHandler.MetaData()



# very important method, influences how windows scale is perceived
def config_monitor():
    ctypes.windll.shcore.SetProcessDpiAwareness(2)


            

# ------------------------------------- Simulation -------------------------------------------------------



class Simulator(InnerProcess):
    
    def __init__(self, controlWindows='true'):
        super().__init__()
        self.simulate_later = None
        self.timer = timing.TaskAwaitingTimeKeeper()
        # wait until simulation begins
        self.timer.register_pause()
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()
        self.ctrlW = controlWindows == 'true'

    def _put_path(self):
        sim = ConfigManager.get_simulation()
        if sim: return f"{self.data.record_path}{sim}.json"
        return None

    def read_file(self):
        path = self._put_path()
        if not path: raise Exception('No path for simulation specified.')
        with open(path, "r") as file:
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
        

    def run(self):
        self.read_file()
        self.listen_to_pause_toggle()
        # timer is invoked
        self.timer.register_resume()
        self.state = "running"
        self.ready = True
        self.init_simulation(lambda: self.fail_safe(self.simulation_wrapper))


    def keep_mouse_pos(self, instruction_dict):
        if not "args" in instruction_dict: return
        self._mouse_pos = instruction_dict["args"][-2], instruction_dict["args"][-1]


    # override
    def on_pause(self, flush, stop_pause):
        if stop_pause: return
        Unpress.rememeber_pressed(self.keyboard_controller, _left=True)
        Unpress.release_all()

    # override
    def on_resume(self, flush):
        if self._mouse_pos:
            self.mouse_controller.position = self._mouse_pos
        Unpress.press_remembered(self.keyboard_controller)

        if not self.simulate_later: return
        func = self.simulate_later
        self.simulate_later = None
        failable = lambda: self.simulation_wrapper(callback=func)
        self.init_simulation(lambda: self.fail_safe(failable))


    def complete_before_end(self, flush):
        Unpress.key_press_warnings(self.keyboard_controller)
        Unpress.release_all()
        if not flush:
            self.event_thread.stop()
            self.event_thread.join()


    # function is called as described in event callback chain
    def simulate_instruction(self, instruction: dict):
        # action (press, release, scroll) belongs to a mouse instruction
        if "command" in instruction:
            exec_cmd_instruction(instruction)
        elif "action" in instruction:
            exec_mouse_instruction(instruction, self.mouse_controller, self, _ignoreMatching=not self.ctrlW)
        else:
            exec_keyboard_instruction(instruction, self.keyboard_controller)


# ================ event callback chain =============


    # every simulation process (even after pause) should be inititated here, for the execution to be able to terminate properly
    # target is usually the simulation_wrapper method
    def init_simulation(self, target):
        t = KillableThread(target)
        self.event_thread = t
        t.start()


    def fail_safe(self, cb):
        try:
            return cb()
        except SystemExit:
            pass
        except Exception:
            sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")
            print("1 special-end 6", flush=True)
            threading.Thread(target=lambda: self.request("stop", flush=False)).start()


    # the simulation wrapper takes the first simulation command and if it receives a comand back, it goes on with that
    # problem solved: when application is paused, the method terminates, but it is recalled on resume, which means no infinite loops waiting for a resumption (reduces power consumption a lot)
    # advantage: before, the events were chained, which led to a recursion-depth-error
    def simulation_wrapper(self, callback=None):
        if not callback:
            callback = self.simulate_events()
        while callback:
            callback = callback()


    # layer of checking whether state of execution has changed, it is a loop (technically) with increased indecies through callbacks
    def simulate_events(self, index=0):
        if index == len(self.storage) or self.state=='stop':
            self.request('stop', flush=True)
        elif self.state=='pause':
            func = lambda: self.simulate_events(index)
            self.simulate_later = lambda: self.fail_safe(func)
        else:
            return self._simulate_no_outer_pause(index)
    

    def _simulate_no_outer_pause(self, index):
        out_time = self._get_exec_time(index)
        is_done = self.timer.sleep_until_instruction(max(out_time, 0))
        if is_done:
            self._get_instruction(index)()
            return lambda: self.simulate_events(index+1)
        # pause inside of timer module, lambda method will be picked up later on resume
        func = lambda: self._get_async_timer_callback(index)
        self.simulate_later = lambda: self.fail_safe(func)


    def _get_exec_time(self, index):
        return self.storage[index]["time"]-self.timer.get_exec_time()


    def _get_instruction(self, index):
        return lambda: self.simulate_instruction(self.storage[index])


    # explained as in self._simulate_no_outer_pause
    def _get_async_timer_callback(self, unfinished_index):
        is_done = self.timer.sleep_async()
        if is_done:
            self._get_instruction(unfinished_index)()
            return lambda: self.simulate_events(unfinished_index+1)
        return lambda: self._get_async_timer_callback(unfinished_index)


# <=============================== end ============================================



def exec_cmd_instruction(instruction: dict):
    if instruction["command"] == "release-all":
        Unpress.release_all()


def exec_mouse_instruction(instruction: dict, controller, simulator, _ignoreMatching=False):
    simulator.keep_mouse_pos(instruction)
    func, args = JSONHandler.get_function_from_mouse_object(instruction, controller, simulator, _ignoreMatching)
    func(*args)


def exec_keyboard_instruction(instruction: dict, controller):
	func, args = JSONHandler.get_function_from_key_object(instruction, controller)
	func(*args)



# ---------------------------------------------- Recording -----------------------------------------------------------


class Recorder(InnerProcess):
    def __init__(self, ctrlW='False', takeScreenshots='true'):
        super().__init__()
        self.timer = timing.SimpleTimeKeeper()
        self.in_realtime = True
        self.storage = JSONHandler.JSONStorage(self, _takeScreenshots=takeScreenshots)
        self.in_handler = InputHandler(self)
        self.round_to = 3
        self.ctrlW = ctrlW == 'true'

    
    '''
    return: Preparation succesful True/False
    no errors
    '''
    def prepare_start(self) -> bool:
        try:
            WindowSaver.reset_handle()
            ClickInfo().clear_clicked_windecies()
            self.init_screenshots()
            if self.save_current_win_status(): return True
            self.print_cmd("special-end 8")
            return False
        except:
            sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")
            self.print_cmd("special-end 7")
            return False


    def save_current_win_status(self) -> bool:
        file = ConfigManager.get_recording()
        if not file: raise Exception('No recording specified.')
        path = f"{PathConstants().get_savename()}{file}.json"
        return WindowSaver().save_current_win_status(path)
        
    def init_screenshots(self):
        path = self._get_scr_path()
        if not os.path.exists(path):
            os.mkdir(path)
        else: self._rm_all_pics(path)


    def _rm_all_pics(self, path):
        files = os.listdir(rf'{path}')
        jpgs = filter(lambda f: f.find(".jpg") != -1, files)
        for f in list(jpgs):
            os.remove(path+f)

    def _get_scr_path(self):
        outer_dir = PathConstants().get_screenshot_name()
        return outer_dir + ConfigManager.get_recording() + '/'

    def listen_to_input(self):
        ih = self.in_handler
        listener1 = keyboard.Listener(on_press=ih.on_press, on_release=ih.on_release)
        listener2 = mouse.Listener(on_click=ih.on_click, on_scroll=ih.on_scroll, on_move=ih.on_move)
        self.add_thread(listener1)
        self.add_thread(listener2)
        listener1.start()
        listener2.start()

    def save_data(self):
        JSONHandler.compress(self.storage)
        JSONHandler.release_all(self.storage)
        JSONHandler.write_storage_file(self.storage, ConfigManager.get_recording())


    def _load_capture(self) -> list:
        with open(f"{PathConstants().get_savename()}{ConfigManager.get_recording()}.json", "r") as file:
            return json.loads(file.read())

    # all inactive windows during the recording get deleted
    def overwrite_window_capture(self):
        active_indecies = ClickInfo().get_clicked_windecies_list()
        data = self._load_capture()
        data = list(filter(lambda d: d["z_index"] in active_indecies, data))
        with open(f"{PathConstants().get_savename()}{ConfigManager.get_recording()}.json", "w") as file:
            file.write(json.dumps(data))


    # override
    def run(self):
        self.listen_to_input()
        self.state = "running"
        self.ready = True

    # override
    # used for adding release-all to commands
    def on_pause(self, flush, stop_pause):
        if stop_pause: return
        self.in_handler.on_command("release-all", {})


    # overwrite
    def complete_before_end(self, flush):
        self.save_data()
        self.overwrite_window_capture()




class InputHandler:

    def __init__(self, process):
        self.process = process
        self.storage = process.storage
        self.input_lock = threading.Lock()
        self.is_paused = lambda: process.state == 'pause'
        self.first_interaction_time = None
        self.get_raw_time = lambda: round(process.timer.get_exec_time(), process.round_to)


    # always start with the first interaction 0.1 seconds after programm start (in the simulation)
    def get_time(self):
        if not self.first_interaction_time:
            self.first_interaction_time = self.get_raw_time()
            return 0.1
        return round(self.get_raw_time() + 0.1 - self.first_interaction_time, self.process.round_to)

    # ------------------------- individual recording ---------------------------------


    def on_command(self, command, details):
        expr = lambda: self.storage.add_command(command, self.get_time(), details)
        self._fail_safe(expr)

    def on_click(self, x, y, mouse_button, pressed):
        expr = lambda: self._on_click(x, y, mouse_button, pressed)
        self._fail_safe(expr)

    def _on_click(self, x, y, mouse_button, pressed):
        if self.is_paused(): return
        with self.input_lock:
            button_name = mouse_button.name
            record_path = ConfigManager.get_recording()
            self.storage.add_mouse_click(button_name, self.get_time(), pressed, (x, y), record_path)


    def on_scroll(self, x, y, dx, dy):
        expr = lambda: self._on_scroll(x, y, dx, dy)
        self._fail_safe(expr)
        
    def _on_scroll(self, x, y, dx, dy):
        if self.is_paused(): return
        with self.input_lock:
            self.storage.add_mouse_scroll(self.get_time(), dx, dy)


    def on_move(self, x, y):
        expr = lambda: self._on_move(x, y)
        self._fail_safe(expr)
    
    def _on_move(self, x, y):
        if self.is_paused(): return
        with self.input_lock:
            self.storage.add_mouse_move(self.get_time(), x, y)


    def on_press(self, key):
        with self.input_lock:
            self._fail_safe(lambda: self.on_press_and_release(key, True))

    def on_release(self, key):
        with self.input_lock:
            self._fail_safe(lambda: self.on_press_and_release(key, False))


    def on_press_and_release(self, key, pressed: bool):
        special_key = type(key) == keyboard.Key
        name = key.char if (not special_key) else str(key)[4:]
        if name == None:
            return
        name = UnicodeReverse.convert_from_unicode(name)
        if not self.process.iterate_special_cases(name, pressed) and not self.is_paused():
            self.storage.add_key_stroke(name, self.get_time(), special_key, pressed)


    def _fail_safe(self, callback):
        try:
            callback()
        except SystemExit: pass
        except Exception:
            sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")
            end_on_warning = lambda: JSONHandler.stop_exec(True, self.process, "3")
            threading.Thread(target=end_on_warning, daemon=True).start()
