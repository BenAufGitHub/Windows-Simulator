from pywinauto import Desktop, uia_defines, findwindows, controls, uia_element_info
import win32gui, win32con
import win32api, ctypes
import win32process
import json, time

ctypes.windll.shcore.SetProcessDpiAwareness(2)

class Constants:
    def __init__(self):
        self._save_file = "./resources/window_start_capture.json"
        self._screenshots = "./resources/screenshots/"
    
    def get_savename(self):
        return self._save_file

    def get_screenshot_name(self):
        return self._screenshots


class WindowSaver:

    _window_dict = dict()
    _cached_window_positions_for_pause = None

    # get the z_index noted at the start of the recording for the given window
    @staticmethod
    def get_window_number(handle: int):
        if not handle in WindowSaver._window_dict:
            return -1
        return WindowSaver._window_dict[handle]


    @staticmethod
    def get_handle(windex):
        is_answer = lambda h: WindowSaver._window_dict[h] == windex
        l = list(filter(is_answer, WindowSaver._window_dict.keys()))
        if not l: return None
        return l[0]



    @staticmethod
    def set_window_number(handle, number):
        WindowSaver._window_dict[handle] = number


    def save_current_win_status(self):
        wins = WinUtils.get_ordered_wins()
        for index, win in enumerate(wins):
            WindowSaver.set_window_number(win.handle, index)
        self._enter_windows_into_file(wins)



    def _enter_windows_into_file(self, windows):
        with open(Constants().get_savename(), "w") as file:
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

        if win.is_maximized():
            return {"name": win_name, "process": process_name, "max": True, "z_index": z_index}

        coordinates = (win.rectangle().left, win.rectangle().top)
        dimensions = (win.rectangle().width(), win.rectangle().height())

        return {
            "name": win_name,
            "process": process_name,
            "max": False,
            "coordinates": coordinates,
            "dimensions": dimensions,
            "z_index": z_index
        }


    def save_screenshot(self, windex):
        hwnd = self.get_handle(windex)
        if hwnd == None: return
        info = uia_element_info.UIAElementInfo(handle_or_elem=hwnd)
        wrapper = controls.hwndwrapper.HwndWrapper(info)
        image = wrapper.capture_as_image(wrapper.rectangle())
        image.save(f"{Constants()._screenshots}{windex}.jpg", quality=30)
        

    
    # ===================== saving windows for pausing ===========================


    def save_windows_for_pause(self):
        WindowSaver._cached_window_positions_for_pause = self._get_current_windows()

    @staticmethod
    def get_cached_wins():
        return WindowSaver._cached_window_positions_for_pause

    @staticmethod
    def clear_cache_for_pause():
        WindowSaver._cached_window_positions_for_pause = None

    def _get_current_windows(self):
        winlist = list()
        windows = WinUtils.get_ordered_wins()
        for zindex, win in enumerate(windows):
            wininfo = self._get_positional_properties(win, zindex)
            winlist.append(wininfo)
        return winlist

    def _get_positional_properties(self, win, zindex):
        if win.is_maximized(): return {"ref": win, "max": True, "z": zindex}
        return {
            "ref": win,
            "max": False,
            "x": win.rectangle().left,
            "y": win.rectangle().top,
            "z": zindex,
            "width": win.rectangle().width(),
            "height": win.rectangle().height()
        }





