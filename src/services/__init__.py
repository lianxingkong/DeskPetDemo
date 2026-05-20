from .config import app_config

if app_config.base.is_enable:
    from .base_callAI_services.call_openai_tools import *
    from .image_recognize_services.photo_handle_tools import *
    from .voice_recognize_services.get_voice_tools import *
    from .voice_recognize_services.faster_whisper_tools import *
