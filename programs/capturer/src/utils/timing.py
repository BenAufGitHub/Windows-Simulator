import time, sys
from Lib import traceback
from Lib.threading import Thread

_print_pause_stats = False


class SimpleTimeKeeper:
    def __init__(self):
        self.start = time.time()
        self.pause_start = None
        # resets on new execution
        self.pause_length = 0
        # never gets reset
        self.total_pause = 0

    def register_pause(self):
        if self.pause_start: return
        self.pause_start = time.time()

    def register_resume(self):
        if not self.pause_start: return
        curr_pause = time.time() - self.pause_start
        self.total_pause += curr_pause
        self.pause_start = None

    # returns total execution time from instantiation
    def get_exec_time(self):
        last_exec_time = time.time() if not self.pause_start else self.pause_start
        return last_exec_time - (self.total_pause + self.start)


class TaskAwaitingTimeKeeper(SimpleTimeKeeper):

    def __init__(self):
        super().__init__()
        self.callback = lambda: self.pause_start != None
        self.exec_start = None
        self.exec_length = None

    def register(self, time_amount):
        self.exec_start = time.time()
        self.exec_length = time_amount
        
    def unregisterExecution(self):
        self.exec_start = None
        self.exec_length = 0
        self.pause_length = 0


    # override
    # if resumed while awaiting execution, accumulate pause amounts to wait for again when execution thread wakes up
    def register_resume(self):
        if not self.pause_start: return
        if not self.exec_start:
            return super().register_resume() # is None
        beginning = max(self.pause_start, self.exec_start)
        curr_pause = time.time() - beginning
        self.pause_length += curr_pause
        self.total_pause += curr_pause
        self.pause_start = None


    # if thread wakes up while pause, how much time has been paused
    def calc_edge_remaining_sleep(self):
        passed_time = time.time() - self.exec_start
        remainder = self.exec_length - (passed_time - self.pause_length)

        if _print_pause_stats:
                self.output(passed_time, self.pause_length, self.exec_length, remainder)
        return max(0, remainder)


    def output(self, total, paused, exec_len, remainder):
        print(f"total time  : {total}")
        print(f"total paused: {paused}")
        print(f"exec duration: {exec_len}")
        print(f"That leaves {remainder} sec. to execute. ({exec_len+paused-total})")


    def sleep_until_instruction(self, amount):
        try:
            return self._sleep_until_instruction(amount)
        except SystemExit: pass
        except Exception as e:
            get_exc = traceback.format_exc()
            sys.stderr.write(get_exc)
            sys.stderr.flush()

    
    # return: whether the sleep is finished or needs to be picked up again later
    def _sleep_until_instruction(self, amount) -> bool:
        if amount < 0.008 and not self.callback():
            return True
        self.register(amount)
        time.sleep(amount)
        return self.sleep_async()


    # return: whether the sleep is finished or needs to be picked up again later
    def sleep_async(self) -> bool:
        if self.callback():
            return False
        remaining = self.calc_edge_remaining_sleep()
        if remaining > 0.015:
            time.sleep(remaining)
            return self.sleep_async()

        self.unregisterExecution()
        return True
        

