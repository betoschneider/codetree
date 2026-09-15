import pytest

from treegen.errors import InputError, LimitError
from treegen.services.timeline import build_timeline

TIMELINE_INPUT = """13/08 | Alteração da origem do atributo

02/09 | Adequação do ALTER TABLE
  - Truncate
  - Recarga da tabela

04/09 | Reinício da Identity
  - Truncate
  - Reset da Identity"""

TIMELINE_EXPECTED = "\n".join(
    [
        "○ 13/08 ───── Alteração da origem do atributo",
        "│",
        "○ 02/09 ───── Adequação do ALTER TABLE",
        "│" + " " * 13 + "├── Truncate",
        "│" + " " * 13 + "└── Recarga da tabela",
        "│",
        "● 04/09 ───── Reinício da Identity",
        " " * 14 + "├── Truncate",
        " " * 14 + "└── Reset da Identity",
    ]
)


def test_coluna_do_titulo_deriva_da_linha_do_evento():
    linha = build_timeline("13/08 | X").splitlines()[0]
    assert linha == "● 13/08 ───── X"
    assert linha.index("X") == 14


def test_exemplo_canonico():
    assert build_timeline(TIMELINE_INPUT) == TIMELINE_EXPECTED


def test_alinhamento_dos_subitens():
    linhas = build_timeline(TIMELINE_INPUT).splitlines()
    primeiro_sub = linhas[3]
    ultimo_sub = linhas[7]
    # W = 5 → o título começa na coluna 14 e os subitens alinham nela.
    assert primeiro_sub.index("├") == 14
    assert ultimo_sub.index("├") == 14
    assert primeiro_sub[0] == "│"
    assert ultimo_sub[0] == " "


def test_evento_unico_recebe_marcador_cheio():
    assert build_timeline("13/08 | Evento") == "● 13/08 ───── Evento"


def test_pipe_sem_espacos():
    assert build_timeline("13/08|Evento") == "● 13/08 ───── Evento"


def test_data_curta_alinhada_a_mais_longa():
    linhas = build_timeline("1/9 | Curto\n13/08 | Longo").splitlines()
    assert linhas[0] == "○ 1/9   ───── Curto"
    assert linhas[2] == "● 13/08 ───── Longo"
    assert linhas[0].index("Curto") == linhas[2].index("Longo") == 14


def test_separador_entre_eventos():
    linhas = build_timeline("13/08 | A\n14/08 | B").splitlines()
    assert linhas == ["○ 13/08 ───── A", "│", "● 14/08 ───── B"]


def test_ultimo_evento_nao_insere_separador():
    linhas = build_timeline("13/08 | A").splitlines()
    assert linhas[-1] == "● 13/08 ───── A"


def test_ignora_linhas_desconhecidas():
    linhas = build_timeline("texto solto\n13/08 | A").splitlines()
    assert linhas == ["● 13/08 ───── A"]


def test_subitem_sem_evento():
    with pytest.raises(InputError):
        _ = build_timeline("- solto")


def test_sem_eventos():
    with pytest.raises(InputError):
        _ = build_timeline("linha qualquer\noutra linha")


def test_normaliza_crlf():
    linhas = build_timeline("13/08 | A\r\n- item").splitlines()
    assert linhas[0] == "● 13/08 ───── A"
    assert linhas[1].index("└") == 14
    assert linhas[1].endswith("└── item")


def test_limite_de_eventos():
    text = "\n".join(f"{i % 30 + 1:02d}/01 | evento {i}" for i in range(501))
    with pytest.raises(LimitError):
        _ = build_timeline(text)
