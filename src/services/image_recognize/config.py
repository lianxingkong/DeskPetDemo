from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH,env_prefix="SWITCH__", extra="ignore")
    image_handle_is_enable: bool = True

class BaiduAIConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_prefix="BAIDU__", extra="ignore")
    report_url: Optional[str] = None
    get_result_url: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    token_url: Optional[str] = None

class AppConfig:
    """应用顶层配置（包内单例）"""
    def __init__(self):
        self.base = BaseConfig()
        self.baidu = BaiduAIConfig()

app_config = AppConfig()