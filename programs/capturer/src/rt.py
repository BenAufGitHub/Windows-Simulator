'''
This files purpose is to keep singleton classes that contain information about the runtime.
'''


# this class counts which windows have been used during the recording
class ClickInfo():

    __shared_state = dict()
    __shared_state["_clicked_wins"] = set()

    def __init__(self):
        self.__dict__ = self.__shared_state

    def add_clicked_windex(self, windex: int):
        self._clicked_wins.add(windex)

    def clear_clicked_windecies(self):
        self._clicked_wins.clear()

    def get_clicked_windecies_list(self) -> list:
        copy = []
        copy.extend(self._clicked_wins)
        return copy
    

