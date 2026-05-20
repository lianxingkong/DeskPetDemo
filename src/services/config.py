import os
from dataclasses import dataclass

@dataclass
class BaseConfig:
    is_enable: bool = True
@dataclass
class OpenAIConfig:
    api_url: str = os.getenv("OPENAI__API_URL", "")
    api_key: str = os.getenv("OPENAI__API_KEY", "")

@dataclass
class BaiduAIConfig:
    report_url: str = os.getenv("BAIDUAI__REPORT_REQUEST_URL", "")
    get_result_url: str = os.getenv("BAIDUAI__GET_RESULT_URL", "")
    api_key: str = os.getenv("BAIDUAI__API_KEY", "")
    secret_key: str = os.getenv("BAIDUAI__SECRET_KEY", "")
    token_url: str = os.getenv("BAIDUAI___TOKEN_URL", "")

class AppConfig:
    """应用顶层配置（全局单例）"""
    def __init__(self):
        self.base = BaseConfig()
        self.openai = OpenAIConfig()   # OpenAI 相关
        self.baidu = BaiduAIConfig()   # 百度 AI 相关

# 直接在模块级实例化，全局唯一
app_config = AppConfig()
