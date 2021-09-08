from lona.events import CHANGE
from lona.html import Node


class RadioButton(Node):
    TAG_NAME = "input"
    SELF_CLOSING_TAG = True
    ATTRIBUTES = {"type": "radio"}
    EVENTS = [CHANGE]

    @property
    def value(self) -> str:
        return self.attributes.get("value", "")

    @value.setter
    def value(self, value: str) -> None:
        self.attributes["value"] = str(value)

    @property
    def checked(self) -> bool:
        return "checked" in self.attributes

    @checked.setter
    def checked(self, checked: bool) -> None:
        if checked:
            self.attributes["checked"] = ""
        else:
            del self.attributes["checked"]

    @property
    def disabled(self) -> bool:
        return "disabled" in self.attributes

    @disabled.setter
    def disabled(self, disabled: bool) -> None:
        if disabled:
            self.attributes["disabled"] = ""
        else:
            del self.attributes["disabled"]
