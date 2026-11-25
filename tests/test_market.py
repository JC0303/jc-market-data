import csv
import datetime as dt
import json
from pathlib import Path

import pytest

from scripts import fetch_market as market

FIX = Path(__file__).parent / "fixtures/market"
DAY = dt.date(2026, 11, 23)
NOW = dt.datetime(2026, 11, 23, 19, tzinfo=market.TPE)
STAMP = "2026-11-23T11:00:00+00:00"


def fixture(name):
    ext = "csv" if name in market.FRED or name == "tx_oi" else "json"
    return (FIX / f"{name}.{ext}").read_bytes()


def getter(changes=None):
    changes = changes or {}

    def read(url):
        for name in market.COLUMNS:
            template = market.endpoint(name, DAY, DAY)
            if (url.split("?")[0] == template.split("?")[0]
                    and (name not in market.FRED or f"id={name}&" in url)):
                body = changes.get(name, fixture(name))
                if name == "tx_oi" and "queryStartDate=2026/11/23" in url:
                    lines = body.splitlines()
                    body = b"\n".join(lines[:1] + [line for line in lines[1:] if line.startswith(b"2026/11/23")])
                return body, STAMP
        raise AssertionError(url)
    return read


@pytest.mark.parametrize("name,expected", [
    ("tw_index", ["36811.89", "778.60", "1113743193221"]),
    ("otc_index", ["270.9", "7.59", "162025173000"]),
    ("tw_institution", ["-19001143162", "-4154927586", "-28947879995", "-52103950743"]),
    ("otc_institution", ["64548922", "-6588416392", "10883370910", "4359503440"]),
    ("tw_margin", ["8530233", "172957", "433807523"]),
    ("otc_margin", ["1868098", "21933", "127812348"]),
])
def test_official_exchange_totals(name, expected):
    rows = market.parse_exchange(name, fixture(name))
    assert rows[DAY] == tuple(map(market.number, expected))


def test_futures_reads_open_interest_not_turnover():
    rows = market.parse_futures(fixture("tx_oi"))
    assert rows[DAY] == (4472, 3154, 1318, 97312, 3747, 93565, 14599, 118031, -103432)


@pytest.mark.parametrize("name,value", list(zip(market.FRED, ("6910.39", "35.89", "4.92", "3.88", "32.9700"))))
def test_fred_real_observations(name, value):
    rows = market.parse_fred(name, fixture(name))
    assert rows[dt.date(2026, 11, 20)] == (market.number(value),)


def read_status(out):
    with (out / "status.csv").open() as f:
        return {r["source"]: r for r in csv.DictReader(f)}


@pytest.mark.parametrize("fault", ["empty", "changed_header", "wrong_day"])
def test_bad_daily_table_preserves_previous_file_and_fails(tmp_path, fault):
    assert market.daily(tmp_path, NOW, getter()) == 0
    path = tmp_path / "tw_institution.csv"
    previous = path.read_bytes()
    payload = json.loads(fixture("tw_institution"))
    if fault == "empty":
        payload["data"] = []
    elif fault == "changed_header":
        payload["fields"][-1] = "新欄名"
    else:
        payload["date"] = "20261120"
    assert market.daily(tmp_path, NOW, getter({"tw_institution": json.dumps(payload).encode()})) == 1
    status = read_status(tmp_path)["tw_institution"]
    assert status["result"] == "FAIL" and status["error"]
    assert (status["fresh"], status["stale_kept"]) == ("no", "yes")
    assert status["data_date"] == "2026-11-23"
    assert path.read_bytes() == previous
    assert "FAIL" in (tmp_path / "freshness.csv").read_text()


def test_stale_fred_is_independent_of_taiwan_sessions(tmp_path):
    body = fixture("SP500").split(b"2026-11-19")[0]
    assert market.daily(tmp_path, NOW, getter({"SP500": body})) == 1
    s = read_status(tmp_path)["SP500"]
    assert (s["result"], s["observed_date"], s["expected_date"]) == ("STALE", "2026-11-18", "2026-11-20")
    assert "STALE" in (tmp_path / "freshness.csv").read_text()
    assert (tmp_path / "SP500.csv").exists()


