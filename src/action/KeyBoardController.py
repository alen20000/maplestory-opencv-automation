import time
import interception
import logging
from config.config_loader import config
import threading

class KeyBoard:
    def __init__(self):
        #捕捉與綁定滑鼠
        interception.auto_capture_devices(keyboard=True, mouse=True)

        # 追蹤目前「實際按著」的按鍵，release_all 靠這個集合來釋放，不再寫死固定清單
        self._pressed_keys = set()
        self._pressed_keys_lock = threading.Lock()

        #states and lock
        self._release_all_lock = threading.Lock()
        self._attack_lock = threading.Lock()
        self._night_lord_attack_lock = threading.Lock()
        self._move_lock = threading.Lock()
        self._item_lock = threading.Lock()
        self._pick_up_lock = threading.Lock()
        self._jump_lock = threading.Lock()
        self._down_lock = threading.Lock()
        self._up_lock = threading.Lock()
        self._down_lock = threading.Lock()
        self._right_lock = threading.Lock()
        self._left_lock = threading.Lock()
        self._move_down_right_lock = threading.Lock()
        self._move_down_left_lock = threading.Lock()
        self._jump_left_lock = threading.Lock()
        self._jump_right_lock = threading.Lock()
        self._jump_left_grab_lock = threading.Lock()
        self._jump_right_grab_lock =threading.Lock()
        self._jump_down_lock = threading.Lock()
        self._jump_up_grab_lock = threading.Lock()

        self._status_release_all = False
        self._status_attack = False
        self._status_night_lord_attack = False #Night_Lord_attack
        self._status_jump = False
        self._status_up = False
        self._status_down = False
        self._status_right = False
        self._status_left = False
        self._status_item = False  
        self._pick_up = False
        self._status_move_down_right = False
        self._status_move_down_left = False
        self._status_jump_left = False
        self._status_jump_right = False
        self._status_jump_left_grab = False 
        self._status_jump_right_grab = False
        self._status_jump_up_grab = False
        self._status_jump_down = False

        #key value
        self.attack_key = config.get("keyboard.attack")
        self.up_key = config.get("keyboard.up")
        self.down_key = config.get("keyboard.down")
        self.left_key = config.get("keyboard.left")
        self.right_key = config.get("keyboard.right")
        self.pick_up_key = config.get("keyboard.pick_up")
        self.jump_key = config.get("keyboard.jump")
        #action logging
        self._current_move = None # <- 紀錄目前移動指令

    ''' 
    底層按鍵包裝：所有 key_down / key_up 都經過這裡，統一追蹤按下狀態 ， 也可統一釋放
    '''

    def _key_down(self, key):
        interception.key_down(key)
        with self._pressed_keys_lock:
            self._pressed_keys.add(key)

    def _key_up(self, key):
        interception.key_up(key)
        with self._pressed_keys_lock:
            self._pressed_keys.discard(key)

    ''' 攻擊行為 '''
    def _attack_command(self, direction):
        try: 
            key = self.right_key if direction == "RIGHT" else self.left_key
            self._key_down(key)
            self._key_up(key)
            self._key_down(self.attack_key)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"攻擊行為發生錯誤:{e}")
            
        finally:
            self._key_up(self.attack_key)
            with self._attack_lock:
                self._status_attack = False


    def enable_attack(self,direction):
        with self._attack_lock:
            if self._status_attack:
                #攻擊還在發生，不再傳輸攻擊指令
                return
            self._status_attack = True
            threading.Thread(target=self._attack_command,args=(direction,),daemon=True).start() 

    def _night_lord_att_command(self, direction):
        try: 
            key = self.right_key if direction == "RIGHT" else self.left_key
            self._key_down(key)
            self._key_up(key)

            time.sleep(0.1)

            self._key_down(self.jump_key)
            self._key_down(self.attack_key)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"攻擊行為發生錯誤:{e}")
            
        finally:
            self._key_up(self.attack_key)
            self._key_up(self.jump_key)
            with self._attack_lock:
                self._status_night_lord_attack = False

    def enable_night_lord_attack(self,direction):
        with self._night_lord_attack_lock:
            if self._status_night_lord_attack:
                #攻擊還在發生，不再傳輸攻擊指令
                return
            self._status_night_lord_attack = True
            threading.Thread(target=self._night_lord_att_command,args=(direction,),daemon=True).start()
            
    ''' 移動行為 '''

    def enable_move_right(self):

        with self._move_lock:

            if self._current_move == "RIGHT": #重複指令拋棄
                return
            if self._current_move == "LEFT":
                self._key_up(self.left_key)

            self._key_down(self.right_key)
            self._current_move = "RIGHT"

    def enable_move_left(self):

        with self._move_lock:
            if self._current_move == "LEFT":    #重複指令拋棄
                return
            if self._current_move == "RIGHT":
                self._key_up(self.right_key)

            self._key_down(self.left_key)
            self._current_move = "LEFT"

    def _jump_command(self,duration):
        try:
            self._key_down(self.jump_key)
            time.sleep(duration)
        finally:
            self._key_up(self.jump_key)
            if self._status_jump:
                self._status_jump = False

    def enable_jump(self,duration=0.1):
        with self._jump_lock:
            if self._status_jump:
                return
        self._status_jump = True
        threading.Thread(target=self._jump_command,args=(duration,),daemon=True).start() 

    def _down_command(self,duration):
        try:
            self._key_down(self.down_key)
            time.sleep(duration)
        finally:
            self._key_up(self.down_key)
            if self._status_down:
                self._status_down = False

    def enable_down(self,duration=0.1):
        with self._down_lock:
            if self._status_down:
                return
            self._status_down = True
        threading.Thread(target=self._down_command, args=(duration,), daemon=True).start()

    def _up_command(self,duration):
        try:
            self._key_down(self.up_key)
            time.sleep(duration)
        finally:
            self._key_up(self.up_key)
            if self._status_up:
                self._status_up = False

    def enable_up(self,duration=0.1):
        with self._up_lock:
            if self._status_up:
                return
            self._status_up = True
        threading.Thread(target=self._up_command,args=(duration,), daemon=True).start()

    def _right_command(self,duration):
        try:
            self._key_down(self.right_key)
            time.sleep(duration)
        finally:
            self._key_up(self.right_key)
            if self.right_key:
                self._status_right = False

    def enable_right(self,duration=0.1):
        with self._right_lock:
            if self._status_right:
                return
            self._status_right = True
        threading.Thread(target=self._right_command,args=(duration,), daemon=True).start()

    def _left_command(self,duration):
        try:
            self._key_down(self.left_key)
            time.sleep(duration)
        finally:
            self._key_up(self.left_key)
            if self.left_key:
                self._status_left = False

    def enable_left(self,duration=0.1):
        with self._left_lock:
            if self._status_left:
                return
            self._status_left = True
        threading.Thread(target=self._left_command,args=(duration,), daemon=True).start()

    '''垂直移動'''
    #先這樣，以後慢慢改
    
    def grab_rope_to_left(self):
        '''向左跳抓繩子'''
        self.enable_left()
        time.sleep(0.03)
        self.enable_jump()
        self.enable_up(duration=0.5)

    def grab_rope_to_right(self):
        '''向右跳抓繩子'''
        self.enable_right()
        time.sleep(0.03)
        self.enable_jump()
        self.enable_up(duration=0.5)

    def _move_down_right_command(self, duration):
        try:
            self._key_down(self.right_key)
            time.sleep(0.03)              # 先給右鍵一點時間讓角色轉向/移動一小步
            self._key_down(self.down_key)   # 再按下「下」，觸發下滑抓繩
            time.sleep(duration)
        except Exception as e:
            logging.error(f"下滑動作發生錯誤:{e}")
        finally:
            self._key_up(self.right_key)
            self._key_up(self.down_key)
            with self._move_down_right_lock:
                self._status_move_down_right = False

    def move_down_right(self, duration=0.5):
        '''向右下移動'''
        with self._move_down_right_lock:
            if self._status_move_down_right:
                return
            self._status_move_down_right = True
        threading.Thread(target=self._move_down_right_command, args=(duration,), daemon=True).start()

    def _move_down_left_command(self, duration):
        try:
            self._key_down(self.left_key)
            time.sleep(0.03)              # 先給左鍵一點時間讓角色轉向/移動一小步
            self._key_down(self.down_key)   # 再按下「下」，觸發下滑抓繩
            time.sleep(duration)
        except Exception as e:
            logging.error(f"下滑動作發生錯誤:{e}")
        finally:
            self._key_up(self.left_key)
            self._key_up(self.down_key)
            with self._move_down_left_lock:
                self._status_move_down_left = False

    def move_down_left(self, duration=0.5):
        '''向左下移動'''
        with self._move_down_left_lock:
            if self._status_move_down_left:
                return
            self._status_move_down_left = True
        threading.Thread(target=self._move_down_left_command, args=(duration,), daemon=True).start()

    #======
    # 跳抓
    #=====

    def jump_left_grab_command(self, duration=0.1, delay=0.03):

        try:
            self._key_down(self.left_key)
            time.sleep(delay)          # 微小間隔，讓方向鍵先生效，才能觸發跳躍轉向
            self._key_down(self.jump_key)
            time.sleep(duration)
            self._key_down(self.up_key)
        except Exception as e:
            logging.error(f"左跳動作發生錯誤:{e}")
        finally:
            self._key_up(self.jump_key)
            self._key_up(self.left_key)
            time.sleep(0.2)             # 等待跳躍動作結束 
            self._key_down(self.up_key)
            with self._jump_left_grab_lock:
                self._status_jump_left_grab = False

    def jump_left_grab(self, duration=0.1, delay=0.03):

        with self._jump_left_grab_lock:
            self.stop_move()  #<== 停止移動
            if self._status_jump_left_grab:
                return
            self._status_jump_left_grab = True
        threading.Thread(target=self.jump_left_grab_command, args=(duration, delay), daemon=True).start()

    def jump_right_grab_command(self, duration=0.1, delay=0.03):

        try:
            self._key_down(self.right_key)
            time.sleep(delay)          # 微小間隔，讓方向鍵先生效，才能觸發跳躍轉向
            self._key_down(self.jump_key)
            time.sleep(duration)
            self._key_down(self.up_key)
        except Exception as e:
            logging.error(f"左跳動作發生錯誤:{e}")
        finally:
            self._key_up(self.jump_key)
            self._key_up(self.right_key)
            time.sleep(0.2)             # 等待跳躍動作結束 
            self._key_down(self.up_key)
            with self._jump_right_grab_lock:
                self._status_jump_right_grab = False

    def jump_right_grab(self, duration=0.1, delay=0.03):

        with self._jump_right_grab_lock:
            if self._status_jump_right_grab:
                return
            self._status_jump_right_grab = True
        threading.Thread(target=self.jump_right_grab_command, args=(duration, delay), daemon=True).start()

    def _jump_up_grab_command(self, duration=0.1, delay=0.03):
        '''向上跳（複合動作：先按住上 -> 微間隔 -> 按下跳躍）'''
        try:
            self._key_down(self.up_key)
            time.sleep(delay)          # 微小間隔，讓上鍵先生效，才能觸發向上跳躍的判定
            self._key_down(self.jump_key)
            time.sleep(duration)
        except Exception as e:
            logging.error(f"向上跳動作發生錯誤:{e}")
        finally:
            self._key_up(self.jump_key)


            with self._jump_up_grab_lock:
                self._status_jump_up_grab = False

    def jump_up_grab(self, duration=0.1, delay=0.03):
        '''向上跳對外接口'''
        with self._jump_up_grab_lock:
            self.stop_move()  #<== 停止移動
            time.sleep(0.1)
            if self._status_jump_up_grab:
                return
            self._status_jump_up_grab = True
        threading.Thread(target=self._jump_up_grab_command, args=(duration, delay), daemon=True).start()

    #======
    # 單點跳
    #=====


    def _jump_down_command(self, duration=0.1, delay=0.03):
        '''向下跳（複合動作：先按住下 -> 微間隔 -> 按下跳躍）'''
        try:
            self._key_down(self.down_key)
            time.sleep(delay)          # 微小間隔，讓下鍵先生效，才能觸發向下落下的判定
            self._key_down(self.jump_key)
            time.sleep(duration)
        except Exception as e:
            logging.error(f"向下跳動作發生錯誤:{e}")
        finally:
            self._key_up(self.jump_key)
            self._key_up(self.down_key)
            time.sleep(0.2)             # 等待跳躍動作結束 

            with self._jump_down_lock:
                self._status_jump_down = False

    def jump_down(self, duration=0.1, delay=0.03):
        '''向下跳对外接口'''
        with self._jump_down_lock:
            if self._status_jump_down:
                return
            self._status_jump_down = True
        threading.Thread(target=self._jump_down_command, args=(duration, delay), daemon=True).start()

    def _jump_left_command(self, duration=0.1, delay=0.03):
        '''向左跳'''
        try:
            self._key_down(self.left_key)
            time.sleep(delay)          # 微小間隔，讓方向鍵先生效，才能觸發跳躍轉向
            self._key_down(self.jump_key)
            time.sleep(duration)

        except Exception as e:
            logging.error(f"左跳動作發生錯誤:{e}")
        finally:
            self._key_up(self.jump_key)
            self._key_up(self.left_key)
            time.sleep(0.2)             # 等待跳躍動作結束 

            with self._jump_left_lock:
                self._status_jump_left = False

    def jump_left(self, duration=0.1, delay=0.03):
        '''向左跳（複合動作：方向鍵 -> 微間隔 -> 跳躍鍵）'''
        with self._jump_left_lock:
            if self._status_jump_left:
                return
            self._status_jump_left = True
        threading.Thread(target=self._jump_left_command, args=(duration, delay), daemon=True).start()



    def _jump_right_command(self, duration=0.1, delay=0.03):
        '''向右跳'''
        try:
            self._key_down(self.right_key)
            time.sleep(delay)          # 微小間隔，讓方向鍵先生效，才能觸發跳躍轉向
            self._key_down(self.jump_key)
            time.sleep(duration)

        except Exception as e:
            logging.error(f"右跳動作發生錯誤:{e}")
        finally:
            self._key_up(self.jump_key)
            self._key_up(self.right_key)
            time.sleep(0.2)             # 等待跳躍動作結束 

            with self._jump_right_lock:
                self._status_jump_right = False

    def jump_right(self, duration=0.1, delay=0.03):
        '''向右跳（複合動作：方向鍵 -> 微間隔 -> 跳躍鍵）'''
        with self._jump_right_lock:
            if self._status_jump_right:
                return
            self._status_jump_right = True
        threading.Thread(target=self._jump_right_command, args=(duration, delay), daemon=True).start()

    #======
    # 上爬
    #=====

    def climb_up(self):
        self._key_down(self.up_key)

    def climb_down(self):
        self.enable_down(duration=1)

    ''' 停止釋放'''

    def _release_all(self):
        # 釋放「目前實際追蹤到有按著」的所有鍵 
        # 這樣新增按鍵(如未來的補血鍵、道具鍵)時不用回來改這裡，也不會漏鍵
        with self._pressed_keys_lock:
            keys_to_release = list(self._pressed_keys)

        self._key_up(self.up_key) #因為一直沒辦法彈起UP，所以直接寫在這裡

        for key in keys_to_release:
            self._key_up(key)
            time.sleep(0.01)  # 給驅動/遊戲一點時間確實處理事件
        
    def release_all(self):
        #釋放常用、高機率卡住的按鍵
        self._packet_wrapper(self._release_all_lock, "_status_release_all", self._release_all)

    def stop_move(self):
        with self._move_lock:
            #如果正在移動，左右鍵彈起
            if self._current_move is not None:
                try:
                    self._key_up(self.left_key)
                    self._key_up(self.right_key)
                except Exception as e:
                    logging.error(f"釋放移動發生錯誤:{e}")
                finally:
                    self._current_move = None

    ''' 物品使用行為（補血/補魔等） '''

    def _item_command(self, key):
        try:
            self._key_down(key)
            time.sleep(3)
        except Exception as e:
            logging.error(f"使用物品發生錯誤:{e}")
        finally:
            self._key_up(key)
            with self._item_lock:
                self._status_item = False

    def enable_use_item(self, key):
        if not key:
            return
        with self._item_lock:
            if self._status_item:
                # 上一次使用還沒結束，不重複觸發
                return
            self._status_item = True
            threading.Thread(target=self._item_command, args=(key,), daemon=True).start()

    ''' 撿拾行為 '''
    def _pick_up_command(self, key):
        try:
            self._key_down(key)
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"撿拾命令發生錯誤:{e}")
        finally:
            self._key_up(key)
            self._pick_up = False

    def enable_pick_up(self):
        with self._pick_up_lock:
            if not self.pick_up_key:
                return
            self._pick_up = True
        threading.Thread(target=self._pick_up_command, args=(self.pick_up_key,), daemon=True).start()

    def _packet_wrapper(self, lock, status_attr, target, *args):
        """
        共用的「防重入 + 背景執行」包裝
        lock: 對應的 threading.Lock
        status_attr: 對應的旗標屬性名稱字串，例如 "_status_rope"
        target: 實際要執行的方法
        """
        with lock:
            if getattr(self, status_attr):
                return
            setattr(self, status_attr, True)

        def _wrapper():
            try:
                target(*args)
            except Exception as e:
                logging.error(f"{target.__name__} 發生錯誤:{e}")
            finally:
                with lock:
                    setattr(self, status_attr, False)

        threading.Thread(target=_wrapper, daemon=True).start()