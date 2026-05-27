from .config import *

if app_config.base.voice_handle_is_enable:
    from .get_voice_tools import *
    from .faster_whisper_tools import *