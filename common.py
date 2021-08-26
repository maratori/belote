from enum import Enum, auto


class AutoName(Enum):
    # noinspection PyMethodParameters
    def _generate_next_value_(name, start, count, last_values):
        return name


class Suit(Enum):
    # NONE = "A"
    # NONE = "🅰"
    NONE = "𝔸"
    SPADES = "♠️"
    HEARTS = "♥️"
    CLUBS = "♣️"
    DIAMONDS = "♦️"


class Location(AutoName):
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
