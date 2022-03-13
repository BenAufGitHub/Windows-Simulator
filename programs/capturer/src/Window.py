import tkinter
import KeyLogger
import os, threading, time

frames = dict()


class MenuFrame(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master=master)
        self.buttons = dict()
        self.order_grid()

    def order_grid(self):
        record = tkinter.Button(master=self, text="Record", command=self.start_recording)
        simulate = tkinter.Button(master=self, text="Simulate", command=self.start_simulating)

        record.grid(row=0, column=0, padx=10, pady=5, ipadx=20, ipady=12)
        simulate.grid(row=0, column=1, padx=10, pady=5, ipadx=20, ipady=12)
        self.buttons["record"] = record
        self.buttons["simulate"] = simulate

    def start_recording(self):
        set_active("disabled", self.buttons)
        frames["root"].iconify()
        raise_frame(frames["pause"])
        def invoke():
            KeyLogger.main(frames["pause"])
        threading.Thread(target=invoke, daemon=True).start()


    def start_simulating(self):
        set_active("disabled", self.buttons)
        frames["root"].iconify()
        raise_frame(frames["pause"])
        def invoke():
            MouseClicker.main(frames["pause"])
        threading.Thread(target=invoke, daemon=True).start()


class PauseFrame(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master=master, width=200, height=200)
        self.on_pause = False
        self.buttons = dict()
        self.order_grid()

    def order_grid(self):
        pause = tkinter.Button(master=self, text="pause", command=self.pause_toggle)
        stop = tkinter.Button(master=self, text="stop", command=self.stop)

        pause.grid(row=0, column=0, ipadx=20, ipady=12, padx=10, pady=5)
        stop.grid(row=0, column=1, ipadx=20, ipady=12,padx=10, pady=5)
        self.buttons["pause"] = pause
        self.buttons["stop"] = stop

    def pause_toggle(self):
        set_active("disabled", self.buttons)
        self.resuming() if self.on_pause else self.pausing()
        set_active("active", self.buttons)

    def resuming(self):
        self.buttons["pause"].config(text="pause") #TODO
        self.on_pause = False
        frames["root"].iconify()
        KeyLogger.resume()

    def pausing(self):
        self.buttons["pause"].config(text="resume") #TODO
        self.on_pause = True
        KeyLogger.pause()

    def stop(self):
        raise_frame(frames["menu"])
        KeyLogger.end()

    def on_call(self):
        frames["root"].deiconify()
        frames["root"].attributes("-topmost", True)
        self.pausing()



def set_active(state, buttons):
    for button in buttons:
        buttons[button]["state"] = state


def raise_frame(frame):
    set_active("active", frame.buttons)
    frame.tkraise()


def getRoot() -> tkinter.Tk:
    window = tkinter.Tk()
    window.title("ZabaG Bildschirm-Assistent")
    window.geometry("200x100")
    window.resizable(True, True)
    return window


def init_frames(window):
    frames["menu"] = MenuFrame(window)
    frames["menu"].grid(row=0, column=0, sticky='news')
    frames["pause"] = PauseFrame(window)
    frames["pause"].grid(row=0, column=0, sticky='news')

def init_window(window):
    pass
    # window.minSize()

def main():
    window = getRoot()
    init_window(window)
    init_frames(window)
    raise_frame(frames["menu"])
    frames["root"] = window
    window.mainloop()


if __name__ == '__main__':
    main()