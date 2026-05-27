from .config import app_config

if app_config.base.image_handle_is_enable:
    from .photo_handle_tools import *