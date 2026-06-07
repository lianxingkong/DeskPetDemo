from dataclasses import dataclass


@dataclass
class UISettingConfig:
    RESOURCES_DIR : str = "C:/Users\qy229\Documents\codes\DeskPet\src/resources"
    HTTP_PORT : int = 8111

class UIConfig:
    def __init__(self):
        self.ui = UISettingConfig()

# 此包内全局唯一实例化
ui_setting = UIConfig()