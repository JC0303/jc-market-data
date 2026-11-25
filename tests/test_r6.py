import datetime as dt
from pathlib import Path

import requests

from scripts import fetch_market as market


class Client:
    def __init__(self):
        self.calls = []
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        r = requests.Response()
        r.status_code = 200 if len(self.calls) == 1 else 307
        r._content = b'diagnostic'
        return r


def test_session_uses_official_page_then_same_client(monkeypatch):
    from scripts import r6_backfill as r6
    client = Client()
    monkeypatch.setattr(r6.time, 'sleep', lambda seconds: None)
    get = r6.session_getter('tw_margin', client)
    try:
        get('https://wwwc.twse.com.tw/rwd/zh/marginTrading/MI_MARGN')
    except requests.HTTPError:
        pass
    assert len(client.calls) == 4
    assert client.calls[1][1]['headers']['Referer'] == client.calls[0][0]
    assert all(not kw['allow_redirects'] for _, kw in client.calls)


def test_repeated_307_stops_batch_without_touching_archive(tmp_path, monkeypatch):
    from scripts import r6_backfill as r6
    client = Client()
    monkeypatch.setattr(r6.time, 'sleep', lambda seconds: None)
    path = tmp_path / 'tw_margin.csv'
    row = dict(date='2026-11-20', financing_units=1, short_units=2, financing_thousand_twd=3,
               source_url='https://wwwc.twse.com.tw/', fetched_utc='2026-11-20T12:00:00+00:00')
    market.save_series(tmp_path,'tw_margin',{}, {dt.date(2026,11,20):row})
    before = path.read_bytes()
    results = r6.collect('tw_margin',[dt.date(2026,11,23),dt.date(2026,11,24)],tmp_path,r6.session_getter('tw_margin',client))
    assert len(results) == 1 and results[0][1] == 307
    assert path.read_bytes() == before


def test_workflow_installs_pinned_requirements():
    root = Path(__file__).resolve().parents[1]
    pins = (root/'requirements.txt').read_text().splitlines()
    assert all('==' in dep for dep in pins)
    assert {'holidays','pytest','requests'} <= {dep.split('==')[0] for dep in pins}
    assert 'pip install -r requirements.txt' in (root/'.github/workflows/market.yml').read_text()
