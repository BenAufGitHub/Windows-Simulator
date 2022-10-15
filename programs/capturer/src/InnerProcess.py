import ctypes, threading, json, os
from pynput import mouse, keyboard
from JSONHandler import MetaData
from save_status import WindowSaver, WindowReproducer
import JSONHandler, timing, UnicodeReverse, Unpress
from threading import Lock

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
    def request(self, arg: str, flush=False):
        with self._req_lock:
            return self._req(arg, flush)


    def _req(self, arg, flush):
        if self.state == "stop" or not self.ready: return False
        paused = (self.state == 'pause')
        if arg == 'pause' and not paused:
            self.pause(flush)
            return True
        if arg == 'resume' and paused:
            self.resume(flush)
            return True
        if arg == 'stop':
            self.request("pause")
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

    def pause(self, flush=False):
        self.state = 'pause'
        self.timer.register_pause()
        if flush: self.print_cmd(self.state)

    def resume(self, flush=False):
        self.state = 'running'
        self.timer.register_resume()
        if flush: self.print_cmd("resume")

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

    def resolve_and_ready_up_windows(self):
        problem_pools = self.reproducer.get_unresolved_pools()
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
            info_map["selection"].append(win.window_text())
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
        self.timer = timing.TaskAwaitingTimeKeeper()
        # wait until simulation begins
        self.timer.register_pause()
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller() 

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
            exec_mouse_instruction(instruction, self.mouse_controller, self)
        else:
            exec_keyboard_instruction(instruction, self.keyboard_controller)


    def run(self):
        self.read_file()
        self.listen_to_pause_toggle()
        # timer is invoked
        self.timer.register_resume()
        self.init_simulation()
        self.state = "running"
        self.ready = True

    def init_simulation(self):
        t = KillableThread(self.simulate_events)
        self.event_thread = t
        t.start()

    def complete_before_end(self, flush):
        Unpress.key_press_warnings(self.keyboard_controller)
        Unpress.release_all()
        if not flush:
            self.event_thread.stop()
            self.event_thread.join()



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
        WindowSaver().save_current_win_status()
        self.timer = timing.SimpleTimeKeeper()
        self.in_realtime = True
        self.storage = JSONHandler.JSONStorage()
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
        JSONHandler.compress(self.storage)
        JSONHandler.release_all(self.storage)
        JSONHandler.write_storage_file(self.storage, self.data.filename)

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

    def on_click(self, x, y, mouse_button, pressed):
        if self.is_paused(): return
        with self.input_lock:
            button_name = mouse_button.name
            self.storage.add_mouse_click(button_name, self.get_time(), pressed, (x, y))

    def on_scroll(self, x, y, dx, dy):
        if self.is_paused(): return
        with self.input_lock:
            self.storage.add_mouse_scroll(self.get_time(), dx, dy)

    def on_move(self, x, y):
        if self.is_paused(): return
        with self.input_lock:
            self.storage.add_mouse_move(self.get_time(), x, y)

    def on_press(self, key):
        with self.input_lock:
            self.on_press_and_release(key, True)

    def on_release(self, key):
        with self.input_lock:
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
        except:
            pass
          
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
