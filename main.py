import collections
import itertools
from threading import Timer
from typing import Optional

from lona import LonaApp
from lona.events.input_event import InputEvent
from lona.html import HTML, Div, H1, Button, Br, Label, CheckBox, Pre, TextInput, Select, Widget
from lona.html.abstract_node import AbstractNode
from lona.request import Request
from lona.static_files import StyleSheet
from lona.view import LonaView

from bazar import Player, BazarFSM, MIN_BET, MIN_CAPO_BET
from common import Suit

RECONTRA_TIMEOUT = 10  # seconds

app = LonaApp(__file__)


# TODO: find better way
class AddStyle(AbstractNode):
    STATIC_FILES = [
        StyleSheet("style.css", "style.css")
    ]


def make_first(arr, elem):
    l = list(arr)
    n = l.index(elem)
    return l[n:] + l[:n]


class PlayerWidget(Widget):
    def __init__(self, name: str, location: str) -> None:
        self._name = Div(name, _class="user-name")
        # two elements is necessary to "repeat" animation without js
        self._said_a = Div(_class="bubble")
        self._said_b = Div(_class="bubble")
        self._using_a = False
        self._text_number = 0
        self.nodes = [
            Div(
                self._name,
                self._said_a,
                self._said_b,
                _class=["player-widget", location]
            )
        ]

    def said(self, text: str, number: int) -> None:
        if self._text_number != number:
            self._text_number = number
            if self._using_a:
                self._said_a.class_list.remove("show")
                self._said_b.class_list.append("show")
                self._said_b.set_text(text)
            else:
                self._said_b.class_list.remove("show")
                self._said_a.class_list.append("show")
                self._said_a.set_text(text)
            self._using_a = not self._using_a

    def should_say(self) -> None:
        self._name.class_list.append("should-say")

    def should_not_say(self) -> None:
        self._name.class_list.remove("should-say")