class WindowReproducer():
     

    _window_dict = dict()
    _hwnd_values = []


    @staticmethod
    def get_handle(z_index: int):
        if(z_index == -1):
            return None
        return WindowReproducer._window_dict[z_index]


    @staticmethod
    def is_hwnd_match(z_index, clicked_handle):
        # -2 represents that the window doesnt matter
        if z_index == -2: return True
        if WindowReproducer.get_handle(z_index) == None:
            return not (clicked_handle in WindowReproducer._hwnd_values)
        return WindowReproducer.get_handle(z_index) == clicked_handle


    @staticmethod
    def set_window_handle(number, handle):
        WindowReproducer._window_dict[number] = handle
    
    def reproduce_window_states(self):
        self._minimize_all_windows()
        with open(Constants().get_savename(), "r") as file:
            windows = json.loads(file.readline())
            found_windows = WinUtils.get_ordered_wins()
            self._replicate_window_pool(windows, found_windows)

    def get_unresolved_pools(self):
        # list entries: [list process_name_saved, list process_name_available]
        old_windows = None
        with open(Constants().get_savename(), "r") as file:
            old_windows = json.loads(file.readline())
        found_windows = WinUtils.get_ordered_wins()
        return self._group_together(old_windows, found_windows)

    def _group_together(self, saved, found):
        groupings = dict()
        for win in saved:
            process = win["process"].lower()
            if process not in groupings:
                groupings[process] = (list(), list())
            groupings[process][0].append(win)
        for win in found:
            process = WinUtils.get_proc_name_by_hwnd(win.handle).lower()
            if process in groupings:
                groupings[process][1].append(win)
        return groupings


    def get_resolved_map(self, groups, solutions):
        resolved_map = dict()
        for group_name in groups:
            group = groups[group_name]
            resolved_wins = len(group[0])
            for i in range(resolved_wins):
                answer = solutions[group_name][i]
                if answer == -1:
                    resolved_map[group[0][i]["z_index"]] = None
                    continue
                resolved_map[group[0][i]["z_index"]] = (group[0][i], group[1][answer])
        return resolved_map


    def replicate_map(self, mapping):
        self._replicate_full_map(mapping)


    def _replicate_window_pool(self, windows, found_windows):
        window_mapping = dict()
        while(windows):
            win0 = windows.pop()
            process0 = win0["process"].lower()
            # find window with same process name, hoping the '*' works as spread fine
            recorded_wins_from_process = [win0, *(self._pop_wins_from_process(process0, windows))]
            available_wins_from_process = self._pop_available_from_pool(process0, found_windows)
            self._match(recorded_wins_from_process, available_wins_from_process, window_mapping)
        self._replicate_full_map(window_mapping)
    

    def _match(self, recorded_wins, available_wins, window_mapping):
        print("Matching windows from process: " + recorded_wins[0]["process"])
        for win in recorded_wins:
            if not available_wins: return
            print(f"Looking for '{win['name']}' with available matches:")
            for i, win2 in enumerate(available_wins):
                print(f"{i}: {win2.window_text()}")
            str_num = input("Enter the number of the window you want to match: ")
            num = int(str_num)
            window_mapping[win["z_index"]] = (win, available_wins.pop(num))
        

    def _replicate_full_map(self, window_mapping):
        for win_key in reversed(window_mapping.keys()):

            if not window_mapping[win_key]:
                continue
            saved, active = window_mapping[win_key]
            self._reproduce(saved, active)



    # from the recording pool
    def _pop_wins_from_process(self, process, windows):
        wins = list()
        i = 0
        while i < len(windows):
            if windows[i]["process"].lower() == process:
                wins.append(windows.pop(i))
            else:
                i += 1
        return wins

    def _pop_available_from_pool(self, process_name, pool):
        avail = list()
        i = 0
        while i < len(pool):
            if WinUtils.get_proc_name_by_hwnd(pool[i].handle).lower() == process_name:
                avail.append(pool.pop(i))
            else:
                i += 1
        return avail

    def _minimize_all_windows(self):
        # TODO maybe add a win+D press with pynput
        for win in WinUtils.get_ordered_wins():
            if not WinUtils.is_normal_win(win): 
                continue
            win32gui.ShowWindow(win.handle, win32con.SW_MINIMIZE)            

    def _reproduce(self, win, active_win):
        WindowReproducer.set_window_handle(win["z_index"], active_win.handle)
        WindowReproducer._hwnd_values.append(active_win.handle)
        # if window has been eliminated during this process
        if active_win.element_info.process_id == None: return
        if win["max"]:
            return self._reproduceMaximized(active_win)
        self.win_to_normalised_rect(active_win, win["coordinates"][0], win["coordinates"][1], win["dimensions"][0], win["dimensions"][1])


    def _reproduceMaximized(self, active_win):
        active_win.minimize()
        self._quick_wait(active_win.is_minimized)
        active_win.maximize()
        self._quick_wait(active_win.is_maximized)


    def win_to_normalised_rect(self, win, left, top, width, height):
        win.minimize()

        # apperently minimize is asynchronous or sth. so we need to wait it out, thx for not putting that into the docs...
        self._quick_wait(win.is_minimized)
        
        if width == 0 and 0 == height: return
        # may consider reactivating the restore function, but putting it away fixed an issue regarding windows not reappearing
        # active_win.restore()
        wrapper = controls.hwndwrapper.HwndWrapper(win.element_info)
        win32gui.ShowWindow(win.handle, win32con.SW_NORMAL)
        wrapper.move_window(x=left, y=top, width=width, height=height, repaint=True)
        self._quick_wait(win.is_normal)


    def _quick_wait(self, callback):
        t0 = time.time()
        while True:
            if callback() or time.time()-t0 > 0.1:
                break


    # ================= reproduction after pausing =============================


    def reproduce_windows_after_pause(self):
        if not WindowSaver.get_cached_wins():
            print("0 No cached windows to reproduce found while reproducing after pause.", flush=True)
            return
        winlist = WindowSaver.get_cached_wins()
        self._minimize_all_windows()
        for i, wininfo in enumerate(reversed(winlist)):
            if i + wininfo["z"] != len(winlist)-1:
                print("0 Aborting Window-Reproduction: list not z-ordered", flush=True)
                return
            self._replecate_win_after_pause(wininfo)
        WindowSaver.clear_cache_for_pause()


    def _replecate_win_after_pause(self, wininfo):
        if wininfo["ref"].element_info.process_id == None: return
        if wininfo["max"]:
            return self._reproduceMaximized(wininfo["ref"])
        self.win_to_normalised_rect(wininfo["ref"], wininfo["x"], wininfo["y"], wininfo["width"], wininfo["height"])


# ====================================== UTILS =======================================


class WinUtils:

    _desktop = Desktop(backend="uia")

    @staticmethod
    def get_top_from_point(x, y):
        return WinUtils._desktop.top_from_point(x, y)


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
        windows = WinUtils._desktop.windows()
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
    WindowReproducer().reproduce_window_states()
    # WindowSaver().save_current_win_status()



if __name__ == '__main__':
    problems = WindowReproducer().get_unresolved_pools()
    solution = {
        "code.exe": [0],
        "spotify.exe": [0]
    }
    win_map = WindowReproducer().get_resolved_map(problems, solution)
    print(win_map)
