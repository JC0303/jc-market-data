"""官方市場統計。每日只合併通過驗證的資料，歷史模式逐個官方回應核對。"""
import argparse
import calendar
import csv
import datetime as dt
import io
import json
import os
import tempfile
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import holidays
from functools import lru_cache

if __package__:
    from .market_sources import COLUMNS, DAILY, FRED, FRED_GRACE, INDEX, endpoint
    from .fetch_tw import TPE, expected_trading_day
else:
    from market_sources import COLUMNS, DAILY, FRED, FRED_GRACE, INDEX, endpoint
    from fetch_tw import TPE, expected_trading_day

OUT = Path(__file__).resolve().parents[1] / "data/market"
STATUS = ("source", "result", "data_date", "observed_date", "expected_date", "fresh", "stale_kept",
          "source_url", "fetched_utc", "error", "history_start", "history_rows", "missing_tw_sessions", "pending_dates")


def number(value):
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"數值欄無效 {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"非有限數值 {value!r}")
    return result


def table_rows(fields, records, required):
    if not records or not fields or len(set(fields)) != len(fields) or set(required) - set(fields):
        raise ValueError(f"空表或缺少必要欄位 {sorted(set(required) - set(fields or []))}")
    return [dict(zip(fields, row, strict=True)) for row in records]


def roc_day(s):
    y, m, d = map(int, s.split("/"))
    return dt.date(y + 1911, m, d)


def insert(rows, day, values):
    if day in rows:
        raise ValueError(f"重複觀測 {day}")
    rows[day] = tuple(number(v) for v in values)


def parse_indices(name, table):
    otc = name == "otc_index"
    close, change, amount = (("櫃買指數", "漲/跌", "金額（仟元）") if otc else
                             ("發行量加權股價指數", "漲跌點數", "成交金額"))
    rows = {}
    for row in table_rows(table["fields"], table["data"], ("日期", close, change, amount)):
        insert(rows, roc_day(row["日期"]), (row[close], row[change], number(row[amount]) * (1000 if otc else 1)))
    return rows


def categories(table, key, column):
    rows = table_rows(table["fields"], table["data"], (key, column))
    values = {r[key].strip(): number(r[column]) for r in rows}
    if len(rows) != len(values):
        raise ValueError("分類重複")
    return values


def institutions(name, table):
    if name == "tw_institution":
        v = categories(table, "單位名稱", "買賣差額")
        return (v["自營商(自行買賣)"] + v["自營商(避險)"], v["投信"],
                v["外資及陸資(不含外資自營商)"], v["合計"])
    v = categories(table, "單位名稱", "買賣超(元)")
    # 自營商合計已包含外資自營商，三類並列時排除重複。
    return v["自營商合計"], v["投信"], v["外資及陸資(不含自營商)"], v["三大法人合計*"]


def margin(name, table):
    if name == "tw_margin":
        v = categories(table, "項目", "今日餘額")
        return v["融資(交易單位)"], v["融券(交易單位)"], v["融資金額(仟元)"]
    if not table["data"]:
        raise ValueError("上櫃融資融券回空表")
    rows = table_rows(table["fields"], table["summary"], ("名稱", "資餘額", "券餘額"))
    totals = {r["名稱"]: r for r in rows}
    if len(totals) != len(rows):
        raise ValueError("融資融券合計列重複")
    return totals["合計(張)"]["資餘額"], totals["合計(張)"]["券餘額"], totals["融資金(仟元)"]["資餘額"]


def parse_exchange(name, body):
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("交易所未回傳資料表物件")
    if str(payload.get("stat", "")).lower() != "ok":
        raise ValueError(f"交易所狀態 {payload.get('stat')}")
    table = payload["tables"][0] if "tables" in payload else payload
    if name in INDEX:
        return parse_indices(name, table)
    day = dt.datetime.strptime(payload["date"], "%Y%m%d").date()
    if name.startswith("otc_") and roc_day(table["date"]) != day:
        raise ValueError("回應日期與表格日期不符")
    values = institutions(name, table) if name.endswith("institution") else margin(name, table)
    return {day: tuple(number(v) for v in values)}


