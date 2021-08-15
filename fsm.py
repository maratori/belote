from collections import defaultdict
from typing import TypeVar, Generic, Union, Callable

State = TypeVar("State")
Event = TypeVar("Event")
EventData = TypeVar("EventData")
Memory = TypeVar("Memory")


class Transition(Generic[State, Memory, Event, EventData]):
    def __init__(self,
                 event: Event,
                 from_: State,
                 to: State,
                 condition: Union[Callable[[State, Memory, Event, EventData], bool],
                                  list[Callable[[State, Memory, Event, EventData], bool]]] = None,
                 callback: Union[Callable[[State, State, Memory, Event, EventData], None],
                                 list[Callable[[State, State, Memory, Event, EventData], None]]] = None):
        self.event = event
        self.from_ = from_
        self.to = to
        self.condition = condition
        self.callback = callback

    def applicable(self, state: State, memory: Memory, event: Event, data: EventData) -> bool:
        if state != self.from_:
            return False
        elif self.condition is None or not self.condition:
            return True
        elif not self.condition:
            return True
        elif isinstance(self.condition, list):
            for c in self.condition:
                if not c(state, memory, event, data):
                    return False
            return True
        else:
            return self.condition(state, memory, event, data)

    def apply(self, state: State, memory: Memory, event: Event, data: EventData) -> State:
        if isinstance(self.callback, list):
            for c in self.callback:
                c(state, self.to, memory, event, data)
        elif self.callback is not None:
            self.callback(state, self.to, memory, event, data)

        return self.to


class FSM(Generic[State, Memory, Event, EventData]):
    def __init__(self,
                 initial_state: State,
                 initial_memory: Memory,
                 transitions: list[Transition[State, Memory, Event, EventData]]):
        self.current_state = initial_state
        self.memory = initial_memory
        self.transitions: dict[State, dict[Event, list[Transition[State, Memory, Event, EventData]]]] = \
            defaultdict(lambda: defaultdict(list))
        for t in transitions:
            self.transitions[t.from_][t.event].append(t)

    def can_handle_event(self, event: Event, data: EventData) -> bool:
        if self.current_state not in self.transitions:
            return False
        if event not in self.transitions[self.current_state]:
            return False
        for t in self.transitions[self.current_state][event]:
            if t.applicable(self.current_state, self.memory, event, data):
                return True

    def handle_event(self, event: Event, data: EventData) -> bool:
        if self.current_state not in self.transitions:
            raise RuntimeError("terminal")
        if event not in self.transitions[self.current_state]:
            raise ValueError("event is not possible from current state")
        for t in self.transitions[self.current_state][event]:
            if t.applicable(self.current_state, self.memory, event, data):
                self.current_state = t.apply(self.current_state, self.memory, event, data)
                return self.current_state in self.transitions
        raise ValueError("applicable transition not found")
