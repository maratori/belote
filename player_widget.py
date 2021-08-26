from typing import Union

from lona.html import Widget, Div, Node
from lona.html.abstract_node import AbstractNode

from common import Location


# css classes
class CLASS:
    PLAYER_WIDGET = "player-widget"
    FIRST = "first"
    SHOULD_ACT = "should-act"
    IMAGE = "image"
    NAME = "name"
    BUBBLE = "bubble"
    SHOW = "show"
    LOCATIONS: dict[Location, str] = {
        Location.TOP: "top",
        Location.BOTTOM: "bottom",
        Location.LEFT: "left",
        Location.RIGHT: "right",
    }


class PlayerWidget(Widget):
    def __init__(self, name: str = "", location: Location = Location.TOP, first: bool = False) -> None:
        self._name = Div(_class=CLASS.NAME)
        # two elements is necessary to "repeat" animation without js
        self._said_a = Div(_class=CLASS.BUBBLE)
        self._said_b = Div(_class=CLASS.BUBBLE)
        self._using_a = False
        self._text_number = 0
        self._container = Div(_class=CLASS.PLAYER_WIDGET, nodes=[
            Div(_class=CLASS.IMAGE, nodes=[
                "👤",
            ]),
            self._name,
            self._said_a,
            self._said_b,
        ])
        self.nodes = [self._container]
        self.change_name(name)
        self.change_location(location)
        self.mark_first(first)

    def change_name(self, name: str) -> None:
        self._name.set_text(name)

    def change_location(self, location: Location) -> None:
        for cl in CLASS.LOCATIONS.values():
            self._container.class_list.remove(cl)
        self._container.class_list.append(CLASS.LOCATIONS[location])

    def mark_first(self, first: bool) -> None:
        if first:
            self._container.class_list.append(CLASS.FIRST)
        else:
            self._container.class_list.remove(CLASS.FIRST)

    def said(self, text: Union[str, AbstractNode], number: int) -> None:
        if self._text_number != number:
            self._text_number = number
            if self._using_a:
                self._said_a.class_list.remove(CLASS.SHOW)
                self._said_b.class_list.append(CLASS.SHOW)
                self._said_b.nodes = text
            else:
                self._said_b.class_list.remove(CLASS.SHOW)
                self._said_a.class_list.append(CLASS.SHOW)
                self._said_a.nodes = text
            self._using_a = not self._using_a

    def should_act(self, yes: bool) -> None:
        if yes:
            self._container.class_list.append(CLASS.SHOULD_ACT)
        else:
            self._container.class_list.remove(CLASS.SHOULD_ACT)
