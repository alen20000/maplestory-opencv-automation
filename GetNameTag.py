import tools.get_nametag
import logging      
'''
暫時使用。 
啟動模塊，抓取角色標籤，為用作名稱標籤以利匹配座標。
'''
if __name__ == "__main__":
    try:
        run = tools.get_nametag.GetRoleImg()
        run.run()
    except Exception as e:
        logging.exception(f"未預期的例外錯誤: {e}")