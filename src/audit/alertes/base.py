from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Severite(str, Enum):
    ROUGE = "ROUGE"
    JAUNE = "JAUNE"
    VERT = "VERT"


@dataclass
class Alerte:
    code: str
    famille: str
    severite: Severite
    titre: str
    description: str
    gain_eur_annuel: float | None
    gain_eur_horizon: float | None
    action_concrete: str
    sources: list[str]
    ligne_concernee: str | None = None


_REGISTRY: list[tuple[str, str, Callable]] = []


def regle(code: str, famille: str):
    def decorator(fn: Callable) -> Callable:
        _REGISTRY.append((code, famille, fn))
        return fn

    return decorator
