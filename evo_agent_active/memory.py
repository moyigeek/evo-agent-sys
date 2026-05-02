import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConversationMemory:
    turns: list = field(default_factory=list)
    long_term_facts: list = field(default_factory=list)
    current_task: str | None = None
    version: float = 1.0
    created_at: float = field(default_factory=time.time)

    def add_turn(self, role: str, content: str):
        self.turns.append(ConversationTurn(role=role, content=content))

    def add_fact(self, fact: str):
        if fact not in self.long_term_facts:
            self.long_term_facts.append(fact)

    def set_task(self, task: str):
        self.current_task = task

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["turns"] = [asdict(t) for t in self.turns]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationMemory":
        memory = cls(
            long_term_facts=data.get("long_term_facts", []),
            current_task=data.get("current_task"),
            version=data.get("version", 1.0),
            created_at=data.get("created_at", time.time()),
        )
        for turn_data in data.get("turns", []):
            memory.turns.append(ConversationTurn(
                role=turn_data["role"],
                content=turn_data["content"],
                timestamp=turn_data.get("timestamp", time.time()),
            ))
        return memory


STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".evo_state.json")
RECOVERY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".evo_recovery_message.json")


def save_state(memory: ConversationMemory, extra: dict[str, Any] | None = None):
    state = {
        "memory": memory.to_dict(),
        "extra": extra or {},
        "saved_at": time.time(),
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state() -> tuple[ConversationMemory, dict[str, Any]]:
    if not os.path.exists(STATE_FILE):
        return ConversationMemory(), {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    memory = ConversationMemory.from_dict(state.get("memory", {}))
    extra = state.get("extra", {})
    return memory, extra


def load_recovery_message() -> str | None:
    if not os.path.exists(RECOVERY_FILE):
        return None
    with open(RECOVERY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("message")
