from typing import Callable

from lona.events.input_event import InputEvent
from lona.html import Span, Widget, Div, Label, Button
from lona.static_files import StyleSheet

from bazar import MIN_BET, MIN_CAPO_BET
from common import Suit
from elements.radio_button import RadioButton
from elements.radio_group import RadioGroup
from elements.toggle_button import ToggleButton


class CssClass:
    BET_WIDGET = "bet-widget"
    FULL = "full"
    ONLY_CONTRA = "only-contra"
    ONLY_RECONTRA = "only-recontra"
    ONLY_TIMER = "only-timer"
    MINUS = "minus"
    PLUS = "plus"
    AMOUNT = "amount"
    CAPO = "capo"
    SUITS = "suits"
    BET = "bet"
    CONTRA = "contra"
    PASS = "pass"
    RECONTRA = "recontra"
    RECONTRA_TIMER = "timer"
    START_TIMER = "start-timer"


class BetWidget(Widget):
    STATIC_FILES = [
        StyleSheet("bet_widget.css", "bet_widget.css")
    ]

    def __init__(
            self,
            recontra_timeout: float,
            handle_bet: Callable[[InputEvent], None] = None,
            handle_pass: Callable[[InputEvent], None] = None,
            handle_contra: Callable[[InputEvent], None] = None,
            handle_recontra: Callable[[InputEvent], None] = None,
    ) -> None:
        self.handle_bet = handle_bet if handle_bet is not None else lambda e: e
        self.handle_pass = handle_pass if handle_pass is not None else lambda e: e
        self.handle_contra = handle_contra if handle_contra is not None else lambda e: e
        self.handle_recontra = handle_recontra if handle_recontra is not None else lambda e: e

        self._min_bet = MIN_BET
        self._minus = Button("-", _class=CssClass.MINUS, handle_click=self._handle_minus)
        self._plus = Button("+", _class=CssClass.PLUS, handle_click=self._handle_plus)
        self._amount = Span("0", _class=CssClass.AMOUNT)
        self._capo = ToggleButton("Capo", _class=CssClass.CAPO, handle_click=self._handle_capo)
        self._suit = RadioGroup(name="suit", handle_change=self._handle_suit, nodes=[
            Label(RadioButton(value=Suit.SPADES.value), Span(Suit.SPADES.value)),
            Label(RadioButton(value=Suit.HEARTS.value), Span(Suit.HEARTS.value)),
            Label(RadioButton(value=Suit.CLUBS.value), Span(Suit.CLUBS.value)),
            Label(RadioButton(value=Suit.DIAMONDS.value), Span(Suit.DIAMONDS.value)),
            Label(RadioButton(value=Suit.NONE.value), Span(Suit.NONE.value)),
        ])
        self._bet = Button("Bet", _class=CssClass.BET, disabled=True, handle_click=self.handle_bet)
        self._contra = Button("Contra", _class=CssClass.CONTRA, handle_click=self.handle_contra)
        self._pass = Button("Pass", _class=CssClass.PASS, handle_click=self.handle_pass)
        self._recontra = Button("Recontra", _class=CssClass.RECONTRA, handle_click=self.handle_recontra)
        self._recontra_timer = Div(_class=CssClass.RECONTRA_TIMER, style={"animation-duration": f"{recontra_timeout}s"})
        self._container = Div(_class=CssClass.BET_WIDGET, nodes=[
            self._minus,
            self._amount,
            self._plus,
            self._capo,
            Div(self._suit, _class=CssClass.SUITS),
            self._bet,
            self._contra,
            self._pass,
            self._recontra,
            self._recontra_timer,
        ])
        self.nodes = [self._container]

    def show_full(self, min_bet: int, capo_only: bool, can_contra: bool):
        with self.lock:
            self._set_container_class_under_lock(CssClass.FULL)
            self._min_bet = min_bet
            self.capo = capo_only
            self._capo.disabled = capo_only
            self.amount = self.min_bet
            self._contra.disabled = not can_contra
            self.show()

    def show_contra(self):
        with self.lock:
            self._set_container_class_under_lock(CssClass.ONLY_CONTRA)
            self._container.show()

    def show_recontra(self):
        with self.lock:
            self._set_container_class_under_lock(CssClass.ONLY_RECONTRA)
            self._recontra_timer.class_list.add(CssClass.START_TIMER)
            self._container.show()

    def show_timer(self):
        with self.lock:
            self._set_container_class_under_lock(CssClass.ONLY_TIMER)
            self._recontra_timer.class_list.add(CssClass.START_TIMER)
            self._container.show()

    @property
    def amount(self) -> int:
        return int(self._amount.get_text())

    @amount.setter
    def amount(self, amount: int) -> None:
        with self.lock:
            if amount < self.min_bet:
                raise ValueError(f"amount can't be less than min bet ({amount} < {self.min_bet})")
            self._amount.set_text(str(amount))
            self._minus.disabled = amount == self.min_bet

    @property
    def capo(self) -> bool:
        return self._capo.pressed

    @capo.setter
    def capo(self, capo: bool) -> None:
        with self.lock:
            self._capo.pressed = capo
            self._handle_capo(None)  # TODO: hack?

    @property
    def min_bet(self) -> int:
        with self.lock:
            if self.capo:
                return max(self._min_bet, MIN_CAPO_BET)
            return self._min_bet

    @property
    def suit(self) -> Suit:
        suit = self._suit.value
        if suit is None:
            raise RuntimeError("suit not selected")
        return Suit(suit)

    @suit.setter
    def suit(self, value: Suit) -> None:
        self._suit.value = value.value

    def _handle_plus(self, event: InputEvent) -> None:
        with self.lock:
            self.amount += 1

    def _handle_minus(self, event: InputEvent) -> None:
        with self.lock:
            self.amount -= 1

    def _handle_capo(self, event: InputEvent) -> None:
        with self.lock:
            if self.amount < self.min_bet:
                self.amount = self.min_bet
            else:
                # TODO: minus button is disabled in two places
                self._minus.disabled = self.amount == self.min_bet

    def _handle_suit(self, event: InputEvent) -> None:
        self._bet.disabled = False

    def _set_container_class_under_lock(self, _class: str):
        for cl in CssClass.FULL, CssClass.ONLY_CONTRA, CssClass.ONLY_RECONTRA, CssClass.ONLY_TIMER:
            self._container.class_list.remove(cl)
        self._container.class_list.add(_class)
