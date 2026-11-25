"""一次只處理指定來源的缺日，遇到拒絕或無法驗證的資料即停批。"""
import argparse
import csv
import sys
from pathlib import Path

import requests

if __package__:
    from . import market_sources
    from . import fetch_market as market
else:
    import market_sources
    import fetch_market as market

PAGES = {
    "tw_margin": "https://wwwc.twse.com.tw/zh/trading/margin/mi-margn.html",
    "tw_institution": "https://wwwc.twse.com.tw/zh/trading/foreign/bfi82u.html",
    "tx_oi": "https://www.taifex.com.tw/cht/3/futContractsDateView",
}


def diagnostic_hook(path):
    recorded = False

    def capture(response, **kwargs):
        nonlocal recorded
        if recorded or response.status_code not in (307, 429):
            return
        recorded = True
        raw = getattr(response.raw, "headers", None)
        headers = raw or response.headers
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            print(f"\n## 首次 HTTP {response.status_code}\n\n{market.utc_stamp()} GET {response.url}", file=handle)
            print(f"Location = {response.headers.get('Location', '（無）')}\n", file=handle)
            for key in headers:
                values = raw.getlist(key) if raw else [headers[key]]
                for value in values:
                    if key.lower() == "set-cookie":
                        value = "[公開版遮蔽工作階段值]"
                    print(f"    {key}: {value}", file=handle)
            print("\n~~~~", response.content[:2048].decode("utf-8", "backslashreplace"),
                  "~~~~", sep="\n", file=handle)
    return capture


def session_getter(name, client):
    page = PAGES[name]
    client.headers.update({"User-Agent": "jc-market-data/1.0 (public market research)"})
    response = client.get(page, allow_redirects=False, timeout=(10, 35))
    if response.status_code != 200:
        raise requests.HTTPError(f"首頁 HTTP {response.status_code}", response=response)

    def get(url):
        return market.download(url, client=client, headers={"Referer": page})
    return get


def collect(name, days, out, getter):
    archive = market.read_series(out, name)
    results = []
    for day in days:
        if day in archive:
            continue
        try:
            new = market.observations(name, day, day, getter)
            if set(new) != {day}:
                raise ValueError("官方回應沒有指定交易日")
        except requests.HTTPError as exc:
            results.append((day, exc.response.status_code, str(exc)))
            break
        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as exc:
            results.append((day, None, str(exc)))
            break
        market.save_series(out, name, archive, new)
        results.append((day, 200, "OK"))
    return results

def trickle(out, diagnostic_path):
    with (out / "status.csv").open(encoding="utf-8", newline="") as handle:
        status = list(csv.DictReader(handle))
    calendar = market.read_series(out, "tw_index").keys()
    for row in status:
        name = row["source"]
        if name not in PAGES:
            continue
        old = market.read_series(out, name)
        dates = sorted(calendar - old.keys())[:market_sources.TRICKLE_LIMIT]
        added = attempted = 0
        errors = []
        if dates:
            capture = diagnostic_hook(diagnostic_path)

            def stop_on_block(response, **kwargs):
                if response.status_code in (307, 429):
                    capture(response)
                    response.close()
                    raise requests.HTTPError(f"HTTP {response.status_code} {response.url}", response=response)

            with requests.Session() as client:
                client.hooks["response"].append(stop_on_block)
                try:
                    getter = session_getter(name, client)
                    for day in dates:
                        attempted += 1
                        try:
                            new = market.observations(name, day, day, getter)
                            if set(new) != {day}:
                                raise ValueError("資料日期不符或無觀測")
                            market.save_series(out, name, old, new)
                            added += 1
                        except (ValueError, KeyError, IndexError, TypeError, csv.Error) as exc:
                            errors.append(f"{day}: {exc}")
                except requests.RequestException as exc:
                    errors.append(str(exc))
        result = "DISABLED" if market_sources.TRICKLE_LIMIT == 0 else "OK"
        row.update(backfill_result="FAIL" if errors else result,
                   backfill_attempted=attempted, backfill_added=added, backfill_error=" / ".join(errors),
                   history_rows=len(old), history_start=min(old, default=""),
                   missing_tw_sessions=len(calendar - old.keys()))
        print(name, row["backfill_result"], f"{added}/{attempted}", row["backfill_error"], flush=True)
    market.write_csv(out / "status.csv", market.STATUS, status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=PAGES)
    parser.add_argument("--expand", action="store_true", help="十日全部驗證成功後繼續同一批次")
    args = parser.parse_args()
    dates = market.read_series(market.OUT, "tw_index").keys()
    missing = sorted(dates - market.read_series(market.OUT, args.source).keys())
    if not missing:
        return 0
    with requests.Session() as client:
        client.hooks["response"].append(diagnostic_hook(Path("results/r6_307_diagnosis.md")))
        getter = session_getter(args.source, client)
        sample = collect(args.source, missing[:10], market.OUT, getter)
        for result in sample:
            print(*result, flush=True)
        if any(status != 200 for _, status, _ in sample):
            return 1
        if len(sample) == 10 and args.expand:
            for day, status, detail in collect(args.source, missing[10:], market.OUT, getter):
                print(day, status, detail, flush=True)
                if status != 200:
                    return 1
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--trickle"]:
        trickle(market.OUT, Path("results/r6_307_diagnosis.md"))
    else:
        raise SystemExit(main())
