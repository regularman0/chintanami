# Path: ui/input/generators/base.py
# Version: 18.0
# Description: Базовый класс генератора. Хранит контекст и утилиты.

class BaseGenerator:
    def __init__(self, input_tab, theme, managers, fas_config):
        self.tab = input_tab
        self.theme = theme
        self.mgrs = managers
        self.fas_config = fas_config

    def register_widget(self, key, widget):
        """Регистрирует виджет в основном табе для доступа к нему (например, для блокировки)"""
        self.tab.widgets[key] = widget