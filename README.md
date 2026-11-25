# jc-market-data

Public copies of official market data, refreshed by GitHub Actions:

- `data/tw/` — TWSE / TPEx daily quotes and P/E, MOPS monthly revenue (weekdays, 18:05 Taipei). `freshness.csv` says whether each day's files are current.
- `data/sec_revenue.csv` — latest-quarter revenue and net income from the SEC XBRL frames API (Mondays).

Only public market data lives here. `scripts/check_public.py` runs before every commit and blocks anything else.

## 大盤日資料

GitHub Actions 每週一至五台北 18:40 排程更新 `data/market/`。每列保留官方觀測日 `date`、來源網址 `source_url` 及抓取時間 `fetched_utc`。金額以欄名指定幣別及單位。

| 檔案（.csv） | 資料內容 |
|---|---|
| tw_index、otc_index | 加權指數、櫃買指數的收盤點位、漲跌點數及成交金額（新臺幣元） |
| tw_institution、otc_institution | 上市、上櫃的自營商、投信、外陸資與官方合計買賣超（元）。自營商包含避險，外陸資排除外資自營商 |
| tw_margin、otc_margin | 上市、上櫃的融資餘額、融券餘額及融資金額（仟元）。數量沿用官方交易單位，上櫃以張計 |
| tx_oi | 臺股期貨 TX 三類法人各自的多方、空方、多空淨未平倉口數 |
| SP500、VIXCLS | FRED 的 S&P 500 與 VIX 收盤指數 |
| DGS10、DFF | 美國十年期公債固定到期殖利率與有效聯邦基金利率（百分比） |
| DEXTAUS | 每一美元兌新臺幣元數 |
| status | 各來源的檔內最新日、本次實際觀測日、預期日、是否新鮮、保留舊檔、錯誤原因、歷史起日及列數。台灣法人、信用與期貨另列相對指數檔的缺日數 |
| freshness | 本次整體判定及異常來源 |

使用資料時先讀 `freshness.csv` 和 `status.csv`。FAIL 代表請求或解析失敗，STALE 代表觀測日落後。這兩種情況保留該來源原檔，排程以非零狀態結束。台灣各來源都成功回應且一致停在同一較早日，列為 HOLIDAY_SUSPECT；美國各序列另依紐約時區檢查。可用 `python scripts/fetch_market.py --backfill-from 2023-11-01` 依官方日期回補。各檔實際涵蓋日期、缺口及發布時差見[端點實測報告](docs/market_overview_report.md)。

2026-11-25 更新：FRED 已驗證的觀測會寫入原始資料日。NORMAL_LAG 表示在該序列容忍的發布時差內，超過才列 STALE。各序列政策與官方發布依據在 `scripts/market_sources.py`。上市信用交易官方回覆當日尚無資料會列 WAITING；未公布日列在 status.csv 的 pending_dates，下次執行會再查。當日狀態與三年歷史缺日數分開記錄。
