import ctypes, threading, json, os, sys
import traceback
from pynput import mouse, keyboard
from JSONHandler import MetaData
from save_status import WindowSaver, WindowReproducer, Constants
import JSONHandler, timing, UnicodeReverse, Unpress
from threading import Lock, Thread
from rt import ClickInfo
import ConfigManager

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
        config_monitor()

    def add_thread(self, thread):
        self.threads.append(thread)

    def stop_threads(self):
        for t in self.threads:
            t.stop()
            t.join()

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
        self.state = 'pause'
        self.timer.register_pause()
        if not _stop_pause:
            WindowSaver().save_windows_for_pause()
        self.on_pause(flush, _stop_pause)
        if flush: self.print_cmd(self.state)

    # empty, override it with subclass
    def on_pause(self, flush, stop_pause):
        pass

    def resume(self, flush=False):
        WindowReproducer().reproduce_windows_after_pause()
        self.state = 'running'
        self.timer.register_resume()
        self.on_resume(flush)
        if flush: self.print_cmd("resume")

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



# ------------------------------------- Reproducer --------------------------------------------------

# ensures that the window is in the same state as it was when the window was recorded, thus Reproducer-Quality-Ensurance
class ReproducerQA():
    
    def __init__(self, command_callback):
        self.reproducer = WindowReproducer()
        self.upstream_requests_executed = 0
        self.print_cmd = command_callback
        self._access_flag_lock = Lock()
        self._resolve_flag = False

    def notify_resolve_ready(self):
        with self._access_flag_lock:
            self._resolve_flag = True

    def _get_path(self):
        file = ConfigManager.get_simulation()
        if not file: raise Exception('No simulation file specified.')
        return f"{Constants().get_savename()}{file}.json"
        
    def resolve_and_ready_up_windows(self):
        path = self._get_path()
        problem_pools = self.reproducer.get_unresolved_pools(path)
        solution = dict()
        for pool in problem_pools:
            result_list = self._resolve_pool(problem_pools[pool], pool)
            solution[pool] = result_list
        self._delete_cache_files()
        mapping = self.reproducer.get_resolved_map(problem_pools, solution)
        self.reproducer.replicate_map(mapping)


        
    def _delete_cache_files(self):
        if os.path.exists(MetaData().window_assigned_data):
            os.remove(MetaData().window_assigned_data)
        if os.path.exists(MetaData().window_unassigned_data):
            os.remove(MetaData().window_unassigned_data)

    def _resolve_pool(self, pool, process_name):
        recorded_wins = pool[0]
        active_wins = pool[1]
        active_wins_copy = active_wins.copy()
        results = []
        for i, win in enumerate(recorded_wins):
            active_win = self._resolve_window(win, active_wins_copy, process_name, i+1)
            if active_win:
                active_wins_copy.remove(active_win)
            results.append(active_wins.index(active_win) if active_win else -1)
        return results

    def _resolve_window(self, old_win, selection, process_name, resolve_attempt):
        if len(selection) == 0: return None
        if self._title_match(old_win["name"], selection):
            selection = self._filter_only_matching_windows(old_win["name"], selection)
        if len(selection) == 1: return selection[0]
        return self._send_and_await_response(old_win, selection, process_name, resolve_attempt)

    def _filter_only_matching_windows(self, name, selection):
        return list(filter(lambda x: x.window_text().encode("ascii", "ignore").decode() == name, selection))

    def _title_match(self, title, selection):
        for win in selection:
            # ignores troublesome characters same way as the titles from the recording
            current_title = win.window_text().encode("ascii", "ignore").decode()
            if current_title == title:
                return True
        return False

        
    def _prepare_file_info(self, old_win, selection, process_name, resolve_attempt):
        info_map = {
            "recorded": old_win["name"],
            "z_index": old_win["z_index"],
            "process_name": process_name,
            "resolve_step_no": resolve_attempt,
            "selection": []
        }
        
        for index, win in enumerate(selection):
            info_map["selection"].append([win.window_text(), win.handle])
        return info_map


    def _send_and_await_response(self, old_win, selection, process_name, resolve_attempt):
        self.upstream_requests_executed += 1
        info_map = self._prepare_file_info(old_win, selection, process_name, resolve_attempt)
        with open(MetaData().window_unassigned_data, 'w') as file:
            file.write(json.dumps(info_map))
        self.print_cmd("reproducer_resolve_window")
        self._stay_here_while_waiting()
        return self._get_response(selection)

    def _get_response(self, selection):
        with open(MetaData().window_assigned_data, 'r') as file:
            response = json.loads(file.read())
            index = int(response["selection"])
            return selection[index] if index >= 0 else None
            
    
    def _stay_here_while_waiting(self):
        while True:
            if self._resolve_flag:
                with self._access_flag_lock:
                    self._resolve_flag = False
                break

