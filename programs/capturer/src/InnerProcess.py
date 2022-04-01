import ctypes
import JSONHandler


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

    def request(self, arg: str):
        if self.state == "stop" or not self.ready: return
        paused = self.state == 'paused'
        if arg == 'pause' and not paused:
            self.pause()
        if arg == 'resume' and paused:
            self.resume()
        if arg == 'stop':
            self.request("pause")
            self.end()

    # overwrite for functionality
    def pause(self): pass
    def resume(self): pass
    def end(self): pass

    # overwrite to match 
    def run():
        pass

    def get_data(self, process):
        return JSONHandler.MetaData(process == 'recording')



# very important method, influences how windows scale is perceived
def config_monitor():
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
