'''
rt == RunTime
This files purpose is to keep singleton classes that contain information about the runtime or other runtime specific classes.
'''

import ctypes, sys, time
from Lib import threading, traceback


# this class counts which windows have been used during the recording
class ClickInfo():

    __shared_state = dict()
    __shared_state["_clicked_wins"] = set()

    def __init__(self):
        self.__dict__ = self.__shared_state

    def add_clicked_windex(self, windex: int):
        self._clicked_wins.add(windex)

    def clear_clicked_windecies(self):
        self._clicked_wins.clear()

    def get_clicked_windecies_list(self) -> list:
        copy = []
        copy.extend(self._clicked_wins)
        return copy

    def clicked_contains(self, windex: int) -> bool:
        return windex in self._clicked_wins


class MetaData:
    def __init__(self):
        self.record_path = "./resources/recordings/"
        self.window_unassigned_path = "./resources/resolves/"
        self.auto_time = 0.1
        self.start_time = time.time()


def stop_exec(bool, process, reason):
    if not bool: return
    # eliminate python-side
    process.request("stop", flush=False)
    # inform front-end
    process.print_cmd(f"special-end {reason}")


# class taken from https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
class KillableThread(threading.Thread):
    def __init__(self, callback):
        threading.Thread.__init__(self)
        self.callback = callback
             
    def run(self):
        # target function of the thread class
        try:
            func = self.callback
            func()
        except SystemExit: pass
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