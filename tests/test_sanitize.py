from codetree.sanitize import clean_text


def test_normaliza_quebras_windows_e_mac():
    assert clean_text("a\r\nb\rc") == "a\nb\nc"


def test_remove_controles_bidi_e_zero_width():
    assert clean_text("a\u202eb\u200dc\ufeffe") == "abce"


def test_remove_controles_c0_preservando_newline_e_tab():
    assert clean_text("a\x00b\x07\tc\nd") == "ab\tc\nd"


def test_preserva_acentos_e_emoji():
    assert clean_text("ação 🚀") == "ação 🚀"


def test_texto_limpo_permanece_igual():
    texto = "notebooks\n  bronze\n    notebook 1"
    assert clean_text(texto) == texto
