"""一次只處理指定來源的缺日，遇到拒絕或無法驗證的資料即停批。"""
import argparse

import requests

if __package__:
    from . import fetch_market as market
else:
    import fetch_market as market

PAGES = {
    "tw_margin": "https://wwwc.twse.com.tw/zh/trading/margin/mi-margn.html",
    "tw_institution": "https://wwwc.twse.com.tw/zh/trading/foreign/bfi82u.html",
    "tx_oi": "https://www.taifex.com.tw/cht/3/futContractsDateView",
}


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
    raise SystemExit(main())
