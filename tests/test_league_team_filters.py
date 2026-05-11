"""Tests for _find_by_league and _find_by_team."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from scan import _find_by_league, _find_by_team
from conftest import make_xls


XLS = make_xls([
    ("IV liga", "Sparta", "Legia", "2025-04-10", "15:00", "Kowalski", "Nowak", ""),
    ("KPZPN - Klasa A Grupa 1", "Unia Janikowo", "Lech", "2025-04-11", "12:00", "Wiśniewski", "", ""),
    ("KPZPN - Klasa B Grupa 3", "Motor", "Unia Janikowo", "2025-04-12", "14:00", "Duda", "", ""),
    ("KPZPN - Klasa A Grupa 2", "Ruch", "Wisła", "2025-04-13", "16:00", "Zając", "", ""),
    ("I liga E1 Grupa 2", "Unia Janikowo", "Start", "2025-04-14", "10:00", "Nowak", "", ""),
])


# --- _find_by_league ---

def test_league_exact_match():
    matches = _find_by_league(XLS, ["IV"])
    assert len(matches) == 1
    assert matches[0]["home"] == "Sparta"


def test_league_no_match():
    matches = _find_by_league(XLS, ["KO Gr.1"])
    assert matches == []


def test_league_empty_list():
    assert _find_by_league(XLS, []) == []


def test_league_multiple():
    matches = _find_by_league(XLS, ["IV", "A Gr.1"])
    groups = [m["group"] for m in matches]
    assert "IV" in groups
    assert "A Gr.1" in groups


def test_league_match_has_referees():
    matches = _find_by_league(XLS, ["IV"])
    assert matches[0]["sg"] == "Kowalski"


# --- _find_by_team ---

def test_team_home_match():
    matches = _find_by_team(XLS, ["Unia Janikowo"])
    assert any(m["home"] == "Unia Janikowo" for m in matches)


def test_team_away_match():
    matches = _find_by_team(XLS, ["Unia Janikowo"])
    assert any(m["away"] == "Unia Janikowo" for m in matches)


def test_team_both_home_and_away_returned():
    matches = _find_by_team(XLS, ["Unia Janikowo"])
    assert len(matches) == 2


def test_team_partial_name_match():
    matches = _find_by_team(XLS, ["Unia"])
    assert len(matches) == 2


def test_team_no_match():
    matches = _find_by_team(XLS, ["Zagłębie"])
    assert matches == []


def test_team_empty_list():
    assert _find_by_team(XLS, []) == []


def test_team_multiple_teams():
    matches = _find_by_team(XLS, ["Sparta", "Lech"])
    teams_found = {m["home"] for m in matches} | {m["away"] for m in matches}
    assert "Sparta" in teams_found
    assert "Lech" in teams_found


def test_team_youth_league_excluded():
    # "Unia Janikowo" appears in E1 row — must be filtered out
    matches = _find_by_team(XLS, ["Unia Janikowo"])
    assert all(not re.search(r'\b[E-G]\d\b', m["klasa"]) for m in matches)
    assert len(matches) == 2  # only A Gr.1 and B Gr.3, not E1
