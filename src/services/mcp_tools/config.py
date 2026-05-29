from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH,env_prefix="SWITCH__", extra="ignore")
    yaohu_is_enable: bool = True

class YaoHuConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_prefix="YAOHU__", extra="ignore")
    api_key : Optional[str] = None
    secret_key : Optional[str] = None

class AppConfig:
    """应用顶层配置（包内单例）"""
    def __init__(self):
        self.yaohu = YaoHuConfig()


app_config = AppConfig()