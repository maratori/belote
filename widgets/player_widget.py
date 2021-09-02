from typing import Union

from lona.html import Widget, Div
from lona.html.abstract_node import AbstractNode
from lona.static_files import StyleSheet

from common import Location


class CssClass:
    PLAYER_WIDGET = "player-widget"
    FIRST = "first"
    SHOULD_ACT = "player-widget-should-act"
    IMAGE = "image"
    NAME = "name"
    BUBBLE = "bubble"
    SHOW = "show"
    LOCATIONS = {
        Location.TOP: "top",
        Location.BOTTOM: "bottom",
        Location.LEFT: "left",
        Location.RIGHT: "right",
    }


class PlayerWidget(Widget):
    STATIC_FILES = [
        StyleSheet("player_widget.css", "player_widget.css")
    ]

    def __init__(self, name: str = "", location: Location = Location.TOP, first: bool = False) -> None:
        self._name = Div(name, _class=CssClass.NAME)
        # two elements is necessary to "repeat" animation without js
        self._said_a = Div(_class=CssClass.BUBBLE)
        self._said_b = Div(_class=CssClass.BUBBLE)
        self._using_a = False
        self._text_number = 0
        self._container = Div(_class=CssClass.PLAYER_WIDGET, nodes=[
            Div(_class=CssClass.IMAGE, nodes=[
                "👤",
            ]),
            self._name,
            self._said_a,
            self._said_b,
        ])
        self.change_location(location)
        self.mark_first(first)
        self.nodes = [self._container]

    def change_name(self, name: str) -> None:
        self._name.set_text(name)

    def change_location(self, location: Location) -> None:
        with self.lock:
            for cl in CssClass.LOCATIONS.values():
                self._container.class_list.remove(cl)
            self._container.class_list.add(CssClass.LOCATIONS[location])

    def mark_first(self, first: bool) -> None:
        if first:
            self._container.class_list.add(CssClass.FIRST)
        else:
            self._container.class_list.remove(CssClass.FIRST)

    def said(self, text: Union[str, AbstractNode], number: int) -> None:
        with self.lock:
            # TODO: In ideal world number should be saved outside PlayerWidget, it isn't its responsibility.
            if self._text_number != number:
                self._text_number = number
                if self._using_a:
                    self._said_a.class_list.remove(CssClass.SHOW)
                    self._said_b.class_list.add(CssClass.SHOW)
                    self._said_b.nodes = text
                else:
                    self._said_b.class_list.remove(CssClass.SHOW)
                    self._said_a.class_list.add(CssClass.SHOW)
                    self._said_a.nodes = text
                self._using_a = not self._using_a

    def should_act(self, yes: bool) -> None:
        if yes:
            self._container.class_list.add(CssClass.SHOULD_ACT)
        else:
            self._container.class_list.remove(CssClass.SHOULD_ACT)
