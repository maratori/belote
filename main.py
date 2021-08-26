from threading import Timer
from typing import Optional, Union

from lona import LonaApp
from lona.events.input_event import InputEvent
from lona.html import HTML, Div, Button, Br, Label, CheckBox, TextInput, Select, Node
from lona.request import Request
from lona.view import LonaView

from bazar import Player, BazarFSM, MIN_BET, MIN_CAPO_BET
from common import Suit, Location
from player_widget import PlayerWidget

RECONTRA_TIMEOUT = 10  # seconds

app = LonaApp(__file__)

app.add_static_file("lona/style.css", path="style.css")  # replace default styles


def make_first(arr, elem):
    l = list(arr)
    n = l.index(elem)
    return l[n:] + l[:n]


@app.route("/")
class MultiplayerBazarViewOnePage(LonaView):
    def handle_request(self, request):
        return HTML(
            Node(tag_name="iframe", src="/bazar/player/A", style={
                "position": "absolute",
                "inset": "0 50% 50% 0",
                "width": "50%",
                "height": "50%",
                "border": "10px black solid",
            }),
            Node(tag_name="iframe", src="/bazar/player/B", style={
                "position": "absolute",
                "inset": "0 0 50% 50%",
                "width": "50%",
                "height": "50%",
                "border": "10px black solid",
            }),
            Node(tag_name="iframe", src="/bazar/player/C", style={
                "position": "absolute",
                "inset": "50% 50% 0 0",
                "width": "50%",
                "height": "50%",
                "border": "10px black solid",
            }),
            Node(tag_name="iframe", src="/bazar/player/D", style={
                "position": "absolute",
                "inset": "50% 0 0 50%",
                "width": "50%",
                "height": "50%",
                "border": "10px black solid",
            }),
        )


@app.route("/bazar/player/<player>")
class MultiplayerBazarView(LonaView):
    def __init__(self, server, view_runtime, request: Request):
        super().__init__(server, view_runtime, request)

        if "bazar" not in self.server.state:
            self.server.state["bazar"] = {
                "fsm": BazarFSM(),
                "timer": None,
                "player_said": {p: ("", 0) for p in Player},
                "waiting_player": Player.A,
            }
        self.server_state = self.server.state["bazar"]
        self.player: Player = {
            "A": Player.A,
            "B": Player.B,
            "C": Player.C,
            "D": Player.D,
        }[request.match_info["player"]]

        self.initialized = False

        self.players: dict[Player, PlayerWidget] = {
            player: PlayerWidget(player.value, pos, player == Player.A)
            for player, pos in
            zip(make_first(Player, self.player), [Location.BOTTOM, Location.LEFT, Location.TOP, Location.RIGHT])
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
        self.bet_container = Div(_class="bet-container", nodes=[
            self.suit_selector,
            self.amount_input,
            Label(self.capo_checkbox, "Capo"),
            Br(),
            self.pass_btn,
            self.bet_btn,
            self.contra_in_bet_container_btn,
        ])
        self.recontra_container = Div(_class="recontra-container", nodes=[
            self.recontra_btn,
            self.recontra_timer_bar,
        ])

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
    def player_said(self) -> dict[Player, tuple[Union[str, HTML], int]]:
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
            w.should_act(p == self.waiting_player)

        if self.waiting_player == self.player:
            self.bet_container.show()
            if self.fsm.memory.last_bet_amount is not None:
                if int(self.amount_input.value) < self.fsm.memory.last_bet_amount + 1:
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

    def say(self, text: Union[str, HTML]) -> None:
        self.player_said[self.player] = (text, self.player_said[self.player][1] + 1)

    def handle_input_event(self, event: InputEvent):
        if event.node is self.pass_btn:
            if self.fsm.can_pass(self.player):
                can_continue = self.fsm.handle_pass(self.player)
                self.say("Pass")
                if can_continue:
                    self.waiting_player = self.fsm.memory.current_player
                else:
                    self.waiting_player = None
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
                    self.say(HTML(f"{Suit(self.suit_selector.value).value}{self.amount_input.value}<sup>cp</sup>"))
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
