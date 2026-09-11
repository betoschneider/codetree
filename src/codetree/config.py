"""Configuração e limites carregados do ambiente.

Limites de entrada (§6.4) e de disponibilidade (§6.5) do plano. Todos podem
ser sobrescritos por variáveis de ambiente ``CODETREE_*``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    """Parâmetros de proteção da API."""

    max_body_bytes: int = 64 * 1024
    request_timeout_seconds: float = 2.0
    rate_limit: int = 120
    rate_burst: int = 20
    rate_window_seconds: float = 60.0


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def load_limits() -> Limits:
    """Monta os limites a partir do ambiente (com defaults seguros)."""
    return Limits(
        max_body_bytes=_int("CODETREE_MAX_BODY_BYTES", 64 * 1024),
        request_timeout_seconds=_float("CODETREE_REQUEST_TIMEOUT", 2.0),
        rate_limit=_int("CODETREE_RATE_LIMIT", 120),
        rate_burst=_int("CODETREE_RATE_BURST", 20),
        rate_window_seconds=_float("CODETREE_RATE_WINDOW", 60.0),
    )


def current_environment() -> str:
    """Ambiente atual: ``production`` desabilita docs e afins."""
    return os.environ.get("CODETREE_ENV", "development").strip().lower()
