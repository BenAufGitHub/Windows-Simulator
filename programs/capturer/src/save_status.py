from pywinauto import controls, uia_element_info, handleprops, base_wrapper

import json, _ctypes, ctypes, os
from Lib import traceback, typing, threading
from Lib.sysconfig import sys

from utils import config_manager
from utils.rt import PathConstants
from utils import win_utils
from utils.app_errors import *


ctypes.windll.shcore.SetProcessDpiAwareness(2)



class WindowSaver:

    _window_dict = dict()

    # get the z_index noted at the start of the recording for the given window
    @staticmethod
    def get_window_number(handle: int):
        if not handle in WindowSaver._window_dict:
            return -1
        return WindowSaver._window_dict[handle]


    @staticmethod
    def get_handle(windex):
        is_answer = lambda h: WindowSaver._window_dict[h] == windex
        l = list(filter(is_answer, WindowSaver._window_dict.keys()))
        if not l: return None
        return l[0]

    
    @staticmethod
    def reset_handle():
        WindowSaver._window_dict = dict()


    @staticmethod
    def set_window_number(handle, number):
        WindowSaver._window_dict[handle] = number


    def save_current_win_status(self, path) -> bool:
        try:
            wins = win_utils.get_ordered_wins()
            for index, win in enumerate(wins):
                WindowSaver.set_window_number(win.handle, index)
            self._enter_windows_into_file(wins, path)
            return True
        except _ctypes.COMError as e:
            if e.hresult == -2147220991: return False
            raise e



    def _enter_windows_into_file(self, windows, path):
        with open(path, "w") as file:
            file.write("[")
            for index, win in enumerate(windows):
                if index != 0:
                    file.write(",")
                win_properties = self._get_win_properties_as_dict(win, index)
                file.write(json.dumps(win_properties))
            file.write("]")


    def _get_win_properties_as_dict(self, win, z_index):
        win_name = win.window_text().encode("ascii", "ignore").decode()
        process_name = win_utils.get_proc_name_by_hwnd(win.handle)

        if win.is_maximized():
            return {"name": win_name, "process": process_name, "max": True, "z_index": z_index}

        coordinates = (win.rectangle().left, win.rectangle().top)
        dimensions = (win.rectangle().width(), win.rectangle().height())

        return {
            "name": win_name,
            "process": process_name,
            "max": False,
            "coordinates": coordinates,
            "dimensions": dimensions,
            "z_index": z_index
        }


    def save_screenshot(self, windex, filepath):
        hwnd = self.get_handle(windex)
        if hwnd == None: return
        info = uia_element_info.UIAElementInfo(handle_or_elem=hwnd)
        wrapper = controls.hwndwrapper.HwndWrapper(info)
        image = wrapper.capture_as_image(wrapper.rectangle())
        path = PathConstants().get_screenshot_name() + filepath + '/'
        image.save(f"{path}{windex}.jpg", quality=10)




class PauseDirector:


    _cached_window_positions_for_pause = None


    # ===== saving =====>


    def save_windows_for_pause(self):
        PauseDirector._cached_window_positions_for_pause = self._get_current_windows()

    @staticmethod
    def get_cached_wins():
        return PauseDirector._cached_window_positions_for_pause

    @staticmethod
    def clear_cache_for_pause():
        PauseDirector._cached_window_positions_for_pause = None

    def _get_current_windows(self):
        winlist = list()
        windows = win_utils.get_ordered_wins()
        for zindex, win in enumerate(windows):
            wininfo = self._get_positional_properties(win, zindex)
            winlist.append(wininfo)
        return winlist

    def _get_positional_properties(self, win, zindex):
        has_title = len(win.window_text()) > 0
        if win.is_maximized(): return {"ref": win, "max": True, "z": zindex, "has_title": has_title}
        return {
            "ref": win,
            "max": False,
            "x": win.rectangle().left,
            "y": win.rectangle().top,
            "z": zindex,
            "width": win.rectangle().width(),
            "height": win.rectangle().height(),
            "has_title": has_title
        }


    # ===== reproducing =======>


    def reproduce_windows_after_pause(self):
        if not PauseDirector.get_cached_wins():
            return print("0 No cached windows to reproduce found while reproducing after pause.", flush=True)
        winlist = PauseDirector.get_cached_wins()
        try:
            self._repr_wins(winlist)
        except _ctypes.COMError as e:
            if e.hresult != -2147220991: raise e
            raise WindowNotExistant()
        PauseDirector.clear_cache_for_pause()

    
    def _repr_wins(self, winlist):
        win_utils.minimize_all_windows()
        for wininfo in reversed(winlist):
            self._replecate_win_after_pause(wininfo)


    def _replecate_win_after_pause(self, wininfo):
        pid = wininfo["ref"].element_info.process_id
        self._alert_closed(wininfo["ref"], wininfo["has_title"])

        if not win_utils.is_normal_win(wininfo["ref"]): return
        if not pid: raise WindowNotExistant()

        if wininfo["max"]:
            return win_utils.maximize_win(wininfo["ref"])
        win_utils.show_win_as_rect(wininfo["ref"], wininfo["x"], wininfo["y"], wininfo["width"], wininfo["height"])

    
    def _alert_closed(self, win, has_title):
        # if there is no window text, it is assumed it is not a normal window, as previously there have been bugs because of it,
        if not handleprops.iswindow(win.handle) and has_title:
            raise WindowNotExistant()




