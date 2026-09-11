"""Gerador de linha do tempo com caracteres Unicode.

Função pura ``build_timeline(text) -> str``; não depende de FastAPI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..errors import InputError, LimitError
from ..sanitize import clean_text

MAX_LINES = 2_000
MAX_EVENTS = 500
MAX_ITEMS = 200

# Data no início da linha, com "|" separador opcional antes do título.
_DATE_RE = re.compile(r"^\s*(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s*(?:\|\s*)?(.*)$")


@dataclass
class _Event:
    date: str
    title: str
    items: list[str] = field(default_factory=list)


def _parse(lines: list[str]) -> list[_Event]:
    events: list[_Event] = []
    for line in lines:
        match = _DATE_RE.match(line)
        if match:
            if len(events) >= MAX_EVENTS:
                raise LimitError("Entrada excede os limites permitidos.")
            events.append(_Event(match.group(1), match.group(2).strip()))
            continue

        stripped = line.strip()
        if stripped.startswith("-"):
            if not events:
                raise InputError("Subitem sem evento associado.")
            if len(events[-1].items) >= MAX_ITEMS:
                raise LimitError("Entrada excede os limites permitidos.")
            events[-1].items.append(stripped[1:].strip())
            continue
        # Linhas que não são evento nem subitem são ignoradas.
    return events


def _render(events: list[_Event]) -> str:
    width = max(len(event.date) for event in events)
    # "○ " (2) + data (width) + " ───── " (7) → título inicia na coluna width+9.
    title_col = width + 9
    last_index = len(events) - 1

    out: list[str] = []
    for index, event in enumerate(events):
        marker = "●" if index == last_index else "○"
        out.append(f"{marker} {event.date.ljust(width)} ───── {event.title}".rstrip())

        if event.items:
            guide = " " if index == last_index else "│"
            pad = guide + " " * (title_col - 1)
            last_item = len(event.items) - 1
            for item_index, item in enumerate(event.items):
                connector = "└── " if item_index == last_item else "├── "
                out.append(pad + connector + item)

        if index != last_index:
            out.append("│")
    return "\n".join(out)


def build_timeline(text: str) -> str:
    """Gera a linha do tempo a partir de ``text``."""
    lines = [line for line in clean_text(text).split("\n") if line.strip()]
    if len(lines) > MAX_LINES:
        raise LimitError("Entrada excede os limites permitidos.")

    events = _parse(lines)
    if not events:
        raise InputError("Nenhum evento encontrado.")
    return _render(events)