def test_consensus_holiday_requires_fresh_responses_from_every_tw_source(tmp_path, monkeypatch):
    for name in market.FRED:
        assert market.expected_date(name, NOW) < DAY
    expected = market.expected_date
    monkeypatch.setattr(market, "expected_date", lambda name, now:
                        expected(name, NOW) if name in market.FRED else DAY + dt.timedelta(days=1))
    changes = {}
    for name in market.INDEX:
        p = json.loads(fixture(name))
        t = p.get("tables", [p])[0]
        t["data"] = [row for row in t["data"] if row[0] != "115/11/24"]
        changes[name] = json.dumps(p).encode()
    assert market.daily(tmp_path, NOW, getter(changes)) == 0
    assert "HOLIDAY_SUSPECT" in (tmp_path / "freshness.csv").read_text()
    changes["tx_oi"] = fixture("tx_oi").splitlines()[0]
    assert market.daily(tmp_path, NOW, getter(changes)) == 1
    assert read_status(tmp_path)["tx_oi"]["result"] == "FAIL"


def test_fred_missing_observation_is_not_carried_forward():
    body = fixture("SP500") + b"2026-11-23,.\n"
    assert DAY not in market.parse_fred("SP500", body)
    with pytest.raises(ValueError):
        market.parse_fred("SP500", body.replace(b"SP500", b"renamed"))


def test_unbalanced_futures_groups_are_rejected():
    with pytest.raises(ValueError, match="不完整"):
        market.parse_futures(b"\n".join(fixture("tx_oi").splitlines()[:-1]))


def test_backfill_merges_observed_dates_and_preserves_old_file_on_source_failure(tmp_path):
    start = dt.date(2026, 11, 20)
    # The daily tables were captured on the 23rd. Returning them for the 20th must fail.
    assert market.daily(tmp_path, NOW, getter()) == 0
    price_file = tmp_path / "tw_institution.csv"
    before = price_file.read_bytes()
    problems = market.backfill(tmp_path, start, DAY, getter(), delay=0)
    assert "tw_institution" in problems
    assert price_file.read_bytes() == before
    assert market.daily(tmp_path, NOW, getter(), history_problems=problems) == 1
    status = read_status(tmp_path)["tw_institution"]
    assert status["fresh"] == "no" and "回補失敗" in status["error"]

@pytest.mark.parametrize("day", [24,25,26,27])
def test_R5_lagged_observation_saved(tmp_path,day):
    now=NOW.replace(day=day,hour=18,minute=40)
    market.daily(tmp_path,now,getter())
    assert (tmp_path/'SP500.csv').exists()
    if day==24:
        assert read_status(tmp_path)['SP500']['result']=='NORMAL_LAG'
    if day==27:
        assert read_status(tmp_path)['SP500']['expected_date']=='2026-11-25'

def test_R6_single_day_futures(tmp_path):
    market.daily(tmp_path,NOW,getter())
    url=read_status(tmp_path)['tx_oi']['source_url']
    assert 'queryStartDate=2026/11/23' in url

def test_R7_pending_margin(tmp_path):
    market.daily(tmp_path,NOW,getter({'tw_margin':json.dumps({'stat':'很抱歉，沒有符合條件的資料!'}).encode()}))
    assert read_status(tmp_path)['tw_margin']['result']=='WAITING'


def test_pending_margin_retried_the_following_session(tmp_path):
    pending = json.dumps({'stat':'很抱歉，沒有符合條件的資料!'}).encode()
    market.daily(tmp_path, NOW, getter({'tw_margin':pending}))
    seen = []
    def read(url):
        if 'MI_MARGN' in url:
            seen.append(url)
            p = json.loads(fixture('tw_margin'))
            if 'date=20261124' in url:
                p['date'] = '20261124'
            return json.dumps(p).encode(), STAMP
        return getter()(url)
    market.daily(tmp_path, NOW + dt.timedelta(days=1), read)
    assert len(seen) == 2
    assert set(market.read_series(tmp_path,'tw_margin')) == {DAY, DAY+dt.timedelta(days=1)}
    assert read_status(tmp_path)['tw_margin']['pending_dates'] == ''


