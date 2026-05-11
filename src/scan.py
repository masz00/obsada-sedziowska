import os
import re
import requests
import xlrd
import resend
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CACHE_FILE = Path(".cache/last_url.txt")
KPZPN_URL = "https://kpzpn.pl"

# E/F/G = youth/amateur categories — excluded everywhere
_YOUTH_RE = re.compile(r'\b[E-G]\d\b')

COL_KLASA   = 1
COL_HOME    = 2
COL_AWAY    = 3
COL_DATE    = 4
COL_TIME    = 5
COL_REFEREE = 7
COL_ASS1    = 8
COL_ASS2    = 9

# Net fees (PLN netto) by shortened class name and role ("sg", "a", "one")
# "one" = sole referee in Klasa B (no assistants)
FEES = [
    (r'^IV$',             {"sg": 316, "a": 258}),
    (r'^KO',              {"sg": 258, "a": 217}),
    (r'^A(?:\s|$)',       {"sg": 199, "a": 167}),
    (r'^B(?:\s|$)',       {"sg": 176, "a": 145, "one": 226}),
    (r'^III K$',          {"sg": 131, "a": 90}),
    (r'^IV K$',           {"sg": 127, "a": 108}),
    (r'^(?:I|II) A',      {"sg": 199, "a": 167}),
    (r'^III A',           {"sg": 140, "a": 118}),
    (r'^IV A',            {"sg": 127, "a": 108}),
    (r'^I B',             {"sg": 181, "a": 163}),
    (r'^(?:II|III|IV) B', {"sg": 127, "a": 108}),
    (r'^I [CD]',          {"sg": 113, "a": 95}),
    (r'^(?:II|III|IV) C', {"sg": 104, "a": 81}),
    (r'^(?:II|III|IV) D', {"sg": 86,  "a": 68}),
]


def get_fee(klasa, role):
    for pattern, fees in FEES:
        if re.match(pattern, klasa):
            return fees.get(role)
    return None


def shorten_klasa(raw):
    raw = raw.strip()

    if " - " in raw:
        raw = raw.split(" - ", 1)[1].strip()

    raw = re.sub(r'^[^\s:]+:\s*', '', raw).strip()
    raw = re.sub(r'\s*\(RW\)\s*$', '', raw).strip()

    r = raw.lower()

    if 'klasa okr' in r:
        m = re.search(r'[Gg]rupa\s*(\d+)', raw)
        return f"KO Gr.{m.group(1)}" if m else "KO"

    if 'klasa a' in r:
        m = re.search(r'[Gg]rupa\s*(\d+)', raw)
        return f"A Gr.{m.group(1)}" if m else "A"

    if 'klasa b' in r:
        m = re.search(r'[Gg]rupa\s*(\d+)', raw)
        return f"B Gr.{m.group(1)}" if m else "B"

    if re.search(r'^iv liga$', r):
        return "IV"

    if 'trzecia liga kobiet' in r:
        return "III K"

    if 'czwarta liga kobiet' in r:
        return "IV K"

    m_liga = re.search(r'^(I{1,3}V?|IV)\s+liga', raw, re.I)
    m_cat  = re.search(r'\b([A-G]\d)\b', raw)
    if m_liga and m_cat:
        liga = m_liga.group(1).upper()
        cat  = m_cat.group(1).upper()
        m_gr = re.search(r'[Gg]rupa\s*(\d+)', raw)
        return f"{liga} {cat} Gr.{m_gr.group(1)}" if m_gr else f"{liga} {cat}"

    m_cat2 = re.match(r'^([A-G]\d)\b', raw)
    if m_cat2:
        cat = m_cat2.group(1).upper()
        m_gr = re.search(r'[Gg]rupa\s*(\d+)', raw)
        return f"{cat} Gr.{m_gr.group(1)}" if m_gr else cat

    return raw


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def get_xls_urls():
    for attempt in range(3):
        try:
            resp = requests.get(KPZPN_URL, timeout=60, headers=HEADERS)
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"[scan] attempt {attempt+1}/3 failed: {e}")
            if attempt == 2:
                print("[scan] kpzpn.pl unreachable, skipping")
                return []
            import time; time.sleep(10)
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"\.(xls|xlsx)$", href, re.IGNORECASE):
            if not href.startswith("http"):
                href = KPZPN_URL + href
            if href not in urls:
                urls.append(href)

    urls.sort(reverse=True)
    return urls


