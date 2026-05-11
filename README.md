# Obsada Sędziowska KPZPN – Skaner

Automatyczny skaner obsady sędziowskiej KPZPN. Sprawdza w czwartki i piątki czy pojawił się nowy plik XLS z obsadą — jeśli tak, wysyła email z tabelą meczów, rolą i stawką netto.

## Jak działa

1. GitHub Actions (cron) scrape'uje kpzpn.pl w poszukiwaniu nowego pliku XLS
2. Porównuje URL z poprzednim skanem (cache) — jeśli ten sam, kończy
3. Parsuje Excel i dla każdego subskrybenta szuka meczów po nazwiskach, ligach i drużynach
4. Wysyła email przez Resend z tabelą meczów i stawkami netto (wg ekwiwalentu KPZPN 2024/2025)

## Stack

- **GitHub Actions** – cron, hosting logiki
- **Python** – requests, beautifulsoup4, xlrd
- **Resend** – wysyłka emaili

## Setup

### 1. Fork repo

### 2. Konto Resend + domena

- Zarejestruj się na [resend.com](https://resend.com)
- Dodaj i zweryfikuj własną domenę (Domains → Add Domain)
- Skopiuj API Key

### 3. GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Secret           | Opis                                     |
| ---------------- | ---------------------------------------- |
| `RESEND_API_KEY` | Klucz API z Resend                       |
| `REPLY_TO_EMAIL` | Adres reply-to w wysyłanych emailach     |
| `SUBSCRIBERS`    | JSON z listą subskrybentów (patrz niżej) |

### 4. Format `SUBSCRIBERS`

```json
[
  {
    "email": "jan@example.com",
    "me": "Kowalski",
    "friends": ["Nowak", "Wiśniewska"],
    "include_co_refs": true,
    "leagues": ["IV", "KO Gr.1"],
    "teams": ["Zawisza Bydgoszcz"]
  },
  {
    "email": "anna@example.com",
    "me": "Wiśniewska",
    "friends": ["Kowalski"],
    "include_co_refs": false,
    "disabled": true
  }
]
```

| Pole              | Opis                                                                        |
| ----------------- | --------------------------------------------------------------------------- |
| `email`           | Adres odbiorcy                                                              |
| `me`              | Twoje nazwisko — Twoje mecze wyświetlane jako pierwsze                      |
| `friends`         | Pozostałe nazwiska do skanowania                                            |
| `include_co_refs` | `true` = dorzuca mecze co-sędziów jadących z Tobą w tym tygodniu           |
| `leagues`         | Lista lig do obserwowania — wszystkie mecze z danej ligi (np. `"IV"`, `"KO Gr.1"`, `"B Gr.5"`) |
| `teams`           | Lista drużyn do obserwowania — mecze jako gospodarz lub gość (np. `"Zawisza Bydgoszcz"`) |
| `disabled`        | `true` = pomija subskrybenta                                                |

Ligi E/F/G (młodzieżowe) są automatycznie pomijane we wszystkich sekcjach.

Dokładne nazwy lig znajdziesz uruchamiając dry run (patrz niżej) — w logu pojawi się pełna lista lig z aktualnego XLS.

### 5. Zmień domenę nadawcy

W `src/scan.py` zmień:

```python
"from": "Obsada KPZPN <obsada@twoja-domena.pl>",
```

### 6. Lokalnie (opcjonalnie)

```bash
pip install -r requirements-dev.txt
cp .env.example .env   # uzupełnij kluczami
python src/scan.py
```

Dry run (bez wysyłki emaila):

```bash
DRY_RUN=1 python src/scan.py
```

### 7. Test na GitHub Actions

**Actions → dry run → Run workflow** — uruchamia skaner bez wysyłania emaili, pokazuje logi z listą lig i znalezionych meczów.

## Harmonogram

| Dzień    | Godziny (CEST) |
| -------- | -------------- |
| Czwartek | 15:00 – 23:00  |
| Piątek   | 10:00 – 16:00  |

Skanowanie co 15 minut.
