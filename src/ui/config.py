import os
from dataclasses import dataclass


@dataclass
class UISettingConfig:
    loadUi : str = 'C:/Users/qy229/Documents/codes/DeskPet/untitled.ui'
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path : str = os.path.join(current_dir, '..', 'resources', 'krx.gif')

class UIConfig:
    def __init__(self):
        self.ui = UISettingConfig()

# 此包内全局唯一实例化
ui_setting = UIConfig()