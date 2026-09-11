"""Schemas de entrada e saída da API (Pydantic)."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

# Limite de tamanho do campo de texto (§6.4).
MAX_TEXT_CHARS = 50_000


class TreeMode(str, Enum):
    """Modo de interpretação da entrada da árvore."""

    auto = "auto"
    paths = "paths"
    indentation = "indentation"


class TreeRequest(BaseModel):
    """Corpo de ``POST /api/tree``."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_TEXT_CHARS)
    mode: TreeMode = TreeMode.auto


class TimelineRequest(BaseModel):
    """Corpo de ``POST /api/timeline``."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_TEXT_CHARS)


class ResultResponse(BaseModel):
    """Resposta padrão de geração."""

    result: str
