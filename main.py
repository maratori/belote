from threading import Timer
from typing import Optional, Union

from lona import LonaApp
from lona.html import HTML, Div, Node, Img
from lona.request import Request
from lona.view import LonaView

from bazar import Player, BazarFSM, MIN_BET
from common import Location
from widgets.bet_widget import BetWidget
from widgets.player_widget import PlayerWidget

RECONTRA_TIMEOUT = 10  # seconds

app = LonaApp(__file__)

app.add_static_file("lona/style.css", path="static/style.css")  # replace default styles
app.settings.STATIC_DIRS.append("static")


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
        self.bet_widget = BetWidget(
            RECONTRA_TIMEOUT,
            on_bet=self.on_bet,
            on_pass=self.on_pass,
            on_contra=self.on_contra,
            on_recontra=self.on_recontra,
        )

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
            self.bet_widget.show_full(
                MIN_BET if self.fsm.memory.last_bet_amount is None else self.fsm.memory.last_bet_amount + 1,
                self.fsm.memory.capo,
                self.fsm.can_contra(self.player),
            )
        elif self.fsm.can_contra(self.player):
            self.bet_widget.show_contra()
        elif self.fsm.can_recontra(self.player):
            self.bet_widget.show_recontra()
        elif self.timer is not None:
            self.bet_widget.show_timer()
        else:
            self.bet_widget.hide()

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
                    self.bet_widget,
                ),
            )
        )
        # need not to return to demonize view
        while True:
            self.sleep(10)

    def say(self, text: Union[str, HTML]) -> None:
        self.player_said[self.player] = (text, self.player_said[self.player][1] + 1)

    def on_bet(self, *args) -> None:
        suit = self.bet_widget.suit
        amount = self.bet_widget.amount
        capo = self.bet_widget.capo
        if self.fsm.can_bet(self.player, suit, amount, capo):
            self.fsm.handle_bet(self.player, suit, amount, capo)
            if capo:
                self.say(HTML(f"{suit.value}{amount}<sup>cp</sup>"))
            else:
                self.say(f"{suit.value}{amount}")
            self.waiting_player = self.fsm.memory.current_player
            self.update_state()

    def on_pass(self, *args) -> None:
        if self.fsm.can_pass(self.player):
            can_continue = self.fsm.handle_pass(self.player)
            self.say("Pass")
            if can_continue:
                self.waiting_player = self.fsm.memory.current_player
            else:
                self.waiting_player = None
            self.update_state()

    def on_contra(self, *args) -> None:
        if self.fsm.can_contra(self.player):
            self.fsm.handle_contra(self.player)
            self.start_recontra_timer()
            self.say("Contra")
            self.waiting_player = None
            self.update_state()

    def on_recontra(self, *args) -> None:
        if self.fsm.can_recontra(self.player):
            self.cancel_timer()
            self.fsm.handle_recontra(self.player)
            self.say("Recontra")
            self.waiting_player = None
            self.update_state()

    def start_recontra_timer(self):
        def fn():
            if self.fsm.can_timeout():
                self.fsm.handle_timeout()
            self.timer = None
            self.update_state()

        self.timer = Timer(RECONTRA_TIMEOUT, fn)
        self.timer.start()
        self.update_state()

    def cancel_timer(self):
        self.timer.cancel()
        self.timer = None
        self.update_state()


app.run(port=8080)
