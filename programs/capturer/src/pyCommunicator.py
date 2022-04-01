import sys, functools, threading
print = functools.partial(print, flush=True)

# all subthreads should go into this, so that they can be eliminated if necessary
active_threads = []


class InputStop(Exception):
    pass


def print_cmd(cmd: str):
    print(cmd)


def print_info(info: str):
    print(info)


def getStdin():
    return sys.stdin.readline().rstrip()


# TODO
def processIn(input):
    # TODO
    if input == 'exit':
        raise InputStop()


def main():
    try:
        while(True):
            input = getStdin()
            processIn(input)
    except InputStop:
        pass


if __name__ == '__main__':
    main()