class SimHandleOperator():

    _window_dict = dict()


    @staticmethod
    def get_handle(z_index: int):
        if(z_index == -1):
            return None
        return SimHandleOperator._window_dict[z_index]

    
    @staticmethod
    def has(z_index):
        return z_index in SimHandleOperator._window_dict

    @staticmethod
    def has_handle(handle):
        return handle in SimHandleOperator._window_dict.values()

    @staticmethod
    def reset_handles():
        SimHandleOperator._window_dict = dict()

    @staticmethod
    def is_handle_match(z_index, clicked_handle):
        # -2 represents that the window doesnt matter
        if z_index == -2: return True
        if z_index >= 0 and not SimHandleOperator.has(z_index):
            return False
        if SimHandleOperator.get_handle(z_index) == None:
            return not (SimHandleOperator.has_handle(clicked_handle))
        return SimHandleOperator.get_handle(z_index) == clicked_handle


    @staticmethod
    def set_window_handle(number, handle):
        SimHandleOperator._window_dict[number] = handle




class WindowCollections:
    

    @staticmethod
    def get_all_from_process(process):
        collection = set()
        found_windows = win_utils.get_ordered_wins()
        for win in found_windows:
            if process == win_utils.get_proc_name_by_hwnd(win.handle).lower():
                collection.add(win)
        return collection


    # ======= create pools =========>


    # list entries: [list process_name_saved, list process_name_available]
    @staticmethod
    def collect_pools(path):
        with open(path, "r") as file:
            old_windows = json.loads(file.readline())
        found_windows = win_utils.get_ordered_wins()
        return WindowCollections._group_together(old_windows, found_windows)


    @staticmethod
    def _group_together(saved, found):
        groups = WindowCollections._prepare_saved(saved)
        for win in found:
            process = win_utils.get_proc_name_by_hwnd(win.handle).lower()
            if process in groups:
                groups[process][1].append(win)
        return groups


    @staticmethod
    def _prepare_saved(saved):
        groups = dict()
        for win in saved:
            process = win["process"].lower()
            if process not in groups:
                groups[process] = (list(), list())
            groups[process][0].append(win)
        return groups


    # ====== evaluate solutions =========>


    # returns ReproducerGuide
    @staticmethod
    def create_win_relations(groups, solutions):
        guide = ReproducerGuide()
        for group_name in groups:
            group = groups[group_name]
            for i, recordedWin in enumerate(group[0]):
                answer = solutions[group_name][i]
                matched = group[1][answer] if answer >= 0 else None
                guide.add(recordedWin["z_index"], recordedWin, matched)
        return guide





class ReproducerGuide():
    
    def __init__(self):
        self._associations = dict()

    def add(self, id: int, saved: dict, matched: base_wrapper.BaseWrapper):
        self._associations[id] = (saved, matched)

    def get_ids(self):
        return self._associations.keys()

    def get_saved(self, id):
        return self._associations[id][0]

    def get_matched(self, id):
        return self._associations[id][1]



