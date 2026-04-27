import os
import re
import requests
import xlrd
import resend
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

CACHE_FILE = Path(".cache/last_url.txt")
KPZPN_URL = "https://kpzpn.pl"

# Columns in XLS
COL_KLASA   = 1
COL_HOME    = 2
COL_AWAY    = 3
COL_DATE    = 4
COL_TIME    = 5
COL_REFEREE = 7
COL_ASS1    = 8
COL_ASS2    = 9


def shorten_klasa(raw):
    raw = raw.strip()

    # Take part after " - "
    if " - " in raw:
        raw = raw.split(" - ", 1)[1].strip()

    # Remove city prefix e.g. "Bydgoszcz: ", "Toruń: ", "Włocławek: "
    raw = re.sub(r'^[^\s:]+:\s*', '', raw).strip()

    # Remove (RW) suffix
    raw = re.sub(r'\s*\(RW\)\s*$', '', raw).strip()

    r = raw.lower()

    # Senior leagues
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

    # Youth leagues: "(I|II|III|IV) liga ... (A1|B2|C1|...) ..."
    m_liga = re.search(r'^(I{1,3}V?|IV)\s+liga', raw, re.I)
    m_cat  = re.search(r'\b([A-G]\d)\b', raw)
    if m_liga and m_cat:
        liga = m_liga.group(1).upper()
        cat  = m_cat.group(1).upper()
        m_gr = re.search(r'[Gg]rupa\s*(\d+)', raw)
        return f"{liga} {cat} Gr.{m_gr.group(1)}" if m_gr else f"{liga} {cat}"

    # Standalone category codes like "G1 Skrzat ...", "E1 Orlik ..."
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


def parse_xls_for_names(content, names):
    book = xlrd.open_workbook(file_contents=content, encoding_override="cp1250")
    sheet = book.sheets()[0]

    matches = []
    seen_rows = set()

    for row_idx in range(4, sheet.nrows):
        def cell(c):
            return str(sheet.cell_value(row_idx, c)).strip()

        referee = cell(COL_REFEREE)
        ass1    = cell(COL_ASS1)
        ass2    = cell(COL_ASS2)
        all_ref = f"{referee} {ass1} {ass2}"

        for name_idx, name in enumerate(names):
            if name.lower() in all_ref.lower() and row_idx not in seen_rows:
                seen_rows.add(row_idx)

                raw_date = cell(COL_DATE)
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
                    date_fmt = date_obj.strftime("%d.%m.%Y")
                except ValueError:
                    date_fmt = raw_date
                    date_obj = datetime.max

                assistants = [a for a in [ass1, ass2] if a and len(a) > 2 and any(c.isalpha() for c in a)]

                matches.append({
                    "name_idx":   name_idx,
                    "name":       name,
                    "klasa":      shorten_klasa(cell(COL_KLASA)),
                    "home":       cell(COL_HOME),
                    "away":       cell(COL_AWAY),
                    "date_fmt":   date_fmt,
                    "date_obj":   date_obj,
                    "time":       cell(COL_TIME)[:5],
                    "referee":    referee,
                    "assistants": assistants,
                })
                break

    matches.sort(key=lambda m: (m["name_idx"], m["date_obj"]))
    return matches


def build_email_html(matches, xls_url, names=None):
    rows_html = ""
    prev_name = None

    for m in matches:
        if m["name"] != prev_name:
            rows_html += (
                f'<tr><td colspan="5" style="background:#1a1a2e;color:white;'
                f'padding:8px 12px;font-weight:bold;font-size:15px">'
                f'{m["name"]}</td></tr>\n'
            )
            prev_name = m["name"]

        ass_str = "; ".join(m["assistants"]) if m["assistants"] else "—"
        rows_html += (
            f"<tr>"
            f'<td style="padding:6px 10px;white-space:nowrap">{m["klasa"]}</td>'
            f'<td style="padding:6px 10px">{m["home"]}</td>'
            f'<td style="padding:6px 10px">{m["away"]}</td>'
            f'<td style="padding:6px 10px;white-space:nowrap">{m["date_fmt"]} {m["time"]}</td>'
            f'<td style="padding:6px 10px;color:#555">{ass_str}</td>'
            f"</tr>\n"
        )

    found_names = sorted({m["name"] for m in matches}, key=lambda n: names.index(n) if names and n in names else 0)
    not_found   = [n for n in (names or []) if n not in {m["name"] for m in matches}]

    names_line = ", ".join(f"<strong>{n}</strong>" for n in found_names)
    if not_found:
        names_line += " &nbsp;|&nbsp; <span style='color:#999'>nie znaleziono: " + ", ".join(not_found) + "</span>"

    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    return f"""
<div style="font-family:Arial,sans-serif;max-width:960px">
  <h2 style="color:#1a1a2e">Nowa obsada sędziowska KPZPN</h2>
  <p>Wykryto nowy plik obsady ({date_str}). Łącznie: <strong>{len(matches)}</strong> mecz(y).</p>
  <p style="margin-bottom:12px">Skanowane nazwiska: {names_line}</p>
  <table border="1" cellspacing="0" cellpadding="0"
         style="border-collapse:collapse;width:100%;border-color:#ddd;font-size:14px">
    <thead>
      <tr style="background:#f0f0f0">
        <th style="padding:7px 10px;text-align:left">Liga</th>
        <th style="padding:7px 10px;text-align:left">Gospodarze</th>
        <th style="padding:7px 10px;text-align:left">Goście</th>
        <th style="padding:7px 10px;text-align:left">Data / Godz.</th>
        <th style="padding:7px 10px;text-align:left">Asystenci</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <p style="margin-top:20px">
    <a href="{xls_url}" style="color:#0066cc">Pobierz pełną obsadę (XLS)</a>
  </p>
</div>
"""


def send_email(to_email, html):
    resend.api_key = os.environ["RESEND_API_KEY"]
    resend.Emails.send({
        "from": "Obsada KPZPN <onboarding@resend.dev>",
        "to": [to_email],
        "subject": "Nowa obsada sędziowska KPZPN",
        "html": html,
    })


def main():
    names = [n.strip() for n in os.environ["SUBSCRIBER_NAMES"].split(",")]
    email = os.environ["SUBSCRIBER_EMAIL"]

    print(f"[scan] names={names}")

    urls = get_xls_urls()
    print(f"[scan] found XLS urls: {urls}")

    if not urls:
        print("[scan] no XLS found on page")
        return

    latest_url = urls[0]
    last_url = get_last_url()
    print(f"[scan] latest={latest_url}  last_known={last_url}")

    if latest_url == last_url:
        print("[scan] no new file, done")
        return

    print("[scan] new file! downloading...")
    content = download_xls(latest_url)

    matches = parse_xls_for_names(content, names)
    print(f"[scan] matches={len(matches)}")

    if matches:
        html = build_email_html(matches, latest_url, names)
        send_email(email, html)
        print(f"[scan] email sent to {email}")
    else:
        print("[scan] no matching names in new file, no email sent")

    save_url(latest_url)
    print("[scan] cache updated")


if __name__ == "__main__":
    main()
