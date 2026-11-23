# jc-market-data

Public copies of official market data, refreshed by GitHub Actions:

- `data/tw/` — TWSE / TPEx daily quotes and P/E, MOPS monthly revenue (weekdays, 18:05 Taipei). `freshness.csv` says whether each day's files are current.
- `data/sec_revenue.csv` — latest-quarter revenue and net income from the SEC XBRL frames API (Mondays).

Only public market data lives here. `scripts/check_public.py` runs before every commit and blocks anything else.
