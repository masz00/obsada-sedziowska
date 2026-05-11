"""Tests for co-referee discovery in parse_xls_for_subscriber."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from scan import parse_xls_for_subscriber
from conftest import make_xls


# XLS: Kowalski sędziuje z Nowak i Wiśniewski w meczu A
# Nowak ma też własny mecz w lidze B (z innym SG)
XLS_BASIC = make_xls([
    ("Klasa A Grupa 1", "Sparta", "Legia",  "2025-04-10", "15:00", "Kowalski", "Nowak",      "Wiśniewski"),
    ("Klasa B Grupa 2", "Motor",  "Ruch",   "2025-04-11", "12:00", "Duda",     "Nowak",      ""),
    ("Klasa A Grupa 2", "Lech",   "Polonia","2025-04-12", "16:00", "Zając",    "Wiśniewski", ""),
])

# XLS: Kowalski sędziuje z Wróbel który jest już w friends
XLS_FRIEND_AS_CO = make_xls([
    ("Klasa A Grupa 1", "Sparta", "Legia", "2025-04-10", "15:00", "Kowalski", "Wróbel", ""),
    ("Klasa B Grupa 1", "Motor",  "Ruch",  "2025-04-11", "10:00", "Wróbel",   "",       ""),
])

# XLS: Kowalski jedzie sam (solo B, brak asystentów)
XLS_SOLO = make_xls([
    ("Klasa B Grupa 3", "Start", "Legia", "2025-04-10", "15:00", "Kowalski", "", ""),
])

# XLS: Kowalski z Nowak w DWÓCH meczach — Nowak powinien mieć oba swoje mecze
XLS_CO_IN_MULTIPLE = make_xls([
    ("Klasa A Grupa 1", "Sparta", "Legia", "2025-04-10", "15:00", "Kowalski", "Nowak", ""),
    ("Klasa A Grupa 2", "Motor",  "Ruch",  "2025-04-11", "12:00", "Kowalski", "Nowak", ""),
    ("Klasa B Grupa 1", "Lech",   "Wisła", "2025-04-12", "10:00", "Nowak",    "",      ""),
])


# --- podstawowy co-ref ---

def test_co_ref_other_matches_included():
    matches = parse_xls_for_subscriber(XLS_BASIC, "Kowalski", [], include_co_refs=True)
    names = [m["name"] for m in matches]
    assert "Nowak" in names

def test_co_ref_flagged_as_is_co_ref():
    matches = parse_xls_for_subscriber(XLS_BASIC, "Kowalski", [], include_co_refs=True)
    co = [m for m in matches if m["name"] == "Nowak"]
    assert all(m["is_co_ref"] for m in co)

def test_primary_matches_not_flagged_as_co_ref():
    matches = parse_xls_for_subscriber(XLS_BASIC, "Kowalski", [], include_co_refs=True)
    my = [m for m in matches if m["name"] == "Kowalski"]
    assert all(not m["is_co_ref"] for m in my)

def test_co_ref_only_their_own_matches_not_shared():
    # Nowak's mecz B (without Kowalski) should appear; shared mecz A should NOT be in co_ref section
    matches = parse_xls_for_subscriber(XLS_BASIC, "Kowalski", [], include_co_refs=True)
    co_nowak = [m for m in matches if m["name"] == "Nowak" and m["is_co_ref"]]
    homes = [m["home"] for m in co_nowak]
    assert "Motor" in homes       # Nowak's own match
    assert "Sparta" not in homes  # shared match with Kowalski — not duplicated


# --- friend nie jest dodawany jako co-ref ---

def test_friend_not_added_as_co_ref():
    matches = parse_xls_for_subscriber(XLS_FRIEND_AS_CO, "Kowalski", ["Wróbel"], include_co_refs=True)
    co = [m for m in matches if m.get("is_co_ref")]
    assert co == []

def test_friend_matches_still_present():
    matches = parse_xls_for_subscriber(XLS_FRIEND_AS_CO, "Kowalski", ["Wróbel"], include_co_refs=True)
    names = [m["name"] for m in matches]
    assert "Wróbel" in names


# --- include_co_refs=False ---

def test_no_co_refs_when_disabled():
    matches = parse_xls_for_subscriber(XLS_BASIC, "Kowalski", [], include_co_refs=False)
    assert all(not m.get("is_co_ref") for m in matches)
    names = [m["name"] for m in matches]
    assert "Nowak" not in names


# --- brak moich meczów → brak co-refs ---

def test_no_co_refs_when_me_has_no_matches():
    matches = parse_xls_for_subscriber(XLS_BASIC, "Zielinski", [], include_co_refs=True)
    assert matches == []


# --- solo mecz (brak asystentów) nie generuje co-refs ---

def test_solo_match_no_co_refs():
    matches = parse_xls_for_subscriber(XLS_SOLO, "Kowalski", [], include_co_refs=True)
    co = [m for m in matches if m.get("is_co_ref")]
    assert co == []


# --- co-ref w wielu moich meczach — jego własne mecze bez duplikatów ---

def test_co_ref_in_multiple_my_matches_no_duplicate_their_matches():
    matches = parse_xls_for_subscriber(XLS_CO_IN_MULTIPLE, "Kowalski", [], include_co_refs=True)
    co_nowak = [m for m in matches if m["name"] == "Nowak" and m["is_co_ref"]]
    homes = [m["home"] for m in co_nowak]
    assert homes.count("Lech") == 1  # Nowak's own match appears exactly once


# --- kolejność: moje mecze przed co-refs ---

def test_my_matches_before_co_ref_matches():
    matches = parse_xls_for_subscriber(XLS_BASIC, "Kowalski", [], include_co_refs=True)
    idxs = [m["name_idx"] for m in matches]
    my_max = max(m["name_idx"] for m in matches if not m.get("is_co_ref"))
    co_min = min(m["name_idx"] for m in matches if m.get("is_co_ref"))
    assert my_max < co_min
