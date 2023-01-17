from pywinauto import handleprops, base_wrapper

import json, _ctypes

from ..utils import win_utils
from ..utils.app_errors import *



class SimHandleOperator():

    _window_dict = dict()


    @staticmethod
    def get_handle(z_index: int):
        if(z_index == -1):
            return None
        return SimHandleOperator._window_dict[z_index]

    
    @staticmethod
    def has(z_index):
        return z_index in SimHandleOperator._window_dict

    @staticmethod
    def has_handle(handle):
        return handle in SimHandleOperator._window_dict.values()

    @staticmethod
    def reset_handles():
        SimHandleOperator._window_dict = dict()

    @staticmethod
    def is_handle_match(z_index, clicked_handle):
        # -2 represents that the window doesnt matter
        if z_index == -2: return True
        if z_index >= 0 and not SimHandleOperator.has(z_index):
            return False
        if SimHandleOperator.get_handle(z_index) == None:
            return not (SimHandleOperator.has_handle(clicked_handle))
        return SimHandleOperator.get_handle(z_index) == clicked_handle


    @staticmethod
    def set_window_handle(number, handle):
        SimHandleOperator._window_dict[number] = handle



class WindowCollections:
    

    @staticmethod
    def get_all_from_process(process):
        collection = set()
        found_windows = win_utils.get_ordered_wins()
        for win in found_windows:
            if process == win_utils.get_proc_name_by_hwnd(win.handle).lower():
                collection.add(win)
        return collection


    # ======= create pools =========>


    # list entries: [list process_name_saved, list process_name_available]
    @staticmethod
    def collect_pools(path):
        with open(path, "r") as file:
            old_windows = json.loads(file.readline())
        found_windows = win_utils.get_ordered_wins()
        return WindowCollections._group_together(old_windows, found_windows)


    @staticmethod
    def _group_together(saved, found):
        groups = WindowCollections._prepare_saved(saved)
        for win in found:
            process = win_utils.get_proc_name_by_hwnd(win.handle).lower()
            if process in groups:
                groups[process][1].append(win)
        return groups


    @staticmethod
    def _prepare_saved(saved):
        groups = dict()
        for win in saved:
            process = win["process"].lower()
            if process not in groups:
                groups[process] = (list(), list())
            groups[process][0].append(win)
        return groups


    # ====== evaluate solutions =========>


    # returns ReproducerGuide
    @staticmethod
    def create_win_relations(groups, solutions):
        guide = ReproducerGuide()
        for group_name in groups:
            group = groups[group_name]
            for i, recordedWin in enumerate(group[0]):
                answer = solutions[group_name][i]
                matched = group[1][answer] if answer >= 0 else None
                guide.add(recordedWin["z_index"], recordedWin, matched)
        return guide



class ReproducerGuide():
    
    def __init__(self):
        self._associations = dict()

    def add(self, id: int, saved: dict, matched: base_wrapper.BaseWrapper):
        self._associations[id] = (saved, matched)

    def get_ids(self):
        return self._associations.keys()

    def get_saved(self, id):
        return self._associations[id][0]

    def get_matched(self, id):
        return self._associations[id][1]



class PauseDirector:


    _cached_window_positions_for_pause = None


    # ===== saving =====>


    def save_windows_for_pause(self):
        PauseDirector._cached_window_positions_for_pause = self._get_current_windows()

    @staticmethod
    def get_cached_wins():
        return PauseDirector._cached_window_positions_for_pause

    @staticmethod
    def clear_cache_for_pause():
        PauseDirector._cached_window_positions_for_pause = None

    def _get_current_windows(self):
        winlist = list()
        windows = win_utils.get_ordered_wins()
        for zindex, win in enumerate(windows):
            wininfo = self._get_positional_properties(win, zindex)
            winlist.append(wininfo)
        return winlist

    def _get_positional_properties(self, win, zindex):
        has_title = len(win.window_text()) > 0
        if win.is_maximized(): return {"ref": win, "max": True, "z": zindex, "has_title": has_title}
        return {
            "ref": win,
            "max": False,
            "x": win.rectangle().left,
            "y": win.rectangle().top,
            "z": zindex,
            "width": win.rectangle().width(),
            "height": win.rectangle().height(),
            "has_title": has_title
        }


    # ===== reproducing =======>


    def reproduce_windows_after_pause(self):
        if not PauseDirector.get_cached_wins():
            return print("0 No cached windows to reproduce found while reproducing after pause.", flush=True)
        winlist = PauseDirector.get_cached_wins()
        try:
            self._repr_wins(winlist)
        except _ctypes.COMError as e:
            if e.hresult != -2147220991: raise e
            raise WindowNotExistant()
        PauseDirector.clear_cache_for_pause()

    
    def _repr_wins(self, winlist):
        win_utils.minimize_all_windows()
        for wininfo in reversed(winlist):
            self._replecate_win_after_pause(wininfo)


    def _replecate_win_after_pause(self, wininfo):
        pid = wininfo["ref"].element_info.process_id
        self._alert_closed(wininfo["ref"], wininfo["has_title"])

        if not win_utils.is_normal_win(wininfo["ref"]): return
        if not pid: raise WindowNotExistant()

        if wininfo["max"]:
            return win_utils.maximize_win(wininfo["ref"])
        win_utils.show_win_as_rect(wininfo["ref"], wininfo["x"], wininfo["y"], wininfo["width"], wininfo["height"])

    
    def _alert_closed(self, win, has_title):
        # if there is no window text, it is assumed it is not a normal window, as previously there have been bugs because of it,
        if not handleprops.iswindow(win.handle) and has_title:
            raise WindowNotExistant()