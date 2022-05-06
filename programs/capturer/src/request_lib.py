from pywinauto import Desktop, uia_defines, findwindows
import win32gui, win32con
import win32api
import win32process

session_hwnd = dict()
session_names = dict()

def find_window(window_title, process_name):
    windows = Desktop(backend="uia").windows()
    normal_windows = list(filter(lambda win: _is_normal_win(win), windows))
    corresponding = list(filter(lambda w: w.window_text() == window_title, normal_windows))
    if len(corresponding) != 0:
        session_hwnd[window_title] = corresponding[0].handle
        return window_title
    corresponding = list(filter(lambda w: get_proc_name_by_hwnd(w.handle) == process_name, normal_windows))
    if len(corresponding) != 0:
        session_hwnd[corresponding[0].window_text()] = corresponding[0].handle
        return corresponding[0].window_text()
    return None

def add_to_session(win):
    name = win.window_text().encode("ascii", "ignore").decode()
    session_names[name] = win.window_text()
    session_hwnd[win.window_text()] = win.handle

def get_filtered_window_collection():
    windows = Desktop(backend="uia").windows()
    normal_windows = filter(lambda win: _is_normal_win(win), windows)
    normal_windows = list(normal_windows)
    for win in normal_windows:
        add_to_session(win)
    return map(lambda w: w.window_text(), normal_windows)

def _is_normal_win(win):
    try:
        proc = get_proc_name_by_hwnd(win.handle)
        if proc.find("electron.exe") != -1: return False
        return win.get_show_state() != None
    except uia_defines.NoPatternInterfaceError:
        return

def is_current_win(win_name):
    if win_name in session_names.keys() or win_name in session_hwnd.keys():
        return True
    return False

def maximize(win_name):
    if win_name in session_names:
        win_name = session_names[win_name]
    win32gui.ShowWindow(session_hwnd[win_name], win32con.SW_MINIMIZE)
    win32gui.ShowWindow(session_hwnd[win_name], win32con.SW_MAXIMIZE)
    # win32gui.SetForegroundWindow(session_data[win_name])

def get_proc_name_by_hwnd(hwnd):
    pid = win32process.GetWindowThreadProcessId(hwnd)
    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid[1])
    return win32process.GetModuleFileNameEx(handle, 0)
