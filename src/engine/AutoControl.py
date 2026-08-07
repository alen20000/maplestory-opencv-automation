import time
import logging


'''
行為邏輯，橋接GameBot 與 發布命令給 KeyBoardController
'''
class AutoControl:
    def __init__(self, game_bot_instance):

        #parameters
        self.bot =game_bot_instance
        self.my_att_range:100

    def decide_action(self):


        pass




def random_move():
    '''
    預設，假使沒匹配到角色，隨機移動  // 也可以做切片匹配保險 但不清楚效能負擔 不是很想弄
    '''

    pass

def attack_action():
    '''
    預設，接收相對座標小於[攻擊範圍]， 觸發攻擊行為
    '''
    pass