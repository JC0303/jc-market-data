"""TAIFEX only serves the last three years of the institutional futures table.

Seen 2026-11-25: the tx_oi trickle backfill spent 17 of its 19 daily attempts
on 2023-11-01..23, which TAIFEX no longer serves (it answers with a non-CSV
page, hence "'cp950' codec can't decode byte 0xe6"). Missing days are tried
oldest-first, so these dead dates came first every day, forever, and newer
gaps waited behind them. The dates stay counted as missing; they are just not
re-requested.
"""
import datetime as dt

import pytest

from scripts import fetch_market as market
from scripts import r6_backfill as r6
from scripts import market_sources


def _row(day, name):
    return dict(date=day.isoformat(), **dict.fromkeys(market_sources.COLUMNS[name], "1"),
                source_url="test", fetched_utc="test")


def test_trickle_skips_dates_taifex_no_longer_serves(tmp_path, monkeypatch):
    today = dt.date.today()
    dead = [today - dt.timedelta(days=4 * 365 + i) for i in range(3)]
    live = today - dt.timedelta(days=10)
    calendar = {d: _row(d, "tw_index") for d in (*dead, live)}
    market.save_series(tmp_path, "tw_index", {}, calendar)
    market.write_csv(tmp_path / "status.csv", market.STATUS, [dict(source="tx_oi")])

    asked = []

    def observations(name, start, end, getter):
        asked.append(start)
        if start in dead:
            raise ValueError("'cp950' codec can't decode byte 0xe6 in position 471")
        return {start: _row(start, name)}

    monkeypatch.setattr(r6, "session_getter", lambda name, client: (lambda url: None))
    monkeypatch.setattr(market, "observations", observations)
    r6.trickle(tmp_path, tmp_path / "diag.md")

    assert not set(asked) & set(dead)
    assert live in market.read_series(tmp_path, "tx_oi")
    with (tmp_path / "status.csv").open(encoding="utf-8") as handle:
        text = handle.read()
    assert "OK" in text and "FAIL" not in text
    assert "三年" in text  # the skipped dates are reported, not hidden


def test_non_csv_futures_reply_says_so():
    page = "<html>查詢日期超出範圍</html>".encode("utf-8")
    with pytest.raises(ValueError, match="不是 CSV"):
        market.parse_futures(page)
