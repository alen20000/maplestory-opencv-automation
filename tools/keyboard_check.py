import keyboard
'''
測試 keyborad模組中，鍵位的對應名稱
'''
def print_key(event):
    print(event)

keyboard.hook(print_key)
keyboard.wait()


