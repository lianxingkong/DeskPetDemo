from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH,env_prefix="SWITCH__", extra="ignore")
    call_AI_is_enable: bool = True
    image_handle_is_enable: bool = True
    memory_handle_is_enable: bool = True
    voice_handle_is_enable: bool = True

class OpenAIConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_prefix="OPENAI__", extra="ignore")
    api_url: str
    api_key: str

class BaiduAIConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_prefix="BAIDU__", extra="ignore")
    report_url: str
    get_result_url: str
    api_key: str
    secret_key: str
    token_url: str

class MemoryConfig(BaseConfig):
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_prefix="MEMORY__", extra="ignore")
    threshold : float
class AppConfig:
    """应用顶层配置（全局单例）"""
    def __init__(self):
        self.base = BaseConfig()
        self.openai = OpenAIConfig()
        self.baidu = BaiduAIConfig()
        self.memorial = MemoryConfig()

app_config = AppConfig()
