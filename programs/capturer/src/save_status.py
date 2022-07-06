from pywinauto import Desktop, uia_defines, findwindows, controls
import win32gui, win32con
import win32api, ctypes
import win32process
import json

ctypes.windll.shcore.SetProcessDpiAwareness(2)

class Constants:
    def __init__(self):
        self._save_file = "window_start_capture.json"
    
    def get_filename(self):
        return self._save_file


class WindowSaver:
    def save_current_win_status(self):
        self._enter_windows_into_file(WinUtils.get_ordered_wins())



    def _enter_windows_into_file(self, windows):
        with open(Constants().get_filename(), "w") as file:
            file.write("[")
            for index, win in enumerate(windows):
                if index != 0:
                    file.write(",")
                win_properties = self._get_win_properties_as_dict(win, index)
                file.write(json.dumps(win_properties))
            file.write("]")


    def _get_win_properties_as_dict(self, win, z_index):
        win_name = win.window_text().encode("ascii", "ignore").decode()
        process_name = WinUtils.get_proc_name_by_hwnd(win.handle)
        coordinates = (win.rectangle().left, win.rectangle().top)
        dimensions = (win.rectangle().width(), win.rectangle().height())
        return {
            "name": win_name,
            "process": process_name,
            "coordinates": coordinates,
            "dimensions": dimensions,
            "z_index": z_index
        }




class WindowReproducer():
    def reproduce_window_states(self):
        self._minimize_all_windows()
        with open(Constants().get_filename(), "r") as file:
            windows = json.loads(file.readline())
            found_windows = WinUtils.get_ordered_wins()
            for win in reversed(windows):
                self._reproduce(win, found_windows)

    def _minimize_all_windows(self):
        for handle in WinUtils.get_windows_in_z_order_ctypes():
            try:
                if not WinUtils.is_normal_win(findwindows.find_window(handle=handle)): raise Exception() 
                win32gui.ShowWindow(handle, win32con.SW_MINIMIZE)
            except:
                pass

    def _reproduce(self, win, found_windows):
        width = win["dimensions"][0]
        height = win["dimensions"][1]
        x = win["coordinates"][0]
        y = win["coordinates"][1]
        
        if width == 0 == height: return

        window = WinUtils.find_window(win["name"], win["process"], found_windows)
        if not window:
            print(win["name"] + " not found")
            return

        wrapper = controls.hwndwrapper.HwndWrapper(window.element_info)
        wrapper.restore()
        wrapper.move_window(x=x, y=y, width=width, height=height, repaint=True)

                

# ====================================== UTILS =======================================


class WinUtils:

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
            try:
                proc = WinUtils.get_proc_name_by_hwnd(win.handle)
                if proc.find("electron.exe") != -1: return False
                return win.get_show_state() != None
            except uia_defines.NoPatternInterfaceError:
                return


    @staticmethod
    def get_proc_name_by_hwnd(hwnd):
            pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid[1])
            full_name = win32process.GetModuleFileNameEx(handle, 0)
            return WinUtils.filter_exec_title(full_name)


    @staticmethod
    def sort_per_z_axis(windows):
            Z_windows = WinUtils.get_windows_in_z_order_ctypes()
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
        windows = Desktop(backend="uia").windows()
        normal_windows = filter(lambda win: WinUtils.is_normal_win(win), windows)
        normal_windows = list(normal_windows)
        return WinUtils.sort_per_z_axis(normal_windows)


    @staticmethod
    def find_window(name, process, windows):
        try:
            win_titles = list(map(lambda win: WinUtils.get_title(win), windows))
            pos = win_titles.index(name)
            return windows.pop(pos)
        except ValueError:
            try:
                pos = list(map(lambda win: WinUtils.get_proc_name_by_hwnd(win.handle), windows)).index(process)
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


def main():
    # WindowReproducer().reproduce_window_states()
    WindowSaver().save_current_win_status()

if __name__ == '__main__':
    main()
