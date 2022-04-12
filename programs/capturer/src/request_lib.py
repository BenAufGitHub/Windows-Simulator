from pywinauto import Desktop, uia_defines, findwindows
import win32gui, win32con

session_data = dict()

def add_to_session(win):
    name = win.window_text().encode("ascii", "ignore").decode()
    session_data[name] = win.handle

def get_filtered_window_collection():
    windows = Desktop(backend="uia").windows()
    normal_windows = filter(lambda win: _is_normal_win(win), windows)
    normal_windows = list(normal_windows)
    for win in normal_windows:
        add_to_session(win)
    return map(lambda w: w.window_text(), normal_windows)

def _is_normal_win(win):
    try:
        return win.get_show_state() != None
    except uia_defines.NoPatternInterfaceError:
        return

def is_current_win(win_name):
    if win_name in session_data.keys():
        maximize(win_name)
        return True
    return False

def maximize(win_name):
    win32gui.ShowWindow(session_data[win_name], win32con.SW_MAXIMIZE)
