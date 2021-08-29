from typing import Callable, Optional

from lona.events.input_event import InputEvent
from lona.html import Button as LonaButton, Widget


class Button(LonaButton, Widget):
    def __init__(
            self,
            *args,
            on_click: Callable[['Button', InputEvent], None] = None,
            bubble_up: bool = False,
            **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.on_click = on_click
        self.bubble_up = bubble_up

    def handle_input_event(self, event: InputEvent) -> Optional[InputEvent]:
        if event.node is self:
            if self.on_click is not None:
                self.on_click(self, event)
            if not self.bubble_up:
                return None
        return event
