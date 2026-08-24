import time
import logging
from config.config_loader import config
from typing import Optional
from src.engine.game_state import GameState
import time
import random
from pathlib import Path
import yaml
import time


class HealthManager:
    def __init__(self):

        #---[補品、血魔設定]
        self.health_setting = {} #<-- 血量等級配置
        self.mp_setting = {} #<-- 藍水等級配置
        self.hp_sorted_levels = [] #<-- 紅水等級排序
        self.mp_sorted_levels = [] #<-- 藍水等級排序
        self.hp_cooldown = 5 #<--紅水冷卻時間
        self.mp_cooldown = 5 #<--藍水冷卻時間
        self._loading_config()
        #---[計時器]
        self.last_hp_time = None #<--上次喝紅時間
        self.last_mp_time = None #<--上次喝藍時間

    def _loading_config(self):

        '''
        功能:
            從設定檔讀取藥水配置，過濾無效配置，再進行排序
        '''

        hp_raw = config.get("player_setting.health_setting") or {}
        for level, setting in hp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":
                key = None

            self.health_setting[level] = {
                "value" : value,
                "key" : key,
            }

        self.hp_sorted_levels = sorted(
            self.health_setting.items(),
            key=lambda item: item[1]["value"]
        )
        mp_raw = config.get("player_setting.mp_setting") or {}
        for level, setting in mp_raw.items():
            key = setting.get("key")
            value = setting.get("value")
            if key == "None":           #<--沒設置的水線，會被拋棄
                key = None

            self.mp_setting[level] = {
                "value" : value,
                "key" : key,
            }

        self.mp_sorted_levels = sorted(
            self.mp_setting.items(),
            key=lambda item: item[1]["value"]
        )
    def _health_status_check(self,player_hp,current_time): 

        '''
        用途:
            血量情況判斷與行動分流
            回傳: 血量分級、對應按鍵
        '''

        if player_hp is None:
            return None, None  # 防呆:# player_hp 為 None 時提前擋下

        if not (0 < player_hp <= 100):
            logging.debug(f"血量取值異常: {player_hp} ")
            return None, None

        if not self.health_setting:
            return None, None 



        if self.last_hp_time is None:
            self.last_hp_time = current_time
        # 喝水冷卻時間
        if (current_time - self.last_hp_time) < self.hp_cooldown:
            return None, None

        #主要判斷
        for level, setting in self.hp_sorted_levels:
            if player_hp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                self.last_hp_time = current_time
                return level, key
        return None, None

    def _mp_status_check(self,player_mp,current_time): 


        if player_mp is None:
            return None, None  # 防呆:# player_mp 為 None 時提前擋下

        if not (0 < player_mp <= 100):
            logging.info(f"魔力取值異常: {player_mp} ")
            return None, None


        # 沒有設定喝水，直接回傳None
        if not self.mp_setting:
            return None, None 

        if self.last_mp_time is None:
            self.last_mp_time = current_time
        # 喝水冷卻時間
        if (current_time - self.last_mp_time) < self.mp_cooldown:
            return None, None
        
        #主要判斷
        for level, setting in self.mp_sorted_levels:
            if player_mp < setting["value"]:
                key = setting["key"]
                if key is None:
                    continue   # 這個等級沒設按鍵，跳過，往下一級檢查
                self.last_mp_time = current_time
                return level, key
            
        return None, None


    def run(self,current_player_hp,current_player_mp, current_time):
        level , heal_key = self._health_status_check(current_player_hp,current_time)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": heal_key}
        level , mp_key = self._mp_status_check(current_player_mp, current_time)
        if level is not None:
            return f"HEAL_{level.upper()}", {"key": mp_key}