# Obsada Sędziowska KPZPN – Skaner

Automatyczny skaner obsady sędziowskiej KPZPN. Sprawdza co 15 minut w czwartki (15:00–24:00) i piątki (8:00–15:00) czy pojawił się nowy plik XLS. Jeśli tak – wysyła email z meczami dla wybranych nazwisk.

## Setup

### 1. Fork / clone repo

### 2. Konto Resend (darmowe)

1. Zarejestruj się na [resend.com](https://resend.com)
2. Utwórz API Key w panelu
3. Skopiuj klucz

### 3. GitHub Secrets

W repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Wartość |
|--------|---------|
| `RESEND_API_KEY` | klucz z Resend |
| `SUBSCRIBER_EMAIL` | twój email |
| `SUBSCRIBER_NAMES` | `Górczyński,Winiarski,Chrzanowski,Błaszczyk,Szymaniak` |

### 4. Test ręczny

**Actions → Skanuj obsadę sędziowską → Run workflow**

## Dodawanie kolejnych sędziów

Aktualnie konfiguracja przez Secrets (jeden subskrybent). Dla wielu sędziów – plik `subscribers.json` + rozbudowa skryptu (w planach).

## Jak działa

1. Scrape głównej strony kpzpn.pl → szuka linków `.xls`
2. Porównuje URL z poprzednim skanem (cache)
3. Jeśli nowy plik → parsuje Excel → szuka nazwisk
4. Wysyła email z dopasowanymi meczami
5. Zapisuje URL do cache na następny run