def parse_futures(body):
    fields = ("多方未平倉口數", "空方未平倉口數", "多空未平倉口數淨額")
    reader = csv.DictReader(io.StringIO(body.decode("cp950")))
    if set(("日期", "商品名稱", "身份別", *fields)) - set(reader.fieldnames or ()):
        raise ValueError("期貨 CSV 缺少必要欄位")
    days = {}
    for row in reader:
        if row["商品名稱"] != "臺股期貨":
            continue
        day = dt.datetime.strptime(row["日期"], "%Y/%m/%d").date()
        groups = days.setdefault(day, {})
        group = row["身份別"]
        if group in groups:
            raise ValueError(f"{day} 法人重複 {group}")
        groups[group] = tuple(number(row[field]) for field in fields)
    rows = {}
    for day, groups in days.items():
        labels = ("自營商", "投信", "外資及陸資")
        if set(groups) != set(labels):
            raise ValueError(f"{day} 三大法人不完整")
        rows[day] = sum((groups[label] for label in labels), ())
    if not rows:
        raise ValueError("臺股期貨回空表")
    return rows


def parse_fred(name, body):
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if reader.fieldnames != ["observation_date", name]:
        raise ValueError(f"FRED 欄名異常 {reader.fieldnames}")
    rows = {}
    for row in reader:
        if None in row or row[name] is None:
            raise ValueError("FRED CSV 欄數異常")
        day = dt.date.fromisoformat(row["observation_date"])
        if row[name] not in ("", "."):
            insert(rows, day, (row[name],))
    if not rows:
        raise ValueError("FRED 回空表或全部缺值")
    return rows


def utc_stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def download(url, client=requests, headers=None):
    for attempt in range(3):
        time.sleep(2)
        response = client.get(url, timeout=(10, 35), allow_redirects=False,
                              headers=headers or {"User-Agent": "jc-market-data public research"})
        if response.status_code not in (307, 429) or attempt == 2:
            break
        wait = response.headers.get("Retry-After", "")
        if wait and (not wait.isdigit() or int(wait) > 120):
            break
        time.sleep(max(5 * 2 ** attempt, int(wait or 0)))
    if response.status_code != 200:
        raise requests.HTTPError(f"HTTP {response.status_code} at {url}", response=response)
    return response.content, utc_stamp()


def observations(name, start, end, getter=download):
    url = endpoint(name, start, end)
    body, stamp = getter(url)
    if name in FRED:
        rows = parse_fred(name, body)
    elif name == "tx_oi":
        rows = parse_futures(body)
    else:
        rows = parse_exchange(name, body)
    if name in DAILY and set(rows) != {start}:
        raise ValueError(f"要求 {start}，官方表日期 {sorted(rows)}")
    if name in INDEX and any(day.replace(day=1) != start.replace(day=1) for day in rows):
        raise ValueError(f"指數月份不符 {start:%Y-%m}")
    if name == "tx_oi" and any(not start <= day <= end for day in rows):
        raise ValueError("未平倉資料超出查詢區間")
    return {day: dict(date=day.isoformat(), **dict(zip(COLUMNS[name], vals, strict=True)),
                      source_url=url, fetched_utc=stamp)
            for day, vals in rows.items() if start <= day <= end}


@lru_cache(maxsize=16)
def closures(name, year):
    if name in ("SP500", "VIXCLS"):
        return holidays.financial_holidays("NYSE", years=year)
    # Federal Reserve Banks remain open Friday before a Saturday holiday.
    return {d for d in holidays.US(years=year) if not (
        d.weekday() == 4 and "observed" in holidays.US(years=year)[d].lower())}


def us_business(name, day):
    return day.weekday() < 5 and day not in closures(name, day.year)


def prior_session(name, day):
    while not us_business(name, day):
        day -= dt.timedelta(days=1)
    return day


