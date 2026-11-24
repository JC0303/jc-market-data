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
                return changes.get(name, fixture(name)), STAMP
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
    body = fixture("SP500").split(b"2026-11-20")[0]
    assert market.daily(tmp_path, NOW, getter({"SP500": body})) == 1
    s = read_status(tmp_path)["SP500"]
    assert (s["result"], s["observed_date"], s["expected_date"]) == ("STALE", "2026-11-19", "2026-11-20")
    assert "STALE" in (tmp_path / "freshness.csv").read_text()
    assert not (tmp_path / "SP500.csv").exists()


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
