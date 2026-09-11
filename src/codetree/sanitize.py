"""Limpeza de caracteres de controle e bidi antes do parsing.

A entrada do usuário nunca é usada para compor caminhos, comandos ou
consultas; ainda assim, removemos caracteres invisíveis que permitem
*spoofing* visual ou escondem conteúdo.
"""

from __future__ import annotations

import unicodedata

# Controles bidi e zero-width que permitem spoofing visual.
_INVISIBLE = frozenset(
    [
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\u2060",  # word joiner
        "\ufeff",  # BOM / zero width no-break space
        "\u202a",  # left-to-right embedding
        "\u202b",  # right-to-left embedding
        "\u202c",  # pop directional formatting
        "\u202d",  # left-to-right override
        "\u202e",  # right-to-left override
        "\u2066",  # left-to-right isolate
        "\u2067",  # right-to-left isolate
        "\u2068",  # first strong isolate
        "\u2069",  # pop directional isolate
    ]
)

_PRESERVED = frozenset(["\n", "\t"])


def clean_text(text: str) -> str:
    """Normaliza quebras de linha e remove caracteres perigosos.

    - Converte ``\\r\\n`` e ``\\r`` isolado em ``\\n``.
    - Remove controles C0/C1 (categoria ``Cc``), exceto ``\\n`` e ``\\t``.
    - Remove controles bidi, zero-width e demais caracteres de formatação
      (categoria ``Cf``), inclusive os de ``_INVISIBLE``.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(
        ch
        for ch in text
        if ch in _PRESERVED
        or (ch not in _INVISIBLE and unicodedata.category(ch) not in ("Cc", "Cf"))
    )
