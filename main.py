from datetime import datetime

from lona import LonaApp
from lona.html import HTML, Div, H1, TextArea, H2, Hr, Button, Span, Br
from lona.view import LonaView

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


app.run(port=8080)
