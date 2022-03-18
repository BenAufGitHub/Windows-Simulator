import sys, threading
import functools
import KeyLogger, MouseClicker

print = functools.partial(print, flush=True)
request = KeyLogger.request if sys.argv[1] == "record" else MouseClicker.request


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
        threading.Thread(target=MouseClicker.main, daemon=False).start()
    else:
        threading.Thread(target=KeyLogger.main, daemon=False).start()


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
