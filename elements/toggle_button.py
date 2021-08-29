from typing import Callable, Optional

from lona.events.input_event import InputEvent
from lona.html import Button as LonaButton, Widget


class ToggleButton(LonaButton, Widget):
    def __init__(
            self,
            *args,
            pressed: bool = False,
            on_click: Callable[['ToggleButton', InputEvent], None] = None,
            bubble_up: bool = False,
            pressed_class_name: str = "pressed",
            **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._pressed_class_name = pressed_class_name
        self.pressed = pressed
        self.on_click = on_click
        self.bubble_up = bubble_up

    @property
    def pressed(self) -> bool:
        return self._pressed_class_name in self.class_list

    @pressed.setter
    def pressed(self, value: bool) -> None:
        if value:
            self.class_list.add(self._pressed_class_name)
        else:
            self.class_list.remove(self._pressed_class_name)

    def toggle(self) -> None:
        with self.lock:
            self.pressed = not self.pressed

    def handle_input_event(self, event: InputEvent) -> Optional[InputEvent]:
        if event.node is self:
            self.toggle()
            if self.on_click is not None:
                self.on_click(self, event)
            if not self.bubble_up:
                return None
        return event
