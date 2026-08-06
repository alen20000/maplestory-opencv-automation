from pathlib import Path
import yaml
'''
設定檔讀取
'''
class ConfigLoader():
    _instance = None
    _config = {} # 要用 .update合併大字典，要先設定空目錄，不然會報錯

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_yaml_config()
        return cls._instance
    
    def _load_yaml_config(self):
        root_dir = Path(__file__).resolve().parent
        '''設定檔清單'''
        config_files = ["config_default.yaml", "config_data.yaml"]

        for file_name in config_files:
            config_path = root_dir / file_name

            if not config_path.exists():
                raise FileNotFoundError(f"找不到設定檔: {config_path}")
                
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._config.update(data)

    def get(self, key_path, default=None):
        """
        支援點記號的 get 方法
        例如：config.get("database.connection.host")
        """
        # 把傳進來的字串用點點切開，變成清單。例如 "database.host" -> ["database", "host"]
        keys = key_path.split(".")
        value = self._config
        
        # 一層一層往下剝開找
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default  # 找不到就回傳預設值，絕對不當機
                
        return value

config = ConfigLoader()