def get_last_url():
    if CACHE_FILE.exists():
        return CACHE_FILE.read_text().strip()
    return None


def save_url(url):
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(url)



def download_xls(url):
    resp = requests.get(url, timeout=60, headers=HEADERS)
    resp.raise_for_status()
    return resp.content


def _parse_rows(content, names, name_offset=0):
    """Find all XLS rows matching any of the given names."""
    book = xlrd.open_workbook(file_contents=content, encoding_override="cp1250")
    sheet = book.sheets()[0]
    matches = []

    for row_idx in range(4, sheet.nrows):
        def cell(c, ri=row_idx):
            return str(sheet.cell_value(ri, c)).strip()

        referee = cell(COL_REFEREE)
        ass1    = cell(COL_ASS1)
        ass2    = cell(COL_ASS2)
        all_ref = f"{referee} {ass1} {ass2}"

        for name_idx, name in enumerate(names):
            if name.lower() not in all_ref.lower():
                continue

            raw_date = cell(COL_DATE)
            raw_time = cell(COL_TIME)[:5]
            try:
                date_obj = datetime.strptime(f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M")
                date_fmt = date_obj.strftime("%d.%m.%Y")
            except ValueError:
                date_fmt = raw_date
                date_obj = datetime.max

            klasa      = shorten_klasa(cell(COL_KLASA))
            if _YOUTH_RE.search(klasa):
                continue

            assistants = [a for a in [ass1, ass2] if a and len(a) > 2 and any(c.isalpha() for c in a)]

            n = name.lower()
            if n in referee.lower():
                role = "one" if klasa.startswith("B") and len(assistants) == 0 else "sg"
            elif n in ass1.lower() or n in ass2.lower():
                role = "a"
            else:
                role = None

            matches.append({
                "name_idx":  name_offset + name_idx,
                "name":      name,
                "klasa":     klasa,
                "home":      cell(COL_HOME),
                "away":      cell(COL_AWAY),
                "date_fmt":  date_fmt,
                "date_obj":  date_obj,
                "time":      raw_time,
                "sg":        referee,
                "a1":        assistants[0] if len(assistants) > 0 else "—",
                "a2":        assistants[1] if len(assistants) > 1 else "—",
                "role":      role,
                "fee":       get_fee(klasa, role) if role else None,
                "is_co_ref": False,
            })

    matches.sort(key=lambda m: (m["name_idx"], m["date_obj"]))
    return matches


def _find_by_league(content, leagues):
    """Return all rows where shortened klasa matches any of the given league strings."""
    if not leagues:
        return []
    book = xlrd.open_workbook(file_contents=content, encoding_override="cp1250")
    sheet = book.sheets()[0]
    matches = []
    for row_idx in range(4, sheet.nrows):
        def cell(c, ri=row_idx):
            try:
                return str(sheet.cell_value(ri, c)).strip()
            except IndexError:
                return ""
        klasa = shorten_klasa(cell(COL_KLASA))
        if _YOUTH_RE.search(klasa):
            continue
        for league in leagues:
            if klasa.lower() != league.lower():
                continue
            raw_date = cell(COL_DATE)
            raw_time = cell(COL_TIME)[:5]
            try:
                date_obj = datetime.strptime(f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M")
                date_fmt = date_obj.strftime("%d.%m.%Y")
            except ValueError:
                date_fmt = raw_date
                date_obj = datetime.max
            referee = cell(COL_REFEREE)
            ass1    = cell(COL_ASS1)
            ass2    = cell(COL_ASS2)
            assistants = [a for a in [ass1, ass2] if a and len(a) > 2 and any(c.isalpha() for c in a)]
            matches.append({
                "group":    league,
                "klasa":    klasa,
                "home":     cell(COL_HOME),
                "away":     cell(COL_AWAY),
                "date_fmt": date_fmt,
                "date_obj": date_obj,
                "time":     raw_time,
                "sg":       referee,
                "a1":       assistants[0] if len(assistants) > 0 else "—",
                "a2":       assistants[1] if len(assistants) > 1 else "—",
            })
            break
    matches.sort(key=lambda m: (m["group"], m["date_obj"]))
    return matches


def _find_by_team(content, teams):
    """Return all rows where home or away team contains any of the given team strings."""
    if not teams:
        return []
    book = xlrd.open_workbook(file_contents=content, encoding_override="cp1250")
    sheet = book.sheets()[0]
    matches = []
    seen = set()
    for row_idx in range(4, sheet.nrows):
        def cell(c, ri=row_idx):
            try:
                return str(sheet.cell_value(ri, c)).strip()
            except IndexError:
                return ""
        home = cell(COL_HOME)
        away = cell(COL_AWAY)
        klasa_t = shorten_klasa(cell(COL_KLASA))
        if _YOUTH_RE.search(klasa_t):
            continue
        for team in teams:
            tl = team.lower()
            if (tl in home.lower() or tl in away.lower()) and (row_idx, team) not in seen:
                seen.add((row_idx, team))
                raw_date = cell(COL_DATE)
                raw_time = cell(COL_TIME)[:5]
                try:
                    date_obj = datetime.strptime(f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M")
                    date_fmt = date_obj.strftime("%d.%m.%Y")
                except ValueError:
                    date_fmt = raw_date
                    date_obj = datetime.max
                referee = cell(COL_REFEREE)
                ass1    = cell(COL_ASS1)
                ass2    = cell(COL_ASS2)
                assistants = [a for a in [ass1, ass2] if a and len(a) > 2 and any(c.isalpha() for c in a)]
                klasa = shorten_klasa(cell(COL_KLASA))
                matches.append({
                    "group":    team,
                    "klasa":    klasa,
                    "home":     home,
                    "away":     away,
                    "date_fmt": date_fmt,
                    "date_obj": date_obj,
                    "time":     raw_time,
                    "sg":       referee,
                    "a1":       assistants[0] if len(assistants) > 0 else "—",
                    "a2":       assistants[1] if len(assistants) > 1 else "—",
                })
    matches.sort(key=lambda m: (m["group"], m["date_obj"]))
    return matches


def parse_xls_for_subscriber(content, me, friends, include_co_refs):
    names = ([me] if me else []) + list(friends)
    matches = _parse_rows(content, names)

    if include_co_refs and me:
        my_matches = [m for m in matches if me.lower() in m["name"].lower()]

        co_ref_set = set()
        for m in my_matches:
            for col in [m["sg"], m["a1"], m["a2"]]:
                if col and col != "—" and me.lower() not in col.lower():
                    co_ref_set.add(col.strip())

        new_co_refs = sorted([
            cr for cr in co_ref_set
            if not any(n.lower() in cr.lower() or cr.lower() in n.lower() for n in names)
        ])

        if new_co_refs:
            my_keys = {(m["home"], m["away"], m["date_fmt"], m["time"]) for m in my_matches}
            co_matches = _parse_rows(content, new_co_refs, name_offset=len(names))
            for m in co_matches:
                m["is_co_ref"] = True
            co_matches = [m for m in co_matches
                          if (m["home"], m["away"], m["date_fmt"], m["time"]) not in my_keys]
            matches.extend(co_matches)
            matches.sort(key=lambda m: (m["name_idx"], m["date_obj"]))

    return matches


def _build_watch_section(items, title):
    """HTML section for league or team watch rows (no fee column)."""
    if not items:
        return ""
    rows = ""
    prev_group = None
    for m in items:
        if m["group"] != prev_group:
            count = sum(1 for x in items if x["group"] == m["group"])
            rows += (
                f'<tr><td colspan="7" style="background:#2e1a1a;color:white;'
                f'padding:8px 12px;font-weight:bold;font-size:15px">'
                f'{m["group"]}'
                f'<span style="font-weight:normal;font-size:13px"> &nbsp;&mdash; {count} mecz(y)</span>'
                f'</td></tr>\n'
            )
            prev_group = m["group"]
        rows += (
            f"<tr>"
            f'<td style="padding:6px 10px;white-space:nowrap">{m["klasa"]}</td>'
            f'<td style="padding:6px 10px">{m["home"]}</td>'
            f'<td style="padding:6px 10px">{m["away"]}</td>'
            f'<td style="padding:6px 10px;white-space:nowrap">{m["date_fmt"]} {m["time"]}</td>'
            f'<td style="padding:6px 10px">{m["sg"]}</td>'
            f'<td style="padding:6px 10px;color:#555">{m["a1"]}</td>'
            f'<td style="padding:6px 10px;color:#555">{m["a2"]}</td>'
            f"</tr>\n"
        )
    return f"""
  <h3 style="color:#1a1a2e;margin-top:28px">{title}</h3>
  <table border="1" cellspacing="0" cellpadding="0"
         style="border-collapse:collapse;width:100%;border-color:#ddd;font-size:14px">
    <thead>
      <tr style="background:#f0f0f0">
        <th style="padding:7px 10px;text-align:left">Liga</th>
        <th style="padding:7px 10px;text-align:left">Gospodarze</th>
        <th style="padding:7px 10px;text-align:left">Goście</th>
        <th style="padding:7px 10px;text-align:left">Data / Godz.</th>
        <th style="padding:7px 10px;text-align:left">SG</th>
        <th style="padding:7px 10px;text-align:left">A1</th>
        <th style="padding:7px 10px;text-align:left">A2</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
"""


def build_email_html(matches, xls_url, me=None, friends=None,
                     league_matches=None, team_matches=None):
    all_names = ([me] if me else []) + list(friends or [])

    name_fee_total = {}
    name_count = {}
    for m in matches:
        n = m["name"]
        name_fee_total[n] = name_fee_total.get(n, 0) + (m["fee"] or 0)
        name_count[n]     = name_count.get(n, 0) + 1

    rows_html = ""
    prev_name = None

    for m in matches:
        if m["name"] != prev_name:
            total   = name_fee_total[m["name"]]
            count   = name_count[m["name"]]
            fee_str = f" &nbsp;|&nbsp; {total} PLN netto" if total else ""
            bg      = "#1a2e1a" if m.get("is_co_ref") else "#1a1a2e"
            co_tag  = " <span style='font-size:12px;font-weight:normal;opacity:0.75'>(co-referee)</span>" if m.get("is_co_ref") else ""
            rows_html += (
                f'<tr><td colspan="8" style="background:{bg};color:white;'
                f'padding:8px 12px;font-weight:bold;font-size:15px">'
                f'{m["name"]}{co_tag}'
                f'<span style="font-weight:normal;font-size:13px"> &nbsp;&mdash; {count} mecz(y){fee_str}</span>'
                f'</td></tr>\n'
            )
            prev_name = m["name"]

        fee_cell = f"{m['fee']} PLN" if m["fee"] else "—"
        rows_html += (
            f"<tr>"
            f'<td style="padding:6px 10px;white-space:nowrap">{m["klasa"]}</td>'
            f'<td style="padding:6px 10px">{m["home"]}</td>'
            f'<td style="padding:6px 10px">{m["away"]}</td>'
            f'<td style="padding:6px 10px;white-space:nowrap">{m["date_fmt"]} {m["time"]}</td>'
            f'<td style="padding:6px 10px">{m["sg"]}</td>'
            f'<td style="padding:6px 10px;color:#555">{m["a1"]}</td>'
            f'<td style="padding:6px 10px;color:#555">{m["a2"]}</td>'
            f'<td style="padding:6px 10px;font-weight:bold;color:#2a6200;white-space:nowrap">{fee_cell}</td>'
            f"</tr>\n"
        )

    found = sorted(
        {m["name"] for m in matches if not m.get("is_co_ref")},
        key=lambda n: all_names.index(n) if n in all_names else 99
    )
    not_found = [n for n in all_names if n not in {m["name"] for m in matches}]

    names_line = ", ".join(f"<strong>{n}</strong>" for n in found)
    if not_found:
        names_line += " &nbsp;|&nbsp; <span style='color:#999'>not found: " + ", ".join(not_found) + "</span>"

    date_str   = datetime.now().strftime("%d.%m.%Y %H:%M")
    main_count = len([m for m in matches if not m.get("is_co_ref")])

    league_section = _build_watch_section(league_matches or [], "Obserwowane ligi")
    team_section   = _build_watch_section(team_matches or [], "Obserwowane drużyny")

    return f"""
<div style="font-family:Arial,sans-serif;max-width:960px">
  <h2 style="color:#1a1a2e">Nowa obsada sędziowska KPZPN</h2>
  <p>Wykryto nowy plik obsady ({date_str}). Łącznie: <strong>{main_count}</strong> mecz(y).</p>
  <p style="margin-bottom:12px">Skanowane nazwiska: {names_line}</p>
  <table border="1" cellspacing="0" cellpadding="0"
         style="border-collapse:collapse;width:100%;border-color:#ddd;font-size:14px">
    <thead>
      <tr style="background:#f0f0f0">
        <th style="padding:7px 10px;text-align:left">Liga</th>
        <th style="padding:7px 10px;text-align:left">Gospodarze</th>
        <th style="padding:7px 10px;text-align:left">Goście</th>
        <th style="padding:7px 10px;text-align:left">Data / Godz.</th>
        <th style="padding:7px 10px;text-align:left">SG</th>
        <th style="padding:7px 10px;text-align:left">A1</th>
        <th style="padding:7px 10px;text-align:left">A2</th>
        <th style="padding:7px 10px;text-align:left">Stawka</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  {league_section}
  {team_section}
  <p style="margin-top:20px">
    <a href="{xls_url}" style="color:#0066cc">Pobierz pełną obsadę (XLS)</a>
  </p>
</div>
"""


def send_email(to_email, html):
    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send({
        "from": "Obsada KPZPN <obsada@szymaniak.online>",
        "reply_to": [os.environ.get("REPLY_TO_EMAIL", "")],
        "to": [to_email],
        "subject": "Nowa obsada sędziowska KPZPN",
        "html": html,
    })


def main():
    import json
    subscribers = json.loads(os.environ["SUBSCRIBERS"])

    urls = get_xls_urls()
    print(f"[scan] found XLS urls: {urls}")

    if not urls:
        print("[scan] no XLS found on page")
        return

    latest_url = urls[0]
    last_url = get_last_url()
    print(f"[scan] latest={latest_url}  last_known={last_url}")

    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry_run:
        print("[scan] *** DRY RUN — emails will NOT be sent ***")

    if latest_url == last_url and not dry_run:
        print("[scan] no new file, done")
        return
    if latest_url == last_url:
        print("[scan] no new file, but DRY_RUN — proceeding anyway")

    print("[scan] downloading...")
    content = download_xls(latest_url)

    if dry_run:
        book = xlrd.open_workbook(file_contents=content, encoding_override="cp1250")
        sheet = book.sheets()[0]
        all_klasy = sorted({
            k for r in range(4, sheet.nrows)
            if (k := shorten_klasa(str(sheet.cell_value(r, COL_KLASA)).strip()))
            and not _YOUTH_RE.search(k)
        })
        print(f"[scan] all leagues in XLS ({len(all_klasy)}): {all_klasy}")

    for sub in subscribers:
        if sub.get("disabled"):
            continue

        email = sub["email"]

        me              = sub.get("me")
        friends         = sub.get("friends", [])
        include_co_refs = sub.get("include_co_refs", False)
        leagues         = sub.get("leagues", [])
        teams           = sub.get("teams", [])

        print(f"[scan] checking for {email}: me={me}, friends={friends}, leagues={leagues}, teams={teams}")

        matches        = parse_xls_for_subscriber(content, me, friends, include_co_refs)
        league_matches = _find_by_league(content, leagues)
        team_matches   = _find_by_team(content, teams)
        print(f"[scan] ref={len(matches)} league={len(league_matches)} team={len(team_matches)}")

        if matches or league_matches or team_matches:
            html = build_email_html(
                matches, latest_url, me=me, friends=friends,
                league_matches=league_matches, team_matches=team_matches,
            )
            if dry_run:
                print(f"[scan] DRY RUN — would send email to {email}")
            else:
                send_email(email, html)
                print(f"[scan] email sent to {email}")
        else:
            print(f"[scan] no matches for {email}, skipping")

    if not dry_run:
        save_url(latest_url)
        print("[scan] cache updated")
    else:
        print("[scan] DRY RUN — cache not updated")


if __name__ == "__main__":
    main()
