import pytest
from scan import shorten_klasa


# --- prefix stripping ---

def test_strips_federation_prefix():
    assert shorten_klasa("Kujawsko-Pomorski ZPN: Klasa A Grupa 3") == "A Gr.3"

def test_strips_dash_prefix():
    assert shorten_klasa("KPZPN - Klasa A Grupa 1") == "A Gr.1"

def test_strips_rw_suffix():
    assert shorten_klasa("Klasa A Grupa 2 (RW)") == "A Gr.2"

def test_strips_both_prefix_and_rw():
    assert shorten_klasa("KPZPN - Klasa B Grupa 4 (RW)") == "B Gr.4"


# --- klasa okręgowa ---

def test_klasa_okregowa_with_group():
    assert shorten_klasa("Klasa Okręgowa Grupa 1") == "KO Gr.1"

def test_klasa_okregowa_without_group():
    assert shorten_klasa("Klasa Okręgowa") == "KO"

def test_klasa_okregowa_prefix():
    assert shorten_klasa("KPZPN - Klasa Okręgowa Grupa 2") == "KO Gr.2"


# --- klasa A ---

def test_klasa_a_with_group():
    assert shorten_klasa("Klasa A Grupa 5") == "A Gr.5"

def test_klasa_a_without_group():
    assert shorten_klasa("Klasa A") == "A"


# --- klasa B ---

def test_klasa_b_with_group():
    assert shorten_klasa("Klasa B Grupa 3") == "B Gr.3"

def test_klasa_b_without_group():
    assert shorten_klasa("Klasa B") == "B"


# --- IV liga ---

def test_iv_liga():
    assert shorten_klasa("IV liga") == "IV"

def test_iv_liga_case_insensitive():
    assert shorten_klasa("IV Liga") == "IV"


# --- ligi kobiet ---

def test_trzecia_liga_kobiet():
    assert shorten_klasa("Trzecia Liga Kobiet") == "III K"

def test_czwarta_liga_kobiet():
    assert shorten_klasa("Czwarta Liga Kobiet") == "IV K"


# --- ligi akademickie / młodzieżowe (liga + kategoria) ---

def test_liga_with_category_and_group():
    assert shorten_klasa("I liga E1 Grupa 2") == "I E1 Gr.2"

def test_liga_with_category_no_group():
    assert shorten_klasa("II liga A1") == "II A1"

def test_iii_liga_with_category():
    assert shorten_klasa("III liga B2 Grupa 1") == "III B2 Gr.1"


# --- standalone category (no liga prefix) ---

def test_standalone_category_with_group():
    assert shorten_klasa("A1 Grupa 3") == "A1 Gr.3"

def test_standalone_category_no_group():
    assert shorten_klasa("B2") == "B2"


# --- passthrough ---

def test_unknown_format_returned_as_is():
    assert shorten_klasa("Nieznana Liga Specjalna") == "Nieznana Liga Specjalna"

def test_whitespace_stripped():
    assert shorten_klasa("  Klasa A Grupa 1  ") == "A Gr.1"
