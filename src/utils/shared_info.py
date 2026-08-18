'''
放共享資料
'''

class SharedInfo:
    def __init__(self):
        # 這是我們的公告欄內容
        self.minimap_tl = None
        self.is_initialized = False

    def update_minimap_anchor(self, tl: tuple):
        self.minimap_tl = tl
        self.is_initialized = True



shared_info =  SharedInfo()