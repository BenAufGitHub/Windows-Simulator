from pywinauto import Desktop, uia_defines, controls, uia_element_info
import win32gui, win32con
import win32api, ctypes, _ctypes
import win32process

import time
from Lib import traceback
from Lib.sysconfig import sys


_desktop = Desktop(backend="uia")


@staticmethod
def get_top_from_point(x, y):
    return _desktop.top_from_point(x, y)


@staticmethod
def get_windows_in_z_order_ctypes():
    '''Returns windows in z-order (top first)'''
    user32 = ctypes.windll.user32
    lst = []
    top = user32.GetTopWindow(None)
    if not top:
        return lst
    lst.append(top)
    while True:
        next = user32.GetWindow(lst[-1], win32con.GW_HWNDNEXT)
        if not next:
            break
        lst.append(next)
    return lst


@staticmethod
def is_normal_win(win):
    # if type(win) != 'pywinauto.controls.uiawrapper.UIAWrapper': return
    try:
        proc = get_proc_name_by_hwnd(win.handle)
        if not proc: return False
        if proc.find("electron.exe") != -1: return False
        return win.get_show_state() != None
    except uia_defines.NoPatternInterfaceError:
        return


@staticmethod
def get_proc_name_by_hwnd(hwnd):
    pid = win32process.GetWindowThreadProcessId(hwnd)
    if not pid[0] or not pid[1]: return
    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid[1])
    full_name = win32process.GetModuleFileNameEx(handle, 0)
    return filter_exec_title(full_name)


@staticmethod
def sort_per_z_axis(windows):
        Z_windows = get_windows_in_z_order_ctypes()
        sorted = list()
        hwnds_of_windows = list(filter(lambda w: w.handle, windows))
        for win_handle in Z_windows:
            if not (win_handle in hwnds_of_windows): continue
            pos = hwnds_of_windows.index(win_handle)
            hwnds_of_windows.pop(pos)
            sorted.append(windows.pop(pos))
        sorted.extend(windows)
        return sorted


@staticmethod
def get_ordered_wins():
    windows = _desktop.windows()
    normal_windows = filter(lambda win: is_normal_win(win), windows)
    normal_windows = list(normal_windows)
    return sort_per_z_axis(normal_windows)


@staticmethod
def find_window(name, process, windows):
    try:
        win_titles = list(map(lambda win: get_title(win), windows))
        pos = win_titles.index(name)
        return windows.pop(pos)
    except ValueError:
        try:
            pos = list(map(lambda win: get_proc_name_by_hwnd(win.handle), windows)).index(process)
            return windows.pop(pos)
        except ValueError:
            return None


@staticmethod
def get_title(window):
    return window.window_text().encode("ascii", "ignore").decode()

# Splits process name from its path
@staticmethod
def filter_exec_title(title):
    return title.split("\\")[-1]


@staticmethod
def minimize_all_windows():
    for win in get_ordered_wins():
        if not is_normal_win(win): 
            continue
        win32gui.ShowWindow(win.handle, win32con.SW_MINIMIZE)    


@staticmethod 
def minimize_no_err(win):
    try:
        if win.is_minimized(): return
        win.minimize()
    except SystemExit: pass
    except Exception as e:
        sys.stderr.write(f"ONLY-DISPLAY{traceback.format_exc()}")
        sys.stderr.flush()


@staticmethod
def quick_wait_ui(callback, seconds=0.3):
    t0 = time.time()
    while True:
        if callback() or time.time()-t0 > seconds:
            break


@staticmethod
def maximize_win(active_win):
    active_win.minimize()
    quick_wait_ui(active_win.is_minimized)
    active_win.maximize()
    quick_wait_ui(active_win.is_maximized)


@staticmethod
def show_win_as_rect(win, left, top, width, height):
    win.minimize()

    # apperently minimize is asynchronous or sth. so we need to wait it out, thx for not putting that into the docs...
    quick_wait_ui(win.is_minimized)
    
    if width == 0 and 0 == height: return
    # may consider reactivating the restore function, but putting it away fixed an issue regarding windows not reappearing
    # active_win.restore()
    wrapper = controls.hwndwrapper.HwndWrapper(win.element_info)
    win32gui.ShowWindow(win.handle, win32con.SW_NORMAL)
    wrapper.move_window(x=left, y=top, width=width, height=height, repaint=True)
    quick_wait_ui(win.is_normal)


# return: True if successful
@staticmethod
def show_window_at_curser(hwnd) -> bool:
    try:
        info = uia_element_info.UIAElementInfo(handle_or_elem=hwnd)
        wrapper = controls.hwndwrapper.HwndWrapper(info)
        x, y = win32api.GetCursorPos()
        width = wrapper.rectangle().width()
        height = wrapper.rectangle().height()
        show_win_as_rect(wrapper, x, y, width, height)
        return True
    except _ctypes.COMError as e:
        if e.hresult == -2147220991: return False # window won't be shown no error raised
        raise e