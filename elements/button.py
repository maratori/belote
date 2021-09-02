from typing import Callable, Optional

from lona.events.input_event import InputEvent
from lona.html import Button as LonaButton, Widget


class Button(LonaButton):
    def __init__(self, *args, on_click: Callable[['Button', InputEvent], None] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.on_click = on_click

    def handle_click(self, event: InputEvent) -> None:
        if self.on_click is not None:
            self.on_click(self, event)
