from .config import app_config


if app_config.base.call_AI_is_enable:
    from .base_callAI_services.call_openai_tools import *

if app_config.base.image_handle_is_enable:
    from .image_recognize_services.photo_handle_tools import *

if app_config.base.voice_handle_is_enable:
    from .voice_recognize_services.get_voice_tools import *
    from .voice_recognize_services.faster_whisper_tools import *

if app_config.base.memory_handle_is_enable:
    from .memory_manage_services.memory_tools import *
