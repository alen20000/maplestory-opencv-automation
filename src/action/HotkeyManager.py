import win32api
import logging

'''
熱鍵管理
這裡是走 "虛擬鍵碼"；以後若要添加可能要再動個鍵值對照表
原因:目前只有一個暫停功能，就先不拉出去了，所以也沒做字串轉換。

'''
class HotkeyManager:
    def __init__(self):
            self._bindings = {}

    def register(self, vk_code, callback):
        '''
        Args:
            vk_code: 虛擬鍵碼
            callback: 觸發時呼叫的函式
        '''
        self._bindings[vk_code] = callback

    def poll(self):
        '''
        每輪主迴圈呼叫一次，檢查所有註冊的熱鍵
        '''
        for vk_code, callback in self._bindings.items():
            state = win32api.GetAsyncKeyState(vk_code)

            #按鍵遮罩:過濾按著的狀態， 這裡是十六進致的1 也就是True
            if state & 0x0001:
                try:
                    callback()
                except Exception as e:
                    logging.error(f"熱鍵回呼發生錯誤 (vk={vk_code}): {e}")