def expected_date(name, now):
    if name not in FRED:
        return expected_trading_day(now.astimezone(TPE))
    ny = now.astimezone(ZoneInfo("America/New_York"))
    cutoff = {"DFF": dt.time(9), "DEXTAUS": dt.time(16, 15)}.get(name, dt.time(19))
    day = ny.date() - dt.timedelta(days=ny.time() < cutoff)
    release = prior_session(name, day)
    if name == "DEXTAUS":
        monday = release - dt.timedelta(days=release.weekday())
        return prior_session(name, monday - dt.timedelta(days=1))
    if name == "DFF":
        return release - dt.timedelta(days=1)
    return release


def tolerated_date(name, now):
    local = now.astimezone(ZoneInfo("America/New_York"))
    day = local.date()
    for _ in range(FRED_GRACE[name]):
        day = prior_session(name, day - dt.timedelta(days=1))
    return expected_date(name, dt.datetime.combine(day, local.time(), local.tzinfo))


def read_series(out, name):
    path = out / f"{name}.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {dt.date.fromisoformat(r["date"]): r for r in csv.DictReader(f)}


def write_csv(path, fields, rows):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8",
                                     newline="", delete=False) as handle:
        tmp = Path(handle.name)
        try:
            w = csv.DictWriter(handle, fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    os.replace(tmp, path)


def save_series(out, name, rows, new):
    rows.update(new)
    write_csv(out / f"{name}.csv", ("date", *COLUMNS[name], "source_url", "fetched_utc"),
              (rows[d] for d in sorted(rows)))


def daily(out, now, getter=download, history_problems=None):
    out.mkdir(parents=True, exist_ok=True)
    pending = set()
    if (out / "status.csv").exists():
        with (out / "status.csv").open() as handle:
            for row in csv.DictReader(handle):
                if row["source"] == "tw_margin":
                    pending.update(dt.date.fromisoformat(d) for d in row.get("pending_dates", "").split() if d)
    status, index_days = {}, {}
    for name in COLUMNS:
        expected = expected_date(name, now)
        start = expected.replace(day=1)
        if name in FRED:
            start = expected - dt.timedelta(days=35)
        elif name in (*DAILY, "tx_oi"):
            start = index_days.get("tw" if name == "tx_oi" else name.split("_")[0], expected)
        path = out / f"{name}.csv"
        old = read_series(out, name)
        r = status[name] = dict(source=name, result="FAIL", data_date=max(old, default=""),
                                observed_date="", expected_date=expected, fresh="no",
                                stale_kept="yes" if path.exists() else "no",
                                source_url=endpoint(name, start, expected), fetched_utc=utc_stamp(), error="")
        if history_problems and name in history_problems:
            errors = history_problems[name]
            r["error"] = f"回補失敗 {len(errors)} 個請求；首筆 {errors[0]}"
            continue
        retry_errors = []
        if name == "tw_margin":
            for day in sorted(d for d in pending if d < expected):
                try:
                    recovered = observations(name, day, day, getter)
                    save_series(out, name, old, recovered)
                    pending.remove(day)
                except (ValueError, KeyError, TypeError, IndexError, AttributeError, csv.Error, requests.RequestException) as exc:
                    retry_errors.append(f"{day}: {exc}")
        try:
            end = now.astimezone(ZoneInfo("America/New_York")).date() if name in FRED else expected
            new = observations(name, start, end, getter)
            if not new:
                raise ValueError("指定區間回空表")
            latest = max(new)
            r.update(observed_date=latest, fetched_utc=new[latest]["fetched_utc"])
            if name in INDEX:
                index_days[name.split("_")[0]] = latest
            if name in FRED:
                save_series(out, name, old, new)
                r.update(data_date=max(old), stale_kept="no")
                if latest < expected:
                    result = "NORMAL_LAG" if latest >= tolerated_date(name, now) else "STALE"
                    r.update(result=result, error=f"最新觀測 {latest}，預期 {expected}")
                else:
                    r.update(result="OK", fresh="yes")
                continue
            if latest != expected:
                r.update(result="STALE", error=f"最新觀測 {latest}，預期 {expected}")
                continue
            save_series(out, name, old, new)
            r.update(result="OK", data_date=latest, fresh="yes", stale_kept="no")
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, csv.Error, requests.RequestException) as exc:
            r["error"] = f"{type(exc).__name__}: {exc}"
            if (name == "tw_margin" and start == expected == now.astimezone(TPE).date()
                    and str(exc).rstrip("!！") == "交易所狀態 很抱歉，沒有符合條件的資料"):
                pending.add(expected)
                r.update(result="WAITING", error="證交所尚未發布當日餘額")
        if name == "tw_margin":
            if r["result"] == "OK":
                pending.discard(expected)
            if retry_errors:
                if r["result"] in ("OK", "WAITING"):
                    r.update(result="STALE", fresh="no")
                r["error"] += " 補抓未完成 " + " / ".join(retry_errors)
            r["pending_dates"] = " ".join(map(str, sorted(pending)))
            r["data_date"] = max(old, default="")
    tw = [status[n] for n in COLUMNS if n not in FRED]
    holiday = all(r["result"] == "STALE" for r in tw) and len({r["observed_date"] for r in tw}) == 1
    if holiday:
        for r in tw:
            r["result"] = "HOLIDAY_SUSPECT"
    results = {r["result"] for r in status.values()}
    verdict = next(v for v in ("FAIL", "STALE", "HOLIDAY_SUSPECT", "OK") if v in results or v == "OK")
    calendars = {n: read_series(out, n).keys() for n in INDEX}
    for name, r in status.items():
        dates = read_series(out, name).keys()
        missing = ""
        if name in (*DAILY, "tx_oi"):
            calendar_name = "otc_index" if name.startswith("otc_") else "tw_index"
            if calendars[calendar_name]:
                missing = len(calendars[calendar_name] - dates)
        r.update(history_start=min(dates, default=""), history_rows=len(dates), missing_tw_sessions=missing)
    write_csv(out / "status.csv", STATUS, status.values())
    issues = " / ".join(f"{n}={r['result']}" for n, r in status.items() if r["result"] != "OK")
    write_csv(out / "freshness.csv", ("checked_utc", "verdict", "note"),
              [dict(checked_utc=utc_stamp(), verdict=verdict, note=issues)])
    print(verdict, issues)
    return 0 if verdict in ("OK", "HOLIDAY_SUSPECT") else 1


