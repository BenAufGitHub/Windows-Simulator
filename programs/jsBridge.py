import sys
import functools
print = functools.partial(print, flush=True)

class InputStop (RuntimeError):
    pass

def listen():
    line = sys.stdin.readline().rstrip()
    execute(line)
    if line == 'stop':
        raise InputStop()


def execute(line: str):
    pass


def main():
    print("bridge started")
    try:
        while(True):
            listen()
    except InputStop:
        print("End of Py-App")


if __name__ == '__main__':
    main()