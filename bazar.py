from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from common import AutoName, Suit
from fsm import Transition, FSM

MIN_BET = 8
MIN_CAPO_BET = 25


class Team(Enum):
    A = "Team A"
    B = "Team B"

    @property
    def players(self) -> list['Player']:
        return [p for p in Player if p.team == self]


class Player(Enum):
    def __new__(cls, name: str, team: Team):
        obj = object.__new__(cls)
        obj._value_ = name
        obj.team = team
        return obj

    A = ("Player A", Team.A)
    B = ("Player B", Team.B)
    C = ("Player C", Team.A)
    D = ("Player D", Team.B)


class Event(AutoName):
    PASS = auto()
    BET = auto()
    CAPO_BET = auto()
    CONTRA = auto()
    RECONTRA = auto()
    TIMEOUT = auto()


@dataclass
class EventData:
    player: Optional[Player] = None
    suit: Optional[Suit] = None
    amount: Optional[int] = None


class State(AutoName):
    NO_BET = auto()
    BET = auto()
    CAPO_BET = auto()
    CONTRA = auto()
    REDIAL = auto()
    PLAY = auto()


@dataclass
class Memory:
    current_player: Player
    pass_count: int = 0
    last_bet_player: Optional[Player] = None
    last_bet_suit: Optional[Suit] = None
    last_bet_amount: Optional[int] = None
    capo: bool = False
    contra: bool = False
    recontra: bool = False


class BazarFSM(FSM[State, Memory, Event, EventData]):
    def __init__(self, state: State = None, memory: Memory = None):
        super().__init__(
            state or State.NO_BET,
            memory or Memory(
                current_player=Player.A,
            ),
            [
                Transition(
                    Event.BET, State.NO_BET, State.BET,
                    [is_current_player, is_bet_at_least_8],
                    [save_bet, reset_pass_count, go_to_next_user],
                ),
                Transition(
                    Event.BET, State.BET, State.BET,
                    [is_current_player, is_bet_increased],
                    [save_bet, reset_pass_count, go_to_next_user],
                ),

                Transition(
                    Event.CAPO_BET, State.NO_BET, State.CAPO_BET,
                    [is_current_player, is_bet_at_least_25],
                    [save_bet, mark_capo_true, reset_pass_count, go_to_next_user],
                ),
                Transition(
                    Event.CAPO_BET, State.BET, State.CAPO_BET,
                    [is_current_player, is_bet_at_least_25, is_bet_increased],
                    [save_bet, mark_capo_true, reset_pass_count, go_to_next_user],
                ),
                Transition(
                    Event.CAPO_BET, State.CAPO_BET, State.CAPO_BET,
                    [is_current_player, is_bet_increased],
                    [save_bet, reset_pass_count, go_to_next_user],
                ),

                Transition(
                    Event.PASS, State.NO_BET, State.NO_BET,
                    [is_current_player, is_not_4th_pass],
                    [increment_pass_count, go_to_next_user],
                ),
                Transition(
                    Event.PASS, State.BET, State.BET,
                    [is_current_player, is_not_4th_pass],
                    [increment_pass_count, go_to_next_user],
                ),
                Transition(
                    Event.PASS, State.CAPO_BET, State.CAPO_BET,
                    [is_current_player, is_not_4th_pass],
                    [increment_pass_count, go_to_next_user],
                ),

                Transition(
                    Event.PASS, State.NO_BET, State.REDIAL,
                    [is_current_player, is_4th_pass],
                    increment_pass_count,
                ),
                Transition(
                    Event.PASS, State.BET, State.PLAY,
                    [is_current_player, is_4th_pass],
                    increment_pass_count,
                ),
                Transition(
                    Event.PASS, State.CAPO_BET, State.PLAY,
                    [is_current_player, is_4th_pass],
                    increment_pass_count,
                ),

                Transition(
                    Event.CONTRA, State.BET, State.CONTRA,
                    is_last_bet_from_another_team,
                    mark_contra_true,
                ),
                Transition(
                    Event.CONTRA, State.CAPO_BET, State.CONTRA,
                    is_last_bet_from_another_team,
                    mark_contra_true,
                ),
                Transition(
                    Event.RECONTRA, State.CONTRA, State.PLAY,
                    is_last_bet_from_same_team,
                    mark_recontra_true,
                ),
                Transition(
                    Event.TIMEOUT, State.CONTRA, State.PLAY,
                ),
            ],
        )

    def can_pass(self, player: Player) -> bool:
        return self.can_handle_event(Event.PASS, EventData(player=player))

    def handle_pass(self, player: Player) -> bool:
        return self.handle_event(Event.PASS, EventData(player=player))

    def can_bet(self, player: Player, suit: Suit, bet: int, capo: bool) -> bool:
        if capo:
            return self.can_handle_event(Event.CAPO_BET, EventData(player=player, suit=suit, amount=bet))
        else:
            return self.can_handle_event(Event.BET, EventData(player=player, suit=suit, amount=bet))

    def handle_bet(self, player: Player, suit: Suit, bet: int, capo: bool) -> bool:
        if capo:
            return self.handle_event(Event.CAPO_BET, EventData(player=player, suit=suit, amount=bet))
        else:
            return self.handle_event(Event.BET, EventData(player=player, suit=suit, amount=bet))

    def can_contra(self, player: Player) -> bool:
        return self.can_handle_event(Event.CONTRA, EventData(player=player))

    def handle_contra(self, player: Player) -> bool:
        return self.handle_event(Event.CONTRA, EventData(player=player))

    def can_recontra(self, player: Player) -> bool:
        return self.can_handle_event(Event.RECONTRA, EventData(player=player))

    def handle_recontra(self, player: Player) -> bool:
        return self.handle_event(Event.RECONTRA, EventData(player=player))

    def can_timeout(self) -> bool:
        return self.can_handle_event(Event.TIMEOUT, EventData())

    def handle_timeout(self) -> bool:
        return self.handle_event(Event.TIMEOUT, EventData())


