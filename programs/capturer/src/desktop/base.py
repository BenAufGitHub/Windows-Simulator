from pywinauto import controls, uia_element_info

import json, _ctypes

from utils.rt import PathConstants
import utils.win_utils as win_utils
from utils.app_errors import *

from desktop.utils import SimHandleOperator, ReproducerGuide


''' ---------------------- Saving ------------------------ '''


class WindowSaver:

    _window_dict = dict()

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
    def reset_handle():
        WindowSaver._window_dict = dict()


    @staticmethod
    def set_window_number(handle, number):
        WindowSaver._window_dict[handle] = number


    def save_current_win_status(self, path) -> bool:
        try:
            wins = win_utils.get_ordered_wins()
            for index, win in enumerate(wins):
                WindowSaver.set_window_number(win.handle, index)
            self._enter_windows_into_file(wins, path)
            return True
        except _ctypes.COMError as e:
            if e.hresult == -2147220991: return False
            raise e



    def _enter_windows_into_file(self, windows, path):
        with open(path, "w") as file:
            file.write("[")
            for index, win in enumerate(windows):
                if index != 0:
                    file.write(",")
                win_properties = self._get_win_properties_as_dict(win, index)
                file.write(json.dumps(win_properties))
            file.write("]")


    def _get_win_properties_as_dict(self, win, z_index):
        win_name = win.window_text().encode("ascii", "ignore").decode()
        process_name = win_utils.get_proc_name_by_hwnd(win.handle)

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


    def save_screenshot(self, windex, filepath):
        hwnd = self.get_handle(windex)
        if hwnd == None: return
        info = uia_element_info.UIAElementInfo(handle_or_elem=hwnd)
        wrapper = controls.hwndwrapper.HwndWrapper(info)
        image = wrapper.capture_as_image(wrapper.rectangle())
        path = PathConstants().get_screenshot_name() + filepath + '/'
        image.save(f"{path}{windex}.jpg", quality=10)



''' ---------------------- Reproducing ------------------------- '''



class Reproducer:


    @staticmethod
    def reproduce(guide: ReproducerGuide):
        Reproducer.minimize_non_active(guide)
        for win_key in reversed(sorted(guide.get_ids())):

            saved = guide.get_saved(win_key)
            active = guide.get_matched(win_key)
            if not active: continue

            Reproducer._reproduce(saved, active)

    
    @staticmethod
    def minimize_non_active(guide: ReproducerGuide):
        wins = win_utils.get_ordered_wins()
        get_handle = lambda id: guide.get_matched(id).handle
        matched = filter(lambda id: guide.get_matched(id), guide.get_ids())
        handles = list(map(get_handle, matched))
        for w in wins:
            if w.handle not in handles:
                win_utils.minimize_no_err(w)
     

    @staticmethod
    def _reproduce(win, active_win):
        SimHandleOperator.set_window_handle(win["z_index"], active_win.handle)
        # if process has been eliminated during this process
        if active_win.element_info.process_id == None: raise WindowNotExistant()
        try:
            if win["max"]: 
                return win_utils.maximize_win(active_win)
            win_utils.show_win_as_rect(active_win, win["coordinates"][0], win["coordinates"][1], win["dimensions"][0], win["dimensions"][1])
        except _ctypes.COMError as e:
            if e.hresult != -2147220991: raise e
            raise WindowNotExistant()
