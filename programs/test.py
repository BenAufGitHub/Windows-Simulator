import sys

class InputStop (RuntimeError):
    pass

def listen():
    line = sys.stdin.readline().rstrip()
    print(f"|{line}|", flush=True)
    if line == 'stop':
        raise InputStop()

print("test", flush=True)

try:
    while(True):
        listen()
except InputStop:
    print("End of Py-App", flush=True)