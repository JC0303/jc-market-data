"""一次只處理指定來源的缺日，遇到拒絕或無法驗證的資料即停批。"""
import time

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
        for attempt in range(3):
            time.sleep(2)
            response = client.get(url, headers={"Referer": page}, allow_redirects=False, timeout=(10, 35))
            if response.status_code == 200:
                return response.content, market.utc_stamp()
            if response.status_code not in (307, 429) or attempt == 2:
                break
            wait = response.headers.get("Retry-After", "")
            if wait and (not wait.isdigit() or int(wait) > 120):
                break
            time.sleep(max(5 * 2 ** attempt, int(wait or 0)))
        raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
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
