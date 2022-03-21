from math import remainder
import time

class TimeKeeper:

    def __init__(self, onpause_callback):
        self.start = time.time()
        self.callback = lambda: self.pause_start == None
        self.exec_start = None
        self.exec_length = None

        self.pause_start = None
        self.pause_length = 0


    def register(self, time_amount):
        self.exec_start = time.time()
        self.exec_length = time_amount
        

    def register_pause(self):
        if self.pause_start != None: return
        self.pause_start = time.time()

    def register_resume(self):
        if self.pause_start == None: return
        self.pause_length += time.time() - self.pause_start
        self.pause_start = None

    # if thread wakes up while pause, how much time has been paused
    def calc_edge_remaining_sleep(self):
        passed_time = time.time() - self.exec_start
        remainder = self.exec_length - (passed_time - self.pause_length)
        if remainder >= 0.02:
            return remainder
        return 0


    # after sleep, there might be another sleep period
    def calc_remaining_sleep(self):
        if(self.callback()):
            self.wait_until_unpause()
        return self.calc_edge_remaining_sleep()
        


    def wait_until_unpause(self):
        while True:
            if not self.callback:
                break

    def sleep_until_ready(self, amount):
        if amount < 0.02:
            return
        self.register(amount)
        time.sleep(amount)
        remaining = self.calc_remaining_sleep()
        while remaining > 0.015:
            time.sleep(remaining)
            remaining = self.calc_remaining_sleep()
        self.pause_length = 0
    