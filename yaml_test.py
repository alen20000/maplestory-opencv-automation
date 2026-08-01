import yaml
# 直接讀取指定路徑的 YAML 檔
with open("config/global.yaml", "r", encoding="utf-8") as f:
  config = yaml.safe_load(f)

# 精準印出 config 結構下的 game.title
game_title = config["game"]["title"]
print(f"成功讀取遊戲標題: {game_title}")