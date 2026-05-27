from .config import app_config

if app_config.base.call_AI_is_enable:
    from .call_openai_tools import *