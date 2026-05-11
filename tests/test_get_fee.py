import pytest
from scan import get_fee


# --- IV liga ---
def test_iv_sg():   assert get_fee("IV", "sg")  == 316
def test_iv_a():    assert get_fee("IV", "a")   == 258

# --- Klasa Okręgowa ---
def test_ko_sg():       assert get_fee("KO", "sg")       == 258
def test_ko_gr_sg():    assert get_fee("KO Gr.1", "sg")  == 258
def test_ko_a():        assert get_fee("KO Gr.3", "a")   == 217

# --- Klasa A ---
def test_a_sg():        assert get_fee("A", "sg")        == 199
def test_a_gr_sg():     assert get_fee("A Gr.2", "sg")   == 199
def test_a_a():         assert get_fee("A Gr.5", "a")    == 167

# --- Klasa B ---
def test_b_sg():        assert get_fee("B", "sg")        == 176
def test_b_a():         assert get_fee("B Gr.1", "a")    == 145
def test_b_one():       assert get_fee("B", "one")       == 226
def test_b_gr_one():    assert get_fee("B Gr.3", "one")  == 226

# --- ligi kobiet ---
def test_iii_k_sg():    assert get_fee("III K", "sg")    == 131
def test_iii_k_a():     assert get_fee("III K", "a")     == 90
def test_iv_k_sg():     assert get_fee("IV K", "sg")     == 127
def test_iv_k_a():      assert get_fee("IV K", "a")      == 108

# --- kategorie A ---
def test_i_a_sg():      assert get_fee("I A1", "sg")     == 199
def test_ii_a_sg():     assert get_fee("II A2", "sg")    == 199
def test_iii_a_sg():    assert get_fee("III A1", "sg")   == 140
def test_iv_a_sg():     assert get_fee("IV A2", "sg")    == 127

# --- kategorie B ---
def test_i_b_sg():      assert get_fee("I B1", "sg")     == 181
def test_i_b_a():       assert get_fee("I B1", "a")      == 163
def test_ii_b_sg():     assert get_fee("II B2", "sg")    == 127
def test_iii_b_sg():    assert get_fee("III B1", "sg")   == 127
def test_iv_b_sg():     assert get_fee("IV B2", "sg")    == 127

# --- kategorie C/D ---
def test_i_c_sg():      assert get_fee("I C1", "sg")     == 113
def test_i_d_a():       assert get_fee("I D2", "a")      == 95
def test_ii_c_sg():     assert get_fee("II C1", "sg")    == 104
def test_iii_d_a():     assert get_fee("III D1", "a")    == 68

# --- brak dopasowania ---
def test_unknown_class_returns_none():
    assert get_fee("Nieznana", "sg") is None

def test_unknown_role_returns_none():
    assert get_fee("IV", "unknown") is None

def test_b_role_one_only_for_b():
    assert get_fee("KO", "one") is None
