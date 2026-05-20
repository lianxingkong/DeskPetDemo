from .config import ui_setting

if ui_setting.base.is_enable:
    from .based_ui import *