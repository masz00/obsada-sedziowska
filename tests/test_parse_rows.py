"""Tests for _parse_rows."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from scan import _parse_rows
from conftest import make_xls


SAME_MATCH = make_xls([
    ("Klasa A", "Sparta", "Legia", "2025-04-10", "15:00", "Kowalski", "Nowak", "Wiśniewski"),
])

E_MATCH = make_xls([
    ("I liga E1 Grupa 2", "Start", "Legia", "2025-04-10", "10:00", "Kowalski", "", ""),
])


# --- multi-name collision fix ---

def test_both_names_found_in_same_row():
    matches = _parse_rows(SAME_MATCH, ["Kowalski", "Nowak"])
    names = [m["name"] for m in matches]
    assert "Kowalski" in names
    assert "Nowak" in names

def test_roles_correct_for_same_row():
    matches = _parse_rows(SAME_MATCH, ["Kowalski", "Nowak"])
    by_name = {m["name"]: m for m in matches}
    assert by_name["Kowalski"]["role"] == "sg"
    assert by_name["Nowak"]["role"] == "a"

def test_fees_correct_for_same_row():
    matches = _parse_rows(SAME_MATCH, ["Kowalski", "Nowak"])
    by_name = {m["name"]: m for m in matches}
    assert by_name["Kowalski"]["fee"] is not None
    assert by_name["Nowak"]["fee"] is not None
    assert by_name["Kowalski"]["fee"] > by_name["Nowak"]["fee"]

def test_single_name_still_works():
    matches = _parse_rows(SAME_MATCH, ["Kowalski"])
    assert len(matches) == 1
    assert matches[0]["role"] == "sg"

def test_name_not_in_row_not_returned():
    matches = _parse_rows(SAME_MATCH, ["Zielinski"])
    assert matches == []


# --- E-league filter ---

def test_e_league_matches_excluded():
    matches = _parse_rows(E_MATCH, ["Kowalski"])
    assert matches == []

def test_non_e_league_not_filtered():
    matches = _parse_rows(SAME_MATCH, ["Kowalski"])
    assert len(matches) == 1
