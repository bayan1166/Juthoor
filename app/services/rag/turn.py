from dataclasses import dataclass, field


@dataclass
class SocraticTurn:
    reply: str
    gap_detected: bool
    gap_skill: str
    misconception: str
    retrieved_ids: list[str] = field(default_factory=list)