def is_current_player(state: State, memory: Memory, e: Event, data: EventData) -> bool:
    return memory.current_player == data.player


def is_bet_at_least_8(state: State, memory: Memory, e: Event, data: EventData) -> bool:
    return data.amount >= MIN_BET


def is_bet_at_least_25(state: State, memory: Memory, e: Event, data: EventData) -> bool:
    return data.amount >= MIN_CAPO_BET


def is_bet_increased(state: State, memory: Memory, e: Event, data: EventData) -> bool:
    return data.amount > memory.last_bet_amount


def is_4th_pass(state: State, memory: Memory, e: Event, data: EventData) -> bool:
    return memory.pass_count + 1 == 4  # +1 from incoming event


def is_not_4th_pass(state: State, memory: Memory, e: Event, data: EventData) -> bool:
    return memory.pass_count + 1 < 4  # +1 from incoming event


def is_last_bet_from_same_team(s: State, memory: Memory, e: Event, data: EventData) -> bool:
    return memory.last_bet_player.team == data.player.team


def is_last_bet_from_another_team(s: State, memory: Memory, e: Event, data: EventData) -> bool:
    return memory.last_bet_player.team != data.player.team


def go_to_next_user(from_: State, to: State, memory: Memory, e: Event, d: EventData) -> None:
    if memory.current_player == Player.A:
        memory.current_player = Player.B
    elif memory.current_player == Player.B:
        memory.current_player = Player.C
    elif memory.current_player == Player.C:
        memory.current_player = Player.D
    elif memory.current_player == Player.D:
        memory.current_player = Player.A


def increment_pass_count(from_: State, to: State, memory: Memory, e: Event, d: EventData) -> None:
    memory.pass_count += 1


def reset_pass_count(from_: State, to: State, memory: Memory, e: Event, d: EventData) -> None:
    memory.pass_count = 0


def save_bet(from_: State, to: State, memory: Memory, e: Event, data: EventData) -> None:
    memory.last_bet_player = data.player
    memory.last_bet_suit = data.suit
    memory.last_bet_amount = data.amount


def mark_capo_true(from_: State, to: State, memory: Memory, e: Event, d: EventData) -> None:
    memory.capo = True


def mark_contra_true(from_: State, to: State, memory: Memory, e: Event, d: EventData) -> None:
    memory.contra = True


def mark_recontra_true(from_: State, to: State, memory: Memory, e: Event, d: EventData) -> None:
    memory.recontra = True
