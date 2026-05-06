# Obsada Sędziowska KPZPN – Skaner XLSX

Automatyczny skaner obsady sędziowskiej KPZPN. Sprawdza w czwartki i piątki czy pojawił się nowy plik XLS z obsadą jeśli tak, wysyła email z tabelą meczów, rolą i stawką netto dla każdego sędziego z listy.

## Jak działa

1. GitHub Actions (cron) scrape'uje kpzpn.pl w poszukiwaniu nowego pliku XLS
2. Porównuje URL z poprzednim skanem (cache) — jeśli ten sam, kończy
3. Sprawdza czy w tym tygodniu już wysłano — jeśli tak, kończy
4. Parsuje Excel i filtruje mecze po nazwiskach z listy każdego subskrybenta
5. Opcjonalnie dorzuca mecze sędziów jadących razem z subskrybentem (`include_co_refs`)
6. Wysyła email przez Resend z tabelą meczów i stawkami netto (wg ekwiwalentu KPZPN 2024/2025)

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
| `SUBSCRIBERS`    | JSON z listą subskrybentów (patrz niżej) |

### 4. Format `SUBSCRIBERS`

```json
[
  {
    "email": "jan@example.com",
    "me": "Kowalski",
    "friends": ["Nowak", "Wiśniewska"],
    "include_co_refs": true
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

| Pole              | Opis                                                               |
| ----------------- | ------------------------------------------------------------------ |
| `email`           | Adres odbiorcy                                                     |
| `me`              | Twoje nazwisko — Twoje mecze wyświetlane jako pierwsze             |
| `friends`         | Pozostałe nazwiska do skanowania                                   |
| `include_co_refs` | `true` = dorzuca mecze co-sędziów jadących z Tobą w danym tygodniu |
| `disabled`        | `true` = pomija subskrybenta (przydatne przy testach)              |

### 5. Zmień domenę nadawcy

W `src/scan.py` zmień:

```python
"from": "Obsada KPZPN <obsada@twoja-domena.pl>",
```

### 6. Test ręczny

**Actions → Skanuj obsadę sędziowską → Run workflow**

## Harmonogram

| Dzień    | Godziny (CEST) |
| -------- | -------------- |
| Czwartek | 15:00 – 23:00  |
| Piątek   | 10:00 – 16:00  |

Skanowanie co 15 minut.
