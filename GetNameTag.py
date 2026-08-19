import tools.get_nametag
import logging
import os
import sys
import ctypes 
'''
暫時使用。 
啟動模塊，抓取角色標籤，為用作名稱標籤以利匹配座標。
'''
    #=================
    # 作業系統管理員權限
    #=================
def is_admin():
    """檢查當前是否擁有管理員權限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理員權限重新執行當前"""

    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)


if __name__ == "__main__":

    #---管理員權限
    if not is_admin():
        run_as_admin()
        sys.exit()
    try:
        run = tools.get_nametag.GetRoleImg()
        run.run()
    except Exception as e:
        logging.exception(f"未預期的例外錯誤: {e}")