class Reproducer:


    @staticmethod
    def reproduce(guide: ReproducerGuide):
        Reproducer.minimize_non_active(guide)
        for win_key in reversed(sorted(guide.get_ids())):

            saved = guide.get_saved(win_key)
            active = guide.get_matched(win_key)
            if not active: continue

            Reproducer._reproduce(saved, active)

    
    @staticmethod
    def minimize_non_active(guide: ReproducerGuide):
        wins = win_utils.get_ordered_wins()
        get_handle = lambda id: guide.get_matched(id).handle
        matched = filter(lambda id: guide.get_matched(id), guide.get_ids())
        handles = list(map(get_handle, matched))
        for w in wins:
            if w.handle not in handles:
                win_utils.minimize_no_err(w)
     

    @staticmethod
    def _reproduce(win, active_win):
        SimHandleOperator.set_window_handle(win["z_index"], active_win.handle)
        # if process has been eliminated during this process
        if active_win.element_info.process_id == None: raise WindowNotExistant()
        try:
            if win["max"]: 
                return win_utils.maximize_win(active_win)
            win_utils.show_win_as_rect(active_win, win["coordinates"][0], win["coordinates"][1], win["dimensions"][0], win["dimensions"][1])
        except _ctypes.COMError as e:
            if e.hresult != -2147220991: raise e
            raise WindowNotExistant()



# ------------------------------------- Reproducer --------------------------------------------------

# Ensures that the window is in the same state as it was when the window was recorded, thus Reproducer-Quality-Ensurance.
# Use subclass ReproductionResolver, the 'Base' doesn't function.
class BaseReproductionResolver():
    
    def __init__(self, command_callback):
        self.print_cmd = command_callback
        self._resolve_cb = None


    # path of currently entered simulation    
    def _get_path(self):
        file = config_manager.get_simulation()
        if not file: raise Exception('No simulation file specified.')
        return f"{PathConstants().get_savename()}{file}.json"
        
    
    # ==== resolve all pools =====>

    
    # called at beginning of simulation
    def resolve_and_ready_up_windows(self, then: typing.Callable[..., typing.Any], failed: typing.Callable[..., typing.Any]) -> None:
        # setup
        SimHandleOperator.reset_handles()
        path = self._get_path()
        problem_pools = WindowCollections.collect_pools(path)
        iterator = iter(problem_pools)
        solution = dict()
        self._resolve_and_ready_up_windows(problem_pools, iterator, solution, then, failed)

    
    # keeps a chain of callbacks, 
    # if it ends without being finished (StopIteration executed), it will be called later when front-end returns answer
    def _resolve_and_ready_up_windows(self, problem_pools, iterator, solution, then, failed):
        try: 
            while True:
                process = next(iterator)
                continue_pools = self._resolve_from_process(problem_pools, process, iterator, solution, then, failed)
                if not continue_pools: break
        except StopIteration:
            self._after_resolving_stop(problem_pools, solution, then, failed)


    def _after_resolving_stop(self, problem_pools, solution, then, failed):
        guide = WindowCollections.create_win_relations(problem_pools, solution)
        try:
            Reproducer.reproduce(guide)
        except WindowNotExistant:
            print(f"1 special-end 8", flush=True)
            return failed()
        return then()

        
    # ===== process-wins resolving ====>
    
        
    def _resolve_from_process(self, problem_pools, process, iterator, solution, then: typing.Callable[..., typing.Any], failed):
        active_wins = problem_pools[process][1]
        queue = active_wins.copy()
        solution[process] = []
        return self._process_iteration(problem_pools, queue, process, iterator, solution, then, failed)

    
    def _process_iteration(self, problem_pools, queue, process, iterator, solution, then: typing.Callable[..., typing.Any], failed, async_behavior=False, loop_index=0):
        callback = lambda: self._resolve_window(problem_pools, queue, process, iterator, solution, then, failed, loop_index)

        # callback-chain, methods are responsible for directing the next step with returning a method, else stop or go asynchronous
        while callback:
            callback = callback()

        saved_wins = problem_pools[process][0]
        pool_end = len(solution[process]) == len(saved_wins)

        # '_resolve_and_ready_up_windows()' usually loops these methods for all processes, but in async the method has to be called again
        # in async, it can't default call the mentioned method, because the iterator would go to the next process, although this process hasn't resolved yet
        if async_behavior and pool_end:
            return self._resolve_and_ready_up_windows(problem_pools, iterator, solution, then, failed)
        return pool_end
    
    
    def _resolve_window(self, problem_pools, queue, process, iterator, solution, then: typing.Callable[..., typing.Any], failed, pos):
        saved, cached, selection = self._select_setup(problem_pools, queue, process, pos)

        if pos >= len(saved): return
        if not len(queue):
            return self._request_retry_async(problem_pools, queue, process, iterator, solution, then, failed, pos)
        if not selection: selection = queue

        if len(selection) > 1:
            return self._request_select_async(problem_pools, queue, process, iterator, solution, then, failed, pos)

        solution[process].append(cached.index(selection[0]))
        queue.remove(selection[0])
        return lambda: self._resolve_window(problem_pools, queue, process, iterator, solution, then, failed, pos+1)



    # ========= resolving goes async ==========>


    '''
    called when program receives answer
    '''
    def resolve_wrapper(self, arg):
        try:
            self._resolve_cb(arg)
        except SystemExit: pass
        except Exception:
            sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")
            self.print_cmd("special-end 5")


    def _select_setup(self, problem_pools, queue, process, pos):
        saved = problem_pools[process][0]
        cached =  problem_pools[process][1]
        if pos >= len(saved): return saved, cached, None
        selection = self._get_narrowed_selection(saved[pos], queue)
        return saved, cached, selection
    

    def _request_select_async(self, problem_pools, queue, process, iterator, solution, then, failed, pos):
        saved, cached, selection = self._select_setup(problem_pools, queue, process, pos)
        if not selection: selection = queue

        def continue_selection(result):
            num = cached.index(selection[result]) if result >=0 else -1
            solution[process].append(num)
            if result:
                queue.remove(selection[result])
            self._process_iteration(problem_pools, queue, process, iterator, solution, then, failed, async_behavior=True, loop_index=pos+1)

        self._resolve_cb = continue_selection
        self.send_file("selection", saved[pos], selection, process, pos+1)

    
    def _request_retry_async(self, problem_pools, queue, process, iterator, solution, then, failed, pos):
        saved = problem_pools[process][0]
        proceed = lambda x: self._process_iteration(problem_pools, queue, process, iterator, solution, then, failed, async_behavior=True, loop_index=pos+x)

        def call_later(retry: bool):
            if not retry:
                solution[process].append(-1)
                return proceed(1)
            self._refresh_process_wins(problem_pools[process][1], queue, process)
            proceed(0)
            
        self._resolve_cb = call_later 
        self.send_file("empty", saved[pos], [], process, pos+1)

    
    # override
    def send_file(self, query, old_win, selection, process_name, winNo):
        pass

    # override
    def process_response(self, id: int):
        pass

    
    # ==== pool matching utils ==>
        

    def _refresh_process_wins(self, old_collection, queue, process):
        old_hwnds = list(map(lambda w: w.handle, old_collection))
        for win in WindowCollections.get_all_from_process(process):
            if win.handle not in old_hwnds:
                old_collection.append(win)
                queue.append(win)

                
    def _get_narrowed_selection(self, rec, queue):
        if self._title_match(rec["name"], queue):
            return self._filter_only_matching_windows(rec["name"], queue)
        return []

    
    def _filter_only_matching_windows(self, name, selection):
        return list(filter(lambda x: x.window_text().encode("ascii", "ignore").decode() == name, selection))

    
    def _title_match(self, title, selection):
        for win in selection:
            # ignores troublesome characters same way as the titles from the recording
            current_title = win.window_text().encode("ascii", "ignore").decode()
            if current_title == title:
                return True
        return False

    


