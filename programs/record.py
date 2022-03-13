import sys, threading, os, time
import functools
print = functools.partial(print, flush=True)

def listen():
    loop:
    while(True):
        for line in sys.stdin:
            if(line=="stop"):
                break loop
            execute(line)


def execute(line: str):
    time.sleep(2)
    print(line, flush=True)



if __name__ == '__main__':
    execute("pause")
