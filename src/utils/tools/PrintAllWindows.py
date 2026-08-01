import win32gui
import win32process
'''
功能:列出所有窗口名稱與窗柄(PID)以及窗口標題(Title)
'''

def list_windows():
  print("=" * 60)
  print(f"{'ID':<5} | {'HWND':<10} | {'PID':<6} | {'視窗標題 (Title)'}")
  print("=" * 60)

  windows = []

  def enum_handler(hwnd, lParam):
    # 只抓取「看得見」且「有標題」的主視窗
    if win32gui.IsWindowVisible(hwnd):
      title = win32gui.GetWindowText(hwnd)
      if title.strip():  # 排除空標題
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        windows.append((hwnd, pid, title))
    return True

  win32gui.EnumWindows(enum_handler, None)

  # 印出所有視窗清單
  for idx, (hwnd, pid, title) in enumerate(windows):
    print(f"{idx:<5} | {hwnd:<10} | {pid:<6} | {title}")

  print("=" * 60)



if __name__ == "__main__":
  list_windows()