def months(start, end):
    first = start.replace(day=1)
    while first <= end:
        last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
        yield first, min(last, end)
        first = last + dt.timedelta(days=1)


def backfill(out, start, end, getter=download, delay=1):
    """回補只合併可核對日期的觀測。後續執行只請求仍有缺口的交易日。"""
    out.mkdir(parents=True, exist_ok=True)
    history = {name: read_series(out, name) for name in COLUMNS}
    problems = {}
    blocked = set()

    def ingest(name, first, last):
        try:
            new = observations(name, first, last, getter)
            if not new:
                raise ValueError("指定區間回空表")
            history[name].update({d: r for d, r in new.items() if start <= d <= end})
        except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, AttributeError, csv.Error) as exc:
            problems.setdefault(name, []).append(f"{first}..{last} {exc}")
            if isinstance(exc, requests.HTTPError) and exc.response.status_code in (307, 403, 429):
                blocked.add(name)
        finally:
            if delay:
                time.sleep(delay)

    for name in FRED:
        ingest(name, start, end)
    for first, last in months(start, end):
        for name in (*INDEX, "tx_oi"):
            if name not in blocked:
                ingest(name, max(start, first) if name == "tx_oi" else first, last)
    for name in DAILY:
        sessions = history[name.split("_")[0] + "_index"]
        for day in sorted(sessions.keys() - history[name].keys()):
            if name in blocked:
                break
            if start <= day <= end:
                ingest(name, day, day)
    for name, series in history.items():
        if series:
            save_series(out, name, series, {})
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill-from", type=dt.date.fromisoformat, help="以 YYYY-MM-DD 指定歷史回補起點")
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    problems = {}
    if args.backfill_from:
        end = expected_date("tw_index", now)
        if args.backfill_from > end:
            parser.error("歷史起點晚於預期交易日")
        problems = backfill(OUT, args.backfill_from, end)
        now = dt.datetime.now(dt.timezone.utc)
    return daily(OUT, now, history_problems=problems)


if __name__ == "__main__":
    raise SystemExit(main())