@pytest.mark.parametrize('status',[307,429])
def test_download_stops_after_three_rate_limited_attempts(monkeypatch,status):
    import requests
    response = requests.Response()
    response.status_code = status
    calls = []
    monkeypatch.setattr(market.time, 'sleep', calls.append)
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: response)
    with pytest.raises(requests.HTTPError):
        market.download('https://wwwc.twse.com.tw/')
    assert calls == [2,5,2,10,2]


def test_friday_close_is_still_expected_over_the_weekend():
    for day in (28,29,30):
        now = NOW.replace(day=day, hour=18, minute=40)
        assert market.expected_date('SP500', now) == dt.date(2026,11,27)


def test_fred_read_timeout_recovers_to_ok(tmp_path, monkeypatch):
    import requests
    waits = []
    attempts = []
    monkeypatch.setattr(market.time, 'sleep', waits.append)
    def get(url, **kwargs):
        attempts.append(kwargs['timeout'])
        if len(attempts) == 1:
            raise requests.ReadTimeout()
        response = requests.Response()
        response.status_code = 200
        response._content = fixture('SP500')
        return response
    monkeypatch.setattr(requests, 'get', get)
    def fetch(url):
        if 'id=SP500&' in url:
            return market.download(url)
        return getter()(url)
    market.daily(tmp_path,NOW,fetch)
    assert read_status(tmp_path)['SP500']['result'] == 'OK'
    assert attempts == [(10,90), (10,90)] and 10 in waits


@pytest.mark.parametrize('limit',[0,2])
def test_trickle_is_bounded_and_isolates_307(tmp_path,monkeypatch,limit):
    import requests
    from scripts import market_sources, r6_backfill as r6
    market.daily(tmp_path,NOW,getter())
    before=read_status(tmp_path)
    calls=[]
    diag=tmp_path/'diagnosis.md'
    def open_source(name,client):
        assert limit
        def fetch(url):
            calls.append((name,url))
            if name=='tw_institution':
                resp=requests.Response()
                resp.url=url
                resp.status_code=307
                resp.headers['Location']='/notice'
                resp._content=b'official notice'
                for hook in client.hooks['response']:
                    hook(resp)
                raise requests.HTTPError(response=resp)
            return getter()(url)
        return fetch
    monkeypatch.setattr(market_sources,'TRICKLE_LIMIT',limit,raising=False)
    monkeypatch.setattr(r6,'session_getter',open_source)
    r6.trickle(tmp_path,diag)
    after=read_status(tmp_path)
    assert all(after[n]['result']==r['result'] for n,r in before.items())
    if limit:
        assert diag.exists() and 'official notice' in diag.read_text()
        assert sum(n=='tw_institution' for n,_ in calls)==1
        assert after['tw_institution']['backfill_result']=='FAIL'
        assert any(n=='tw_margin' for n,_ in calls)
        assert all(sum(n==source for n,_ in calls)<=limit for source in r6.PAGES)
        assert 'dayDate=20261102' in next(u for n,u in calls if n=='tw_institution')
    else:
        assert not calls


@pytest.mark.parametrize('timeout_type', ['ConnectTimeout', 'ReadTimeout'])
def test_exhausted_fred_retry_keeps_last_verified_file(tmp_path,monkeypatch,timeout_type):
    import requests
    market.daily(tmp_path,NOW,getter())
    path=tmp_path/'SP500.csv'
    previous=path.read_bytes()
    waits=[]
    attempts=[]
    monkeypatch.setattr(market.time,'sleep',waits.append)
    def timeout(url, **kwargs):
        attempts.append(kwargs['timeout'])
        raise getattr(requests,timeout_type)()
    monkeypatch.setattr(requests,'get',timeout)
    def fetch(url):
        return market.download(url) if 'id=SP500&' in url else getter()(url)
    assert market.daily(tmp_path,NOW,fetch)==1
    assert read_status(tmp_path)['SP500']['result']=='FAIL'
    assert attempts==[(10,90)]*3 and [s for s in waits if s!=2]==[10,20]
    assert path.read_bytes()==previous
