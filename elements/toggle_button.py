from typing import Callable

from lona.events.input_event import InputEvent

from elements.button import Button


class ToggleButton(Button):
    def __init__(
            self,
            *args,
            pressed: bool = False,
            on_click: Callable[['ToggleButton', InputEvent], None] = None,
            pressed_class_name: str = "pressed",
            **kwargs
    ) -> None:
        super().__init__(*args, on_click=on_click, **kwargs)
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

    def handle_click(self, event: InputEvent) -> None:
        self.toggle()
        super().handle_click(event)
