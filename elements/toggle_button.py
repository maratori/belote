from typing import Optional

from lona.events.input_event import InputEvent
from lona.html import Button


class ToggleButton(Button):
    def __init__(
            self,
            *args,
            pressed: bool = False,
            pressed_class_name: str = "pressed",
            **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self._pressed_class_name = pressed_class_name
        self.pressed = pressed

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
        if event.name == 'click':
            self.toggle()
        return super().handle_input_event(event)
