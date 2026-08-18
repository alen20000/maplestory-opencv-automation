
import cv2
import numpy as np
import win32gui
from PIL import ImageGrab
from src.utils.common import (get_window_handle_and_rect_by,
bring_to_front_and_center_origin,cent_coord,get_bbox_from_center,draw_dectection_box,BGR2Binary,convert_img2xy
)
from src.engine.MobHunting import MobDetector
import ctypes
from src.utils.boxes import BBox
from config.config_loader import config
import logging
from src.states.player_states import PlayerStates
from src.engine.AutoControl import AutoControl
from src.engine.HealthDetector import HealthDetector
from src.engine.game_state import GameState
from src.engine.MinimapDetector import MinimapDetector
import time
import re
import src.action.HotkeyManager as hk
import win32con

'''
快捷鍵:
F9:暫停/繼續
F12:退出離開
'''

class GameBot:
    
    def __init__(self):
        #---config setting

        #--視窗設定
        self.game_title = config.get("game.title")
        self.hwnd = None

        #---角色屬性
        self.my_character_template_path = 'img/nametag/MyRoleNameTag.png'
        self.my_character_template = None
        self.my_character_template_size = None
        self.my_character_template_gray = None
        self.my_character_template_binary = None

        #---畫面資料
        self.frame_bgr = None
        self.roi_crop_frame_gray = None
        self.frame_size:tuple[int, int] = None # (x,y)typle
        self.dectect_False_count = 0

        #---掃描設定
        self.method = cv2.TM_CCOEFF_NORMED
        self.min_threshold = config.get("image_processing.role_min_threshold")

        #---計算資料
        self.role_BBOX:BBox = None
        self.roi_BBOX:BBox = None
        self.role_score = 0  #角色置信度
        self.last_loc = None  # 記住上一次找到的位置
        self.player_center_loc = None
        self.current_mobs_result =None
        self.lost_track_duration = 0#<-  人物失蹤計算

        #---健康參數
        self.player_hp = None

        ##--模組實例
        self.mob_detector = None
        self.player_states = None
        self.health_dectector = None
        self.minimap_detector = None

        #---視窗狀態
        self.bot_enabled = True

        #---熟鍵設定
        self.hotkey_manager = hk.HotkeyManager()
        self.hotkey_manager.register(win32con.VK_F9, self._toggle_bot)
        self.hotkey_manager.register(win32con.VK_F12, self._exit_app)
        
    def _connect_window(self):
        '''
        hook the game window
        '''
        self.hwnd,self.client_rect =  get_window_handle_and_rect_by(self.game_title)
        if self.hwnd :
            logging.info(f"成功讀取遊戲標題: {self.game_title }，視窗句柄: {self.hwnd}")
        else:
            logging.info(f"未匹配到指定窗口{self.game_title }")

    def _toggle_bot(self):
        '''
        功能: 切換bot狀態，預設F9
        '''
        try:
            self.bot_enabled = not self.bot_enabled
            # 釋放所有熟鍵
            import src.action.KeyBoardController as kb
            kb = kb.KeyBoard()
            kb.release_all()
            #這是[Info]層，但因為會被過濾所以放warning
            logging.warning(f"[Bot 狀態]: {'啟動' if self.bot_enabled else '暫停'}")
        except Exception as e:
            logging.error(e)

    def _exit_app(self):
        '''
        功能:關掉程式
        '''
        logging.info("正在關閉應用程式...")
        self.bot_enabled = False
        
        # 銷毀所有 OpenCV 視窗
        cv2.destroyAllWindows()
        
        # 結束整個程式 (可以透過回傳或直接 sys.exit)
        import sys
        sys.exit(0)

    def _load_game_resources(self):
        """預先載入資源"""       

        #樣板載入
        self.my_character_template = cv2.imread(self.my_character_template_path)
        self.my_character_template_size =  convert_img2xy(self.my_character_template)
        self.my_character_template_gray =cv2.cvtColor(self.my_character_template, cv2.COLOR_BGR2GRAY)
        self.my_character_template_binary = BGR2Binary(self.my_character_template)

        #模組實例化
        self.mob_detector = MobDetector()
        self.player_states = PlayerStates() #init player state
        self.health_dectector = HealthDetector()
        self.auto_control = AutoControl()
        self.minimap_detector = MinimapDetector()
        logging.info(f"已載入屬性與實例")

    def _scan_full_screen(self):
        '''以窗柄去掃描遊戲畫面'''
        try:
            #這邊還能優化 以後看到記得改
            screen_rect = win32gui.GetClientRect(self.hwnd)
            screen_rect_point_top_left = win32gui.ClientToScreen(self.hwnd, (screen_rect[0], screen_rect[1]))
            screen_rect_point_bottom_right = win32gui.ClientToScreen(self.hwnd, (screen_rect[2], screen_rect[3]))
            screen_rect = (screen_rect_point_top_left[0], screen_rect_point_top_left[1], screen_rect_point_bottom_right[0], screen_rect_point_bottom_right[1])  

        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
            return None

        #抓圖-轉陣-轉BRG
        current_frame = ImageGrab.grab(bbox=screen_rect)
        current_frame = np.array(current_frame)
        frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR) #影像處理預設都是BGR

        if frame_bgr is not None:
            self.frame_bgr = frame_bgr
            
            # 記錄畫面尺寸
            if self.frame_size is None:
                y, x = frame_bgr.shape[:2]  # (height, width)
                self.frame_size = (x ,y)

        return frame_bgr


    def _is_window_valid(self):
        if not win32gui.IsWindow(self.hwnd):
            logging.info("沒有偵測到窗口")
            return False
        if win32gui.IsIconic(self.hwnd):
            logging.info("沒有偵測到窗口")
            return False
        rect = win32gui.GetClientRect(self.hwnd)
        if rect[2] < 100 or rect[3] < 100:
            return False
        return True

    def _lost_track_count(self):
        self.lost_track_duration += 1
        return True
    
    def run(self):

        """#pre_process"""
        # 強制讓 Python 程式識別真實的螢幕 DPI 像素，避免抓圖範圍縮水
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
        self._connect_window()
        #adjusying display window
        bring_to_front_and_center_origin(self.hwnd)
        self._load_game_resources()


        #process
        self.screen_loop()

    def screen_loop(self):
        '''
        全螢幕刷新
        
        '''
        
        try:
            while True:
                self.frame_bgr = self._scan_full_screen()
                '''
                ==============
                | 數據收集封包|
                ==============
                '''
                # 監測熟鍵
                self.hotkey_manager.poll() 
                if not self.bot_enabled: 
                    # 暫停狀態
                    if cv2.waitKey(1) == ord('q'):
                        break
                    continue  

                # 窗口偵測
                self._is_window_valid()

                # start =time.time() 

                # 偵測與更新數據
                self.player_tracking_logic()
                self.HealthDetector()
                self.current_mobs_result = self.MobDetector()
                mini_player_loc = self.MinimapDetector()

                #測試
                try:
                    pass
                except:
                    pass

                #繪製BBOX,Text
                self._draw_mob(self.current_mobs_result)
                self._show_player_loc(mini_player_loc)

                # print(f"圖匹配畫圖耗時: {time.time() - start:.3f}")
                # 數據封包
                current_game_state =  GameState(
                    player_center_loc = self.player_center_loc,
                    player_hp = self.player_hp,
                    roi_BBOX = self.roi_BBOX,
                    mobs = self.current_mobs_result,
                    # frame = self.frame_bgr,
                    # lost_track_count = self.lost_track_duration,
                    mini_player_loc = mini_player_loc,
                )
                
                '''
                decide_operation ,execute_behavior  -> (str, dict{})
                '''
                action_states, target_info = self.auto_control.select_operation(current_game_state)
                # print(f"行為:{action_states} 目標:{target_info}")

                #至少有  action_states 才傳輸給狀態機
                if action_states is not None :
                    self.player_states.execute_behavior(action_states, target_info)

                '''
                ================
                '''
                cv2.imshow("Game Debug View", self.frame_bgr)
                cv2.waitKey(1)

                # print(f"一個while循環耗時: {time.time() - start:.3f}")
        except Exception as e:
            logging.error(f"screen_loop 發生例外錯誤: {e}", exc_info=True)
        finally:
            cv2.destroyAllWindows()

    #=================
    # 人物掃描邏輯
    #=================
    def player_tracking_logic(self):
        '''
        角色位置提取:全局掃描/ROI掃描
        人物BBOX繪製
        '''
        try:
            if self.player_center_loc is None:
                #全圖掃
                player_loc = self._locate_player_globally()

                #防止max_loc沒東西時report
                if player_loc is not None:
                    self.lost_track_duration = 0 #<-  人物失蹤計算歸零
                    self.player_center_loc = cent_coord(player_loc,self.my_character_template_size)
                else:
                    #計算人物失聯時間
                    self._lost_track_count()
                    if self.lost_track_duration > 30:
                        self.lost_track_duration = 0

            else:
                #進入ROI掃
                fund_result = self._locate_player_locally()

                #用回傳的True/False，來做失敗紀錄，好像沒啥用，先放著
                if not fund_result:
                    self.dectect_False_count += 1
                    if self.dectect_False_count > 10:
                        self.player_center_loc = None
                        self.dectect_False_count = 0

            #得到中心座標，則繪製bounding box
            if self.player_center_loc is not None:
                #計算角色BBOX
                self.role_BBOX = get_bbox_from_center(self.player_center_loc,self.my_character_template_size)

                role_name = f"玩家 {self.role_score:.2f}"
                #繪製角色BBOX
                draw_dectection_box(self.frame_bgr,self.role_BBOX.top_left,self.role_BBOX.bottom_right,label=role_name,
                top_padding=100, bottom_padding=0, left_padding=0, right_padding=0)
            else:
                pass

        except Exception as e:
            logging.error(e)

    def _locate_player_globally(self):
        '''
        全局掃描人物
        '''
        try:
            current_frame = cv2.cvtColor(self.frame_bgr, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(current_frame,self.my_character_template_gray,self.method)
            
            #找到角色
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > self.min_threshold:
                logging.info(f"全圖掃描找到角色，位置:{max_loc},置信度:{max_val}")
                self.role_score = max_val
                return max_loc
            else:
                logging.info(f"全圖模式:未匹配角色")
                pass
        except Exception as e:
            logging.error(e)

    def _locate_player_locally(self):
        '''
        局部掃描:
        '''
        try:
            # # 設定搜尋範圍的位移量[!] 之後變數要移走
            # x_offset, y_offset = config.get("game_bot.roi_x_offset"), config.get("game_bot.roi_y_offset")
            x_offset_l_w = config.get("game_bot.roi_x_offset_l_width")
            x_offset_r_w = config.get("game_bot.roi_x_offset_r_width")
            y_offset_t_h = config.get("game_bot.roi_y_offset_t_high")
            y_offset_b_h = config.get("game_bot.roi_y_offset_b_high")
            # Tuple都是[x,y]位置
            top = max(0, self.player_center_loc[1] - y_offset_t_h)
            left = max(0, self.player_center_loc[0] - x_offset_l_w)
            bottom = min(self.frame_size[1], self.player_center_loc[1] + y_offset_b_h )
            right = min(self.frame_size[0], self.player_center_loc[0]  + x_offset_r_w)

            # 計算ROI範圍
            self.roi_BBOX = BBox(left, top, right, bottom)

            #[!]OpenCV 陣列切片強制要求 [y軸範圍, x軸範圍]，小心切錯
            roi_crop_frame = self.frame_bgr[top:bottom, left:right]
            self.roi_crop_frame_gray  =  cv2.cvtColor(roi_crop_frame, cv2.COLOR_BGR2GRAY)
            matches = cv2.matchTemplate(self.roi_crop_frame_gray ,self.my_character_template_gray,self.method)
            _, max_val, _, max_loc = cv2.minMaxLoc(matches)

            if max_val > self.min_threshold:

                #相對座標轉全局座標；全局座標= 相對座標x + roi全局座標x, 相對座標y + roi全局座標y 
                player_loc_globally = (max_loc[0] + self.roi_BBOX.x1, max_loc[1] + self.roi_BBOX.y1)

                self.player_center_loc = cent_coord(player_loc_globally , self.my_character_template_size)
                self.role_BBOX = get_bbox_from_center(self.player_center_loc , self.my_character_template_size)

                # 繪製偵查範圍
                draw_dectection_box(self.frame_bgr, self.roi_BBOX.top_left, self.roi_BBOX.bottom_right, label="偵測範圍",
                top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)

                return  True
            
            else:
                logging.info('ROI掃描，未找到角色')
                return False    

        except Exception as e:
            logging.error(e)

    #=================
    # 偵測器:怪物
    #=================
    def MobDetector(self):
        '''
        與怪物偵測模組進行互動：傳送當前灰階圖，並取得回傳的怪物封包。
        '''
        if self.roi_crop_frame_gray is not None:
            #push data

            mob_results = self.mob_detector.searching_mob(self.roi_crop_frame_gray)

            return mob_results

    #=================
    # 偵測器:健康
    #=================

    def HealthDetector(self):
        '''
        get:self.player_hp
        '''
        try:
            #這裡以後若要做補MP偵測，不能這樣寫
            self.player_hp = self.health_dectector.hp_detect(self.frame_bgr)
        except Exception as e:
            logging.error(e)

    #=================
    # 偵測器:小地圖
    #=================
    def MinimapDetector(self)-> tuple[int,int]:
        '''
        WIP
        與小圖偵測模組進行互動：傳送當前BGR圖
        return : 人物位置(x,y)
        '''
        mini_player_loc = self.minimap_detector.run(self.frame_bgr)
        return mini_player_loc
    
    #=================
    # 繪製函式
    #=================

    def _show_player_loc(self,player_loc):
        
        cv2.putText(self.frame_bgr, f"人物座標: {player_loc}", org=(10, 250),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0, 0, 0), thickness=2)

    def _draw_mob(self, mob_results: list):
        """
        解析怪物封包，然後畫出BBOX
        """
        if mob_results and self.roi_BBOX is not None:
            for mob_name, mob_details in mob_results:
                
                for detailed in mob_details:
                    x1 = detailed["top_left"][0] + self.roi_BBOX.x1
                    y1 = detailed["top_left"][1] + self.roi_BBOX.y1
                    w, h = detailed["size"]
                    score = detailed["score"]
                    clean_name = re.sub(r'\s*\(\s*\d+\s*\)', '', mob_name)
                    score_text = f"{score:.2f}"
                    clean_name = f"{clean_name} {score_text}"

                    draw_dectection_box(
                        self.frame_bgr,
                        (x1,y1),
                        (x1+w, y1+h),
                        label=clean_name,color = (0, 0, 255),
                        top_padding=0, bottom_padding=0, left_padding=0, right_padding=0)

        
    # def get_client_screen_pos(self):
    #     '''
    #     測試用
    #     窗口內座標轉螢幕座標
    #     '''
    #     screen_x, screen_y = win32gui.ClientToScreen(self.hwnd, (0, 0))
    #     print(f"窗口內座標轉螢幕座標: {screen_x}, {screen_y}")