# ------------------------------------- Simulation -------------------------------------------------------



class Simulator(InnerProcess):
    
    def __init__(self):
        super().__init__()
        self.simulate_later = None
        self.timer = timing.TaskAwaitingTimeKeeper()
        # wait until simulation begins
        self.timer.register_pause()
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller() 

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
        self.init_simulation(self.simulation_wrapper)


    # override
    def on_pause(self, flush, stop_pause):
        if stop_pause: return
        Unpress.rememeber_pressed(self.keyboard_controller)
        Unpress.release_all()

    # override
    def on_resume(self, flush):
        Unpress.press_remembered(self.keyboard_controller)

        if not self.simulate_later: return
        func = self.simulate_later
        self.simulate_later = None
        self.init_simulation(lambda: self.simulation_wrapper(callback=func))


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
            exec_mouse_instruction(instruction, self.mouse_controller, self)
        else:
            exec_keyboard_instruction(instruction, self.keyboard_controller)


# ================ event callback chain =============


    # every simulation process (even after pause) should be inititated here, for the execution to be able to terminate properly
    # target is usually the simulation_wrapper method
    def init_simulation(self, target):
        t = KillableThread(target)
        self.event_thread = t
        t.start()


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
            self.simulate_later = lambda: self.simulate_events(index=index)
        else:
            return self._simulate_no_outer_pause(index)
    

    def _simulate_no_outer_pause(self, index):
        out_time = self._get_exec_time(index)
        is_done = self.timer.sleep_until_instruction(max(out_time, 0))
        if is_done:
            self._get_instruction(index)()
            return self.simulate_events(index=index+1)
        # pause inside of timer module, lambda method will be picked up later on resume
        self.simulate_later = lambda: self._get_async_timer_callback(index)


    def _get_exec_time(self, index):
        return self.storage[index]["time"]-self.timer.get_exec_time()


    def _get_instruction(self, index):
        return lambda: self.simulate_instruction(self.storage[index])


    # explained as in self._simulate_no_outer_pause
    def _get_async_timer_callback(self, unfinished_index):
        is_done = self.timer.sleep_async()
        if is_done:
            self._get_instruction(unfinished_index)()
            return lambda: self.simulate_events(index=unfinished_index+1)
        self.simulate_later = lambda: self._get_async_timer_callback(unfinished_index)


# <=============================== end ============================================



def exec_cmd_instruction(instruction: dict):
    if instruction["command"] == "release-all":
        Unpress.release_all()


def exec_mouse_instruction(instruction: dict, controller, simulator):
    func, args = JSONHandler.get_function_from_mouse_object(instruction, controller, simulator)
    func(*args)


def exec_keyboard_instruction(instruction: dict, controller):
	func, args = JSONHandler.get_function_from_key_object(instruction, controller)
	func(*args)



# ---------------------------------------------- Recording -----------------------------------------------------------


class Recorder(InnerProcess):
    def __init__(self):
        super().__init__()
        WindowSaver.reset_handle()
        self.save_current_win_status()
        ClickInfo().clear_clicked_windecies()
        self.init_screenshots()
        self.timer = timing.SimpleTimeKeeper()
        self.in_realtime = True
        self.storage = JSONHandler.JSONStorage()
        self.in_handler = InputHandler(self)
        self.round_to = 3

    def save_current_win_status(self):
        file = ConfigManager.get_recording()
        if not file: raise Exception('No recording specified.')
        path = f"{Constants().get_savename()}{file}.json"
        WindowSaver().save_current_win_status(path)
        
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
        outer_dir = Constants().get_screenshot_name()
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
        with open(f"{Constants().get_savename()}{ConfigManager.get_recording()}.json", "r") as file:
            return json.loads(file.read())

    # all inactive windows during the recording get deleted
    def overwrite_window_capture(self):
        active_indecies = ClickInfo().get_clicked_windecies_list()
        data = self._load_capture()
        data = list(filter(lambda d: d["z_index"] in active_indecies, data))
        with open(f"{Constants().get_savename()}{ConfigManager.get_recording()}.json", "w") as file:
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
        except Exception:
            sys.stderr.write(traceback.format_exc())
            end_on_warning = lambda: JSONHandler.stop_exec(True, self.process, "An error occured while receiving input.")
            threading.Thread(target=end_on_warning, daemon=True).start()



# class taken from https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
class KillableThread(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback
             
    def run(self):
        # target function of the thread class
        try:
            self.callback()
        except:
            exc = traceback.format_exc()
            sys.stderr.write(exc)
            sys.stderr.flush()
          
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
            print('0 Stop-Exception raise failure')
