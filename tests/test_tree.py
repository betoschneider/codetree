import pytest

from codetree.errors import InputError, LimitError
from codetree.services.tree import build_tree

PATHS_INPUT = """notebooks
/config/ambiente
/bronze/notebook 1
/bronze/notebook 2
/silver/notebook 1
/gold/notebook 1"""

PATHS_EXPECTED = """notebooks
├── config
│   └── ambiente
├── bronze
│   ├── notebook 1
│   └── notebook 2
├── silver
│   └── notebook 1
└── gold
    └── notebook 1"""

INDENT_INPUT = """notebooks
 config
  ambiente
 bronze
  notebook 1
  notebook 2
 silver
  notebook 1"""

INDENT_EXPECTED = """notebooks
├── config
│   └── ambiente
├── bronze
│   ├── notebook 1
│   └── notebook 2
└── silver
    └── notebook 1"""


def test_modo_caminhos():
    assert build_tree(PATHS_INPUT, "paths") == PATHS_EXPECTED


def test_modo_indentacao_um_espaco():
    assert build_tree(INDENT_INPUT, "indentation") == INDENT_EXPECTED


def test_auto_detecta_caminhos():
    assert build_tree(PATHS_INPUT, "auto") == PATHS_EXPECTED


def test_auto_detecta_indentacao():
    assert build_tree(INDENT_INPUT, "auto") == INDENT_EXPECTED


def test_mescla_duplicados_e_cria_intermediarios():
    text = "raiz\n/a/b\n/a/b\n/a/c"
    assert build_tree(text, "paths") == "raiz\n└── a\n    ├── b\n    └── c"


def test_preserva_ordem_de_insercao():
    text = "raiz\n/z\n/a\n/m"
    assert build_tree(text, "paths") == "raiz\n├── z\n├── a\n└── m"


@pytest.mark.parametrize("espacos", [1, 2, 3, 4])
def test_qualquer_largura_de_recuo(espacos: int):
    pad = " " * espacos
    text = f"raiz\n{pad}a\n{pad * 2}b"
    assert build_tree(text, "indentation") == "raiz\n└── a\n    └── b"


def test_tabs_expandidos():
    assert build_tree("raiz\n\to", "indentation") == "raiz\n└── o"


def test_arvore_de_um_no():
    assert build_tree("notebooks", "auto") == "notebooks"


def test_normaliza_crlf():
    assert build_tree("raiz\r\n/a", "auto") == "raiz\n└── a"


def test_preserva_acentos_e_emoji_no_nome():
    assert build_tree("raiz\n/ação 🚀", "paths") == "raiz\n└── ação 🚀"


def test_espacos_nas_pontas_dos_segmentos():
    assert build_tree("raiz\n/a / b", "paths") == "raiz\n└── a\n    └── b"


def test_entrada_vazia():
    with pytest.raises(InputError):
        _ = build_tree("   \n\n  ", "auto")


def test_modo_invalido():
    with pytest.raises(InputError):
        _ = build_tree("raiz", "xyz")


def test_limite_de_profundidade():
    lines = ["raiz"] + [" " * i + f"nivel{i}" for i in range(1, 60)]
    with pytest.raises(LimitError):
        _ = build_tree("\n".join(lines), "indentation")
