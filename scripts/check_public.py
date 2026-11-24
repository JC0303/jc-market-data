"""Refuse to publish anything personal from this PUBLIC repository.

This repo exists only so a Google Sheet can read official market data through
public URLs. Holdings, costs, rules, decisions and account details belong in the
private repository. Every workflow runs this before it commits, and the tests
run it too, so a personal file can never be pushed here by an automated job.
"""
import csv
import datetime as dt
import pathlib
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlsplit
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWED_DATA = {
    'data/tw/bwibbu_all.csv', 'data/tw/stock_day_all.csv', 'data/tw/tpex_close.csv',
    'data/tw/tpex_pe.csv', 'data/tw/mops_rev_L.csv', 'data/tw/mops_rev_O.csv',
    'data/tw/status.csv', 'data/tw/freshness.csv', 'data/tw/freshness.json',
    'data/sec_revenue.csv',
    *(f'data/market/{name}.csv' for name in (
        'tw_index', 'otc_index', 'tw_institution', 'otc_institution', 'tw_margin', 'otc_margin',
        'tx_oi', 'SP500', 'VIXCLS', 'DGS10', 'DFF', 'DEXTAUS', 'status', 'freshness')),
}
# Words that only appear in personal records, never in official market files.
PERSONAL = re.compile(r'avg_cost|positions\.csv|SinoPac|永豐|帳戶|持股|成本均價|approved_for_execution'
                      r'|monthly_dca|OPEN_ITEMS|Claude invest', re.I)
TEXT = {'.py', '.md', '.yml', '.yaml', '.json', '.txt', '.toml', '.cfg'}


def check_series(path):
    # Only date, numbers, an official URL and a UTC timestamp may enter a public series.
    if __name__ == "__main__":
        from market_sources import COLUMNS, endpoint
    else:
        from scripts.market_sources import COLUMNS, endpoint
    name = path.stem
    expected = ("date", *COLUMNS[name], "source_url", "fetched_utc")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != expected:
            raise ValueError("unexpected CSV columns")
        previous = None
        for r in reader:
            day = dt.date.fromisoformat(r["date"])
            if previous and day <= previous:
                raise ValueError("dates are duplicated or unsorted")
            previous = day
            if (None in r or not all(Decimal(r[k]).is_finite() for k in COLUMNS[name])
                    or dt.datetime.fromisoformat(r["fetched_utc"]).utcoffset() != dt.timedelta(0)):
                raise ValueError("invalid numeric observation or UTC timestamp")
            url = urlsplit(r["source_url"])
            template = urlsplit(endpoint(name, day, day))
            if (url.scheme, url.netloc, url.path) != (template.scheme, template.netloc, template.path):
                raise ValueError("unexpected source URL")
            params = parse_qsl(url.query, keep_blank_values=True)
            expected_params = dict(parse_qsl(template.query))
            if url.fragment or sorted(k for k, _ in params) != sorted(expected_params):
                raise ValueError("unexpected source URL parameters")
            for key, value in params:
                if key == "cosd":
                    dt.date.fromisoformat(value)
                elif key in ("date", "dayDate", "queryStartDate", "queryEndDate"):
                    dt.datetime.strptime(value, "%Y/%m/%d" if "/" in expected_params[key] else "%Y%m%d")
                elif value != expected_params[key]:
                    raise ValueError("unexpected source URL value")



def problems():
    found = []
    for path in sorted(ROOT.rglob('*')):
        if '.git' in path.parts or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith('data/') and rel not in ALLOWED_DATA:
            found.append(f'{rel}: not an approved public market-data file')
        if rel.startswith('data/market/') and rel in ALLOWED_DATA and path.stem not in ('status', 'freshness'):
            try:
                check_series(path)
            except (ValueError, TypeError, KeyError, csv.Error, InvalidOperation) as exc:
                found.append(f'{rel}: {exc}')
        if (path.suffix in TEXT or rel.startswith('data/market/')) and rel != 'scripts/check_public.py' and not rel.startswith('tests/'):
            text = path.read_text(encoding='utf-8', errors='replace')
            hit = PERSONAL.search(text)
            if hit:
                found.append(f'{rel}: contains "{hit.group(0)}", which belongs in the private repo')
    return found


if __name__ == '__main__':
    bad = problems()
    for line in bad:
        print('BLOCKED', line)
    sys.exit(1 if bad else 0)
