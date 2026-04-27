import os
import re
import json
import requests
import xlrd
import resend
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

CACHE_FILE = Path(".cache/last_url.txt")
KPZPN_URL = "https://kpzpn.pl"


def get_xls_urls():
    resp = requests.get(KPZPN_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"\.(xls|xlsx)$", href, re.IGNORECASE):
            if not href.startswith("http"):
                href = KPZPN_URL + href
            urls.append(href)

    # sort by date embedded in URL path (YYYY/MM/...)
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
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def parse_xls_for_names(content, names):
    book = xlrd.open_workbook(file_contents=content)
    matches = []
    seen = set()

    for sheet in book.sheets():
        for row_idx in range(sheet.nrows):
            row_vals = []
            for col in range(sheet.ncols):
                cell = sheet.cell(row_idx, col)
                val = str(cell.value).strip()
                row_vals.append(val)

            row_text = " ".join(row_vals)

            for name in names:
                if name.lower() in row_text.lower():
                    key = (row_idx, sheet.name)
                    if key not in seen:
                        seen.add(key)
                        matches.append({
                            "name": name,
                            "row": row_vals,
                            "sheet": sheet.name,
                        })
                    break

    return matches


def build_email_html(matches, xls_url):
    rows_html = ""
    for m in matches:
        cells = " &nbsp;|&nbsp; ".join(c for c in m["row"] if c)
        rows_html += (
            f"<tr>"
            f"<td style='padding:6px 12px;font-weight:bold'>{m['name']}</td>"
            f"<td style='padding:6px 12px'>{cells}</td>"
            f"</tr>\n"
        )

    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    return f"""
<div style="font-family:Arial,sans-serif;max-width:900px">
  <h2 style="color:#1a1a2e">Nowa obsada sędziowska KPZPN</h2>
  <p>Wykryto nowy plik obsady ({date_str}). Znaleziono <strong>{len(matches)}</strong> mecz(y):</p>
  <table border="1" cellspacing="0" cellpadding="0"
         style="border-collapse:collapse;width:100%;border-color:#ddd">
    <thead>
      <tr style="background:#1a1a2e;color:white">
        <th style="padding:8px 12px;text-align:left">Nazwisko</th>
        <th style="padding:8px 12px;text-align:left">Szczegóły</th>
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


def send_email(to_email, html, xls_url):
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
        html = build_email_html(matches, latest_url)
        send_email(email, html, latest_url)
        print(f"[scan] email sent to {email}")
    else:
        print("[scan] no matching names in new file, no email sent")

    save_url(latest_url)
    print("[scan] cache updated")


if __name__ == "__main__":
    main()
