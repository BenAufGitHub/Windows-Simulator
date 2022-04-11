from pywinauto import Desktop, uia_defines

def get_filtered_window_collection():
    windows = Desktop(backend="uia").windows()
    normal_windows = filter(lambda win: _is_normal_win(win), windows)
    return map(lambda w: w.window_text(), normal_windows)

def _is_normal_win(win):
    try:
        return win.get_show_state() != None
    except uia_defines.NoPatternInterfaceError:
        return