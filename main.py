from dataclasses import dataclass
from datetime import datetime

from lona import LonaApp
from lona.contrib.bootstrap3 import Row, ColMd6
from lona.events.input_event import InputEvent
from lona.html import HTML, Div, H1, TextArea, H2, Hr, Button, Span, Br, Label, CheckBox, Pre, TextInput, Node
from lona.request import Request
from lona.view import LonaView

from bazar import Player, BazarFSM
from common import Suit

app = LonaApp(__file__)


@app.route("/")
class ClockView(LonaView):
    def handle_request(self, request):
        timestamp = Div()

        html = HTML(
            H1("Clock"),
            timestamp,
        )

        while True:
            timestamp.set_text(str(datetime.now()))

            self.show(html)

            self.sleep(1)


@app.route("/chat/<topic>/")
class MultiUserChat(LonaView):
    def add_message_to_history(self, message, show=True):
        issuer, text = message

        self.history.append(
            Div('{}: {}'.format(issuer, text))
        )

        if show:
            self.show()

    def update_user_list(self):
        with self.html.lock:
            self.user_list.clear()
            self.user_list.append(Div('User Online: '))

            for user in self.state['user']:
                self.user_list.append(Div('    {}'.format(str(user))))

        self.show()

    def handle_request(self, request):
        self.topic = request.match_info.get('topic', '')

        # setup state
        self.state = None

        with self.server.state.lock:
            if 'multi-user-chat' not in self.server.state:
                self.server.state['multi-user-chat'] = {}

            if self.topic not in self.server.state['multi-user-chat']:
                self.server.state['multi-user-chat'][self.topic] = {
                    'user': [],
                    'messages': [],
                }

            self.state = self.server.state['multi-user-chat'][self.topic]

            # setup user list
            if self.request.user not in self.state['user']:
                self.state['user'].append(self.request.user)

            # setup history
            messages = self.state['messages']
            self.history = Div()

            for message in messages:
                self.add_message_to_history(message, show=False)

        # setup html
        self.user_list = Div()
        self.text_area = TextArea()

        self.html = HTML(
            H1('Multi User Chat'),
            H2('Topic: {}'.format(self.topic or '(blank)')),

            self.user_list,
            Hr(),

            self.history,
            Hr(),

            self.text_area,
            Button('Send', _id='send')
        )

        for view_object in self.iter_objects():
            if view_object.topic != self.topic:
                continue

            view_object.update_user_list()

        # main loop (waiting for messages)
        while True:
            self.show(self.html)
            self.await_click()

            message = (str(self.request.user), self.text_area.value,)

            with self.state.lock:
                self.state['messages'].append(
                    message,
                )

                for view_object in self.iter_objects():
                    if view_object.topic != self.topic:
                        continue

                    view_object.add_message_to_history(message)

    def on_shutdown(self, reason):
        with self.state.lock:
            if self.request.user in self.state['user']:
                self.state['user'].remove(self.request.user)

            for view_object in self.iter_objects():
                if view_object.topic != self.topic:
                    continue

                view_object.update_user_list()


@app.route("/daemon")
class DaemonView(LonaView):
    def handle_request(self, request):
        self.timestamp = Span()

        html = HTML(
            H1('Daemon View'),
            'user: ', Span(str(request.user)),
            Br(),
            'connection: ', Span(str(request.connection)),
            Br(),
            'started: ', Span(str(datetime.now())),
            Br(),
            'running since: ', self.timestamp,
            Br(),
            Button('Stop View', _id='stop-view'),
        )

        self.daemonize()
        self.running = True

        while self.running:
            self.timestamp.set_text(str(datetime.now()))
            self.show(html)
            self.sleep(1)

    def handle_input_event(self, input_event):
        if input_event.node_has_id('stop-view'):
            self.running = False


@dataclass
class PlayerInputs:
    pass_: Button
    bet: Button
    contra: Button
    recontra: Button
    capo: CheckBox
    amount: TextInput


@app.route("/bazar")
class DaemonView(LonaView):
    def __init__(self, server, view_runtime, request):
        super().__init__(server, view_runtime, request)
        self.fsm = BazarFSM()
        self.state = Pre()
        self.memory = Pre()
        self.history = Pre()
        self.players: dict[Player, PlayerInputs] = {
            p: PlayerInputs(
                pass_=Button("Pass"),
                bet=Button("Bet"),
                contra=Button("Contra"),
                recontra=Button("Recontra"),
                capo=CheckBox(bubble_up=True),
                amount=TextInput(8, type="number", bubble_up=True),
            ) for p in Player
        }
        self.initialized = False

    def update_state(self):
        self.state.set_text(self.fsm.current_state)
        self.memory.clear()
        self.memory.write_line(f"current_player: {self.fsm.memory.current_player}")
        self.memory.write_line(f"pass_count: {self.fsm.memory.pass_count}")
        self.memory.write_line(f"last_bet_player: {self.fsm.memory.last_bet_player}")
        self.memory.write_line(f"last_bet_suit: {self.fsm.memory.last_bet_suit}")
        self.memory.write_line(f"last_bet_amount: {self.fsm.memory.last_bet_amount}")
        self.memory.write_line(f"capo: {self.fsm.memory.capo}")
        self.memory.write_line(f"contra: {self.fsm.memory.contra}")
        self.memory.write_line(f"recontra: {self.fsm.memory.recontra}")

        for p, inputs in self.players.items():
            inputs.pass_.disabled = not self.fsm.can_pass(p)
            inputs.bet.disabled = not self.fsm.can_bet(p, Suit.CLUBS, int(inputs.amount.value), inputs.capo.value)
            inputs.contra.disabled = not self.fsm.can_contra(p)
            inputs.recontra.disabled = not self.fsm.can_recontra(p)

        if self.initialized:
            self.show()

    def handle_request(self, request: Request):
        self.update_state()
        self.initialized = True
        return HTML(
            Node("button:disabled { color: white; }", tag_name="style"),
            Row(
                ColMd6(
                    H1("State"),
                    self.state,
                    H1("Memory"),
                    self.memory,
                    H1("History"),
                    self.history,
                ),
                ColMd6(*[
                    Row(
                        H1(p.value),
                        Label("Amount", inputs.amount),
                        Br(),
                        Label(inputs.capo, "Capo"),
                        Br(),
                        inputs.pass_,
                        inputs.bet,
                        inputs.contra,
                        inputs.recontra,
                    ) for p, inputs in self.players.items()
                ]),
            )
        )

    def handle_input_event(self, event: InputEvent):
        for p, inputs in self.players.items():
            if event.node == inputs.pass_:
                if self.fsm.can_pass(p):
                    self.fsm.handle_pass(p)
                break
            if event.node == inputs.bet:
                if self.fsm.can_bet(p, Suit.CLUBS, int(inputs.amount.value), inputs.capo.value):
                    self.fsm.handle_bet(p, Suit.CLUBS, int(inputs.amount.value), inputs.capo.value)
                break
            if event.node == inputs.contra:
                if self.fsm.can_contra(p):
                    self.fsm.handle_contra(p)
                break
            if event.node == inputs.recontra:
                if self.fsm.can_recontra(p):
                    self.fsm.handle_recontra(p)
                break
        self.update_state()


app.run(port=8080)
