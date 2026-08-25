from typing import Optional
'''
功能:
    記錄觸發進出垂直通道的事件
    只有進去及進出時觸發
'''
class ZoneTracker:

    def __init__(self):

        # self.last_platform: Optional[int] = None
        self.last_vertical_passage: Optional[int] = None

    def update(self, player_loc, vertical_passages):
        if not player_loc:
            return []

        events = []


        current_vp = self._find_zone(player_loc, vertical_passages)
        if current_vp != self.last_vertical_passage:
            if self.last_vertical_passage is not None:
                events.append(("LEAVE_VERTICAL", self.last_vertical_passage))
            if current_vp is not None:
                events.append(("ENTER_VERTICAL", current_vp))
            self.last_vertical_passage = current_vp

        return events

    @staticmethod
    def _find_zone(player_loc, zones):
        """
        共用的座標比對邏輯
        返回的是一個引所值
        """
        if not zones:
            return None

        px, py = player_loc
        for index, zone in enumerate(zones):
            left, top = zone["t_l"]
            right, bottom = zone["b_r"]
            if left <= px <= right and top <= py <= bottom:
                return index
        return None