"""Refuse to publish anything personal from this PUBLIC repository.

This repo exists only so a Google Sheet can read official market data through
public URLs. Holdings, costs, rules, decisions and account details belong in the
private repository. Every workflow runs this before it commits, and the tests
run it too, so a personal file can never be pushed here by an automated job.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWED_DATA = {
    'data/tw/bwibbu_all.csv', 'data/tw/stock_day_all.csv', 'data/tw/tpex_close.csv',
    'data/tw/tpex_pe.csv', 'data/tw/mops_rev_L.csv', 'data/tw/mops_rev_O.csv',
    'data/tw/status.csv', 'data/tw/freshness.csv', 'data/tw/freshness.json',
    'data/sec_revenue.csv',
}
# Words that only appear in personal records, never in official market files.
PERSONAL = re.compile(r'avg_cost|positions\.csv|SinoPac|永豐|帳戶|持股|成本均價|approved_for_execution'
                      r'|monthly_dca|OPEN_ITEMS|Claude invest', re.I)
TEXT = {'.py', '.md', '.yml', '.yaml', '.json', '.txt', '.toml', '.cfg'}


def problems():
    found = []
    for path in sorted(ROOT.rglob('*')):
        if '.git' in path.parts or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith('data/') and rel not in ALLOWED_DATA:
            found.append(f'{rel}: not an approved public market-data file')
        if path.suffix in TEXT and rel != 'scripts/check_public.py' and not rel.startswith('tests/'):
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
