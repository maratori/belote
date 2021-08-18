from enum import Enum


class AutoName(Enum):
    # noinspection PyMethodParameters
    def _generate_next_value_(name, start, count, last_values):
        return name


class Suit(Enum):
    NONE = "A"
    SPADES = "♠️"
    HEARTS = "♥️"
    CLUBS = "♣️"
    DIAMONDS = "♦️"