class ReproductionResolver(BaseReproductionResolver):


    def __init__(self, command_callback):
        super().__init__(command_callback)


    # ========== sending  ======>


    def send_file(self, query, old_win, selection, process_name, winNo):
        info_map = self._prepare_file_info(query, old_win, selection, process_name, winNo)
        resID = config_manager.assign_resolve_id()
        filename = PathConstants().get_resolvename() + str(resID) + ".json"
        with open(filename, 'w') as file:
            file.write(json.dumps(info_map))
        self.print_cmd("reproducer_resolve_window", args=resID)

        
    def _prepare_file_info(self, query: str, old_win, selection, process_name, winNo):
        info_map = {
            "query": query,
            "recorded": old_win["name"],
            "z_index": old_win["z_index"],
            "process_name": process_name,
            "winNo": winNo,
            "selection": []
        }
        for win in selection:
            info_map["selection"].append([win.window_text(), win.handle])
        return info_map

    
    # ========== catch answer =========> 


    def process_response(self, id: int):
        filename = PathConstants().get_resolvename() + "r" + str(id) +".json"
        with open(filename, 'r') as file:
            response = json.loads(file.read())
            answer = self.transform_answer(response["result"])
        self._delete_cache_files(id)
        threading.Thread(target=lambda:self.resolve_wrapper(answer)).start()
        

    def transform_answer(self, answer):
        if type(answer) is int:
            return int(answer)
        return bool(answer)


    def _delete_cache_files(self, id):
        def do(flag):
            starter = "r" if flag else ""
            file = PathConstants().get_resolvename() + starter + str(id) + ".json"
            if os.path.exists(file): os.remove(file)
        do(True); do(False)
            
