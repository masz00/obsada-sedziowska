# Obsada Sędziowska KPZPN – Skaner

Automatyczny skaner obsady sędziowskiej KPZPN. Sprawdza co 15 minut w czwartki (15:00–24:00 CEST) i piątki (8:00–15:00 CEST) czy pojawił się nowy plik XLS z obsadą. Jeśli tak – filtruje mecze po nazwiskach i wysyła spersonalizowany email do każdego subskrybenta.

## Jak działa

1. GitHub Actions (cron) scrape'uje kpzpn.pl w poszukiwaniu nowego pliku XLS
2. Porównuje URL z poprzednim skanem (cache)
3. Jeśli nowy plik – parsuje Excel i filtruje mecze po nazwiskach
4. Wysyła email przez Resend z tabelą: Liga | Gospodarze | Goście | Data | SG | A1 | A2
5. Każdy subskrybent dostaje tylko swoje mecze

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

| Secret | Opis |
|--------|------|
| `RESEND_API_KEY` | Klucz API z Resend |
| `SUBSCRIBERS` | JSON z listą subskrybentów (patrz niżej) |

Format `SUBSCRIBERS` (jedna linia):
```json
[{"email":"jan@example.com","names":["Kowalski","Nowak"]},{"email":"anna@example.com","names":["Wiśniewska"]}]
```

### 4. Zmień domenę nadawcy

W `src/scan.py` zmień:
```python
"from": "Obsada KPZPN <obsada@twoja-domena.pl>",
```

### 5. Test ręczny

**Actions → Skanuj obsadę sędziowską → Run workflow**

## Harmonogram

| Dzień | Godziny (CEST) |
|-------|---------------|
| Czwartek | 15:00 – 24:00 |
| Piątek | 08:00 – 15:00 |

Skanowanie co 15 minut w tych oknach czasowych.
