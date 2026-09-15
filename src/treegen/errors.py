"""Erros compartilhados pelos serviços de geração.

A camada de API (Fase 2) mapeia ``InputError`` para HTTP 400 e
``LimitError`` para HTTP 422.
"""

from __future__ import annotations


class InputError(ValueError):
    """Entrada inválida do ponto de vista de conteúdo (HTTP 400)."""


class LimitError(ValueError):
    """Entrada acima dos limites permitidos (HTTP 422)."""
