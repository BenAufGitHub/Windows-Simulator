import json, os
from Lib import traceback, typing, threading
from Lib.sysconfig import sys

from utils import config_manager
from utils.rt import PathConstants
from utils.app_errors import *

from desktop.utils import SimHandleOperator, WindowCollections
from desktop.base import Reproducer


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
            