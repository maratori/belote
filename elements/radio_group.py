from typing import Callable, Optional, Iterator

from lona.events.input_event import InputEvent
from lona.html import Widget
from lona.html.abstract_node import AbstractNode

from elements.radio_button import RadioButton


class RadioGroup(Widget):
    def __init__(
            self,
            nodes: list[AbstractNode],
            name: str,
            value: str = None,
            on_change: Callable[['RadioGroup', InputEvent], None] = None,
    ) -> None:
        self.on_change = on_change
        self.nodes = nodes
        with self.lock:
            for node in self._iter_radio_nodes_under_lock():
                node.attributes["name"] = name
        if value is not None:
            self.value = value

    @property
    def values(self) -> list[str]:
        with self.lock:
            return list(map(lambda n: n.value, self._iter_radio_nodes_under_lock()))

    @property
    def value(self) -> Optional[str]:
        with self.lock:
            for node in self._iter_radio_nodes_under_lock():
                if node.checked:
                    return node.value
        return None

    @value.setter
    def value(self, value: str) -> None:
        with self.lock:
            for node in self._iter_radio_nodes_under_lock():
                if node.value == value:
                    target_node = node
                    break
            else:
                raise ValueError(f"Unknown value for radio group: {value!r}")

            for node in self._iter_radio_nodes_under_lock():
                if node is not target_node:
                    node.checked = False

            target_node.checked = True

    def handle_change(self, event: InputEvent) -> None:
        with self.lock:
            for node in self._iter_radio_nodes_under_lock():
                if event.node is node:
                    self.value = node.value
                    if self.on_change is not None:
                        self.on_change(self, event)

    def _iter_radio_nodes_under_lock(self, node: AbstractNode = None) -> Iterator[RadioButton]:
        node = node or self
        if hasattr(node, "nodes"):
            for child in node.nodes:
                if isinstance(child, RadioButton):
                    yield child
                elif isinstance(child, RadioGroup):
                    continue
                else:
                    yield from self._iter_radio_nodes_under_lock(child)
