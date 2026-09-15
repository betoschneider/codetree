"""Gerador de estrutura de pastas (tree) com caracteres Unicode.

Função pura ``build_tree(text, mode) -> str``; não depende de FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..errors import InputError, LimitError
from ..sanitize import clean_text

MAX_LINES = 2_000
MAX_NODES = 2_000
MAX_DEPTH = 50

VALID_MODES = frozenset(["auto", "paths", "indentation"])


@dataclass
class _Node:
    """Nó da árvore, preservando a ordem de inserção dos filhos."""

    name: str
    children: list[_Node] = field(default_factory=list)
    by_name: dict[str, _Node] = field(default_factory=dict)


def _content_lines(text: str) -> list[str]:
    """Retorna as linhas não vazias, na ordem original."""
    return [line for line in text.split("\n") if line.strip()]


def _detect_mode(lines: list[str]) -> str:
    """Modo *paths* se houver alguma linha que comece com ``/``."""
    return "paths" if any(line.lstrip().startswith("/") for line in lines) else "indentation"


def _new_child(parent: _Node, name: str) -> _Node:
    """Cria (ou reaproveita) um filho, mesclando duplicados."""
    child = parent.by_name.get(name)
    if child is None:
        child = _Node(name)
        parent.by_name[name] = child
        parent.children.append(child)
    return child


def _split_path(line: str) -> list[str]:
    """Divide uma linha em segmentos de caminho, descartando vazios."""
    return [seg.strip() for seg in line.strip().lstrip("/").split("/") if seg.strip()]


def _build_from_paths(lines: list[str]) -> _Node:
    head = _split_path(lines[0])
    if not head:
        raise InputError("Entrada vazia.")
    root = _Node(head[0])
    node = root
    for segment in head[1:]:
        node = _new_child(node, segment)
    for line in lines[1:]:
        node = root
        for segment in _split_path(line):
            node = _new_child(node, segment)
    return root


def _build_from_indentation(lines: list[str]) -> _Node:
    root = _Node(lines[0].strip())
    # Cada item é (largura da indentação, nó). A raiz começa com -1 para que
    # linhas de indentação 0 sejam filhas dela.
    stack: list[tuple[int, _Node]] = [(-1, root)]
    for line in lines[1:]:
        stripped = line.lstrip(" \t")
        name = stripped.rstrip()
        if not name:
            continue
        raw_indent = line[: len(line) - len(stripped)]
        width = sum(4 if ch == "\t" else 1 for ch in raw_indent)

        while stack[-1][0] >= width:
            del stack[-1]
        parent = stack[-1][1]
        child = _Node(name)
        parent.children.append(child)
        stack.append((width, child))
    return root


def _validate_limits(root: _Node) -> None:
    count = 0
    max_depth = 0
    stack: list[tuple[_Node, int]] = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        count += 1
        max_depth = max(max_depth, depth)
        stack.extend((child, depth + 1) for child in node.children)
    if count > MAX_NODES or max_depth > MAX_DEPTH:
        raise LimitError("Entrada excede os limites permitidos.")


def _render(root: _Node) -> str:
    lines = [root.name]
    # Cada item: (nó, prefixo da linha, conector, prefixo dos filhos).
    pending: list[tuple[_Node, str, str, str]] = []

    def schedule(node: _Node, prefix: str) -> None:
        total = len(node.children)
        items: list[tuple[_Node, str, str, str]] = []
        for index, child in enumerate(node.children):
            is_last = index == total - 1
            items.append(
                (
                    child,
                    prefix,
                    "└── " if is_last else "├── ",
                    prefix + ("    " if is_last else "│   "),
                )
            )
        pending.extend(reversed(items))

    schedule(root, "")
    while pending:
        node, prefix, connector, child_prefix = pending.pop()
        lines.append(prefix + connector + node.name)
        schedule(node, child_prefix)
    return "\n".join(lines)


def build_tree(text: str, mode: str = "auto") -> str:
    """Gera a estrutura de pastas a partir de ``text``.

    ``mode`` aceita ``"auto"``, ``"paths"`` ou ``"indentation"``.
    """
    if mode not in VALID_MODES:
        raise InputError(f"Modo inválido: {mode!r}.")

    lines = _content_lines(clean_text(text))
    if not lines:
        raise InputError("Entrada vazia.")
    if len(lines) > MAX_LINES:
        raise LimitError("Entrada excede os limites permitidos.")

    resolved = _detect_mode(lines) if mode == "auto" else mode
    root = _build_from_paths(lines) if resolved == "paths" else _build_from_indentation(lines)
    _validate_limits(root)
    return _render(root)
