import sys, threading
import functools
import Recorder, Simulator

print = functools.partial(print, flush=True)
request = Recorder.request if sys.argv[1] == "record" else Simulator.request


class InputStop (RuntimeError):
    pass


def listen():
    line = sys.stdin.readline().rstrip()
    execute(line)
    if line == 'stop':
        raise InputStop()


def execute(line: str):
    if line == 'pause':
        request("pause")
    if line == 'resume':
        request("resume")
    if line == 'stop':
        request("stop")


def run():
    if(sys.argv[1] == 'simulate'):
        threading.Thread(target=Simulator.main, daemon=False).start()
    else:
        threading.Thread(target=Recorder.main, daemon=False).start()


def main():
    print("bridge started")
    run()
    try:
        while(True):
            listen()
    except InputStop:
        print("End of Py-App")


if __name__ == '__main__':
    main()