@app.route("/")
class MultiplayerBazarView(LonaView):
    def __init__(self, server, view_runtime, request):
        super().__init__(server, view_runtime, request)

        if "bazar" not in self.server.state:
            self.server.state["bazar"] = {
                "fsm": BazarFSM(),
                "players": 0,
                "timer": None,
                "player_said": {p: ("", 0) for p in Player},
                "waiting_player": Player.A,
            }
        self.server_state = self.server.state["bazar"]
        self.player = self._next_player()

        self.initialized = False

        self.players: dict[Player, PlayerWidget] = {
            player: PlayerWidget(player.value, pos)
            for player, pos in zip(make_first(Player, self.player), ["bottom", "left", "top", "right"])
        }
        self.pass_btn = Button("Pass")
        self.bet_btn = Button("Bet")
        self.contra_in_bet_container_btn = Button("Contra")
        self.contra_btn = Button("Contra", _class="contra")
        self.recontra_btn = Button("Recontra")
        self.recontra_timer_bar = Div(_class="recontra-timer", style={"animation-duration": f"{RECONTRA_TIMEOUT}s"})
        self.capo_checkbox = CheckBox(bubble_up=True)
        self.suit_selector = Select(values=[[s.value, s.value] for s in Suit], bubble_up=True)
        self.amount_input = TextInput(MIN_BET, type="number", bubble_up=True)
        self.bet_container = Div(
            self.suit_selector,
            self.amount_input,
            Label(self.capo_checkbox, "Capo"),
            Br(),
            self.pass_btn,
            self.bet_btn,
            self.contra_in_bet_container_btn,
            _class="bet-container"
        )
        self.recontra_container = Div(
            self.recontra_btn,
            self.recontra_timer_bar,
            _class="recontra-container"
        )

    def _next_player(self) -> Player:
        self.server_state["players"] += 1
        if self.server_state["players"] == 1:
            return Player.A
        elif self.server_state["players"] == 2:
            return Player.B
        elif self.server_state["players"] == 3:
            return Player.C
        elif self.server_state["players"] == 4:
            return Player.D
        else:
            raise RuntimeError("too many users")

    @property
    def fsm(self) -> BazarFSM:
        return self.server_state["fsm"]

    @property
    def timer(self) -> Timer:
        return self.server_state["timer"]

    @timer.setter
    def timer(self, timer: Timer) -> None:
        self.server_state["timer"] = timer

    @property
    def player_said(self) -> dict[Player, tuple[str, int]]:
        return self.server_state["player_said"]

    @property
    def waiting_player(self) -> Optional[Player]:
        return self.server_state["waiting_player"]

    @waiting_player.setter
    def waiting_player(self, player: Optional[Player]) -> None:
        self.server_state["waiting_player"] = player

    def update_state(self):
        for view in self.iter_objects():
            view._update_state()

    def _update_state(self):
        for p, w in self.players.items():
            w.said(*self.player_said[p])
            if p == self.waiting_player:
                w.should_say()
            else:
                w.should_not_say()

        if self.waiting_player == self.player:
            self.bet_container.show()
            if self.fsm.memory.last_bet_amount is not None:
                self.amount_input.value = self.fsm.memory.last_bet_amount + 1
            if self.fsm.memory.capo:
                self.capo_checkbox.value = True
                self.capo_checkbox.disabled = True
            if self.fsm.can_contra(self.player):
                self.contra_in_bet_container_btn.show()
            else:
                self.contra_in_bet_container_btn.hide()
            self.contra_btn.hide()
        else:
            self.bet_container.hide()
            if self.fsm.can_contra(self.player):
                self.contra_btn.show()
            else:
                self.contra_btn.hide()

        if self.fsm.can_recontra(self.player):
            self.recontra_container.show()
            self.recontra_timer_bar.class_list.append("start")
        else:
            self.recontra_container.hide()

        if self.initialized:
            self.show()

    def handle_request(self, request: Request):
        self.daemonize()
        self.update_state()
        self.initialized = True
        self.show(
            HTML(
                Div(
                    *self.players.values(),
                    self.bet_container,
                    self.contra_btn,
                    self.recontra_container,
                ),
            )
        )
        # need not to return to demonize view
        while True:
            self.sleep(10)

    def say(self, text: str) -> None:
        self.player_said[self.player] = (text, self.player_said[self.player][1] + 1)

    def handle_input_event(self, event: InputEvent):
        if event.node is self.pass_btn:
            if self.fsm.can_pass(self.player):
                self.fsm.handle_pass(self.player)
                self.say("Pass")
                self.waiting_player = self.fsm.memory.current_player
        if event.node is self.bet_btn:
            if self.fsm.can_bet(
                    self.player,
                    Suit(self.suit_selector.value),
                    int(self.amount_input.value),
                    self.capo_checkbox.value,
            ):
                self.fsm.handle_bet(
                    self.player,
                    Suit(self.suit_selector.value),
                    int(self.amount_input.value),
                    self.capo_checkbox.value,
                )
                if self.capo_checkbox.value:
                    self.say(f"{Suit(self.suit_selector.value).value}{self.amount_input.value}cp")
                else:
                    self.say(f"{Suit(self.suit_selector.value).value}{self.amount_input.value}")
                self.waiting_player = self.fsm.memory.current_player
        if event.node is self.contra_in_bet_container_btn or event.node is self.contra_btn:
            if self.fsm.can_contra(self.player):
                self.fsm.handle_contra(self.player)
                self.start_recontra_timer()
                self.say("Contra")
                self.waiting_player = None
        if event.node is self.recontra_btn:
            if self.fsm.can_recontra(self.player):
                self.cancel_timer()
                self.fsm.handle_recontra(self.player)
                self.say("Recontra")
                self.waiting_player = None
        if event.node is self.capo_checkbox:
            if self.amount_input.value < MIN_CAPO_BET:
                self.amount_input.value = MIN_CAPO_BET
        self.update_state()

    def start_recontra_timer(self):
        def fn():
            if self.fsm.can_timeout():
                self.fsm.handle_timeout()
            self.update_state()
            self.timer = None

        self.update_state()
        self.timer = Timer(RECONTRA_TIMEOUT, fn)
        self.timer.start()

    def cancel_timer(self):
        self.timer.cancel()
        self.timer = None
        self.update_state()


app.run(port=8080)
