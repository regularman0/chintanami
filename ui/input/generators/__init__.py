# Path: ui/input/generators/__init__.py
# Version: 18.0
# Description: Фасад для рендереров ввода. Объединяет Time и List генераторы.

from .time_gens import TimeGenerator
from .list_gens import ListGenerator

class InputModuleRenderer:
    def __init__(self, input_tab, theme, managers, fas_config):
        self.time = TimeGenerator(input_tab, theme, managers, fas_config)
        self.list = ListGenerator(input_tab, theme, managers, fas_config)

    # Делегирование методов
    def draw_range(self, *args): self.time.draw_range(*args)
    def draw_duration(self, *args): self.time.draw_duration(*args)
    def draw_checks(self, *args): self.list.draw_checks(*args)
    def draw_tags(self, *args): self.list.draw_tags(*args)