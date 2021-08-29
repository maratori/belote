from lona.events import CHANGE
from lona.html import InputNode


class RadioButton(InputNode):
    ATTRIBUTES = {'type': 'radio'}
    EVENTS = [CHANGE]

    @property
    def value(self) -> str:
        return self.attributes.get("value", "")

    @value.setter
    def value(self, value: str) -> None:
        self.attributes["value"] = str(value)

    @property
    def checked(self) -> bool:
        return self.attributes.get("checked", False)

    @checked.setter
    def checked(self, checked: bool) -> None:
        self.attributes["checked"] = bool(checked)
