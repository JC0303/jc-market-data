# 官方大盤資料實測紀錄

2026-11-24 台北 16:16 實跑每日入口，退出碼為 1，整體 **FAIL**。期交所 CSV 回 HTTP 429。SP500、VIXCLS、DGS10、DFF 最新回應均停在 11/20，分別列為 STALE。DEXTAUS 依週發布，本次預期 11/20，列為 OK。失敗來源的 CSV 保留先前已驗證觀測與原抓取時間。

## 回補與最新狀態

起訖為實際落盤觀測日；「缺日」以各自市場指數檔內 742 個日期比對。期貨採上市市場日期供對照。美國序列沿用 FRED 實際發布的非空觀測，不以台灣日曆計算缺日。最後一欄是本輪實際呼叫的網址，每列資料另保留原查詢網址。

| 檔名 | 首日 | 最新日 | 列數 | 缺日 | 預期日 | 本輪結果 | 官方端點 |
|---|---|---|---:|---:|---|---|---|
| tw_index | 2023-11-01 | 2026-11-23 | 742 | — | 2026-11-23 | OK | [查詢](https://wwwc.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=20261101&response=json) |
| otc_index | 2023-11-01 | 2026-11-23 | 742 | — | 2026-11-23 | OK | [查詢](https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingIndex?date=2026/11/01&response=json) |
| tw_institution | 2023-11-23 | 2026-11-23 | 84 | 658 | 2026-11-23 | OK | [查詢](https://wwwc.twse.com.tw/rwd/zh/fund/BFI82U?dayDate=20261123&type=day&response=json) |
| otc_institution | 2023-11-01 | 2026-11-23 | 742 | 0 | 2026-11-23 | OK | [查詢](https://www.tpex.org.tw/www/zh-tw/insti/summary?date=2026/11/23&response=json) |
| tw_margin | 2023-11-23 | 2026-11-23 | 87 | 655 | 2026-11-23 | OK | [查詢](https://wwwc.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20261123&selectType=MS&response=json) |
| otc_margin | 2023-11-01 | 2026-11-23 | 742 | 0 | 2026-11-23 | OK | [查詢](https://www.tpex.org.tw/www/zh-tw/margin/balance?date=2026/11/23&response=json) |
| tx_oi | 2023-12-01 | 2026-11-23 | 660 | 82 | 2026-11-23 | FAIL | [查詢](https://www.taifex.com.tw/cht/3/futContractsDateDown?queryStartDate=2026/11/01&queryEndDate=2026/11/23&commodityId=TXF) |
| SP500 | 2023-11-01 | 2026-11-20 | 767 | — | 2026-11-23 | STALE | [查詢](https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2026-10-19) |
| VIXCLS | 2023-11-01 | 2026-11-20 | 789 | — | 2026-11-23 | STALE | [查詢](https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2026-10-19) |
| DGS10 | 2023-11-01 | 2026-11-20 | 763 | — | 2026-11-23 | STALE | [查詢](https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2026-10-19) |
| DFF | 2023-11-01 | 2026-11-20 | 1116 | — | 2026-11-22 | STALE | [查詢](https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF&cosd=2026-10-18) |
| DEXTAUS | 2023-11-01 | 2026-11-20 | 764 | — | 2026-11-20 | OK | [查詢](https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXTAUS&cosd=2026-10-16) |

## 來源與計量口徑

- 加權指數使用證交所 FMTQIK 月表。證交所 www 主機回 503，同一機構的 wwwc 主機實測回 200。櫃買日成交量值指數把表內「金額（仟元）」乘以 1,000 統一為元。兩個月表在本次抓取時已出現 11/24 一列；依既有台股程式台北 17:00 的到期邏輯，本次收錄至 11/23。
- 上市三大法人用 BFI82U，合併自營商自行買賣與避險，另列投信、外陸資（不含外資自營商）及官方合計。上櫃採櫃買中心 summary 同口徑原表。融資融券讀當日餘額及官方彙總融資金額。歷史期間上市端點多次回 HTTP 307 安全性頁面；降速重試後再次收到 307，當次停止該批回補。兩份上市檔各缺 658、655 日，日期跨度不代表連續覆蓋。
- 期交所下載使用 TXF，解析時再篩選「臺股期貨」，讀自營商、投信與外陸資多方、空方、多空淨未平倉，每組均為口數。11/02–11/23 的 CSV 成功回 200；後續請求多次回 429。期間內最早成功取得的觀測是 2023-12-01。2023-11 的整月查詢回 HTML，2026-08 至 10 月未取得，缺日揭露於表中。[成功下載樣本](https://www.taifex.com.tw/cht/3/futContractsDateDown?queryStartDate=2026%2F11%2F02&queryEndDate=2026%2F11%2F23&commodityId=TXF)
- 五個美國與匯率序列均成功讀到 FRED 的 fredgraph.csv。歷史查詢採 cosd=2023-11-01，每日重讀近期觀測以接收來源修訂。空白及點號沒有數值，保留日期缺口。預期日使用紐約時間：兩個指數與 DGS10 以 19:00 後的最近平日為基準，DFF 以 09:00 到期發布日前一曆日為基準，DEXTAUS 以週一 16:15 到期發布的前週五為基準。這些是資料檢查時間；美國假日或來源另有發布延遲時可能標示 STALE。
- 全市場外資持有比率未納入。實測證交所 MI_QFIIS_cat 回 36 個分類，櫃買 OpenAPI 回 28 個產業；兩份表都沒有全市場比率列。本次未確認免費免金鑰的全市場官方每日總數，也未將類股百分比平均。[證交所分類表](https://wwwc.twse.com.tw/rwd/zh/fund/MI_QFIIS_cat?date=20261123&response=json) · [櫃買分類表](https://www.tpex.org.tw/openapi/v1/tpex_3insti_qfii_industry)

## 驗證

- `test_official_exchange_totals` 六例核對兩個指數、法人及信用交易總額，包括仟元換算。`test_futures_reads_open_interest_not_turnover` 核對同日九個未平倉欄位。`test_fred_real_observations` 分別核對五個序列。
- `test_bad_daily_table_preserves_previous_file_and_fails` 三例將真實樣本改為空表、改欄名或錯日，逐一驗證退出碼、錯誤原因、FAIL、新鮮度以及舊檔位元組。`test_stale_fred_is_independent_of_taiwan_sessions` 驗證美國來源可單獨過期。`test_consensus_holiday_requires_fresh_responses_from_every_tw_source` 驗證疑似休市與來源錯誤的優先順序。
- `test_fred_missing_observation_is_not_carried_forward`、`test_unbalanced_futures_groups_are_rejected`、`test_backfill_merges_observed_dates_and_preserves_old_file_on_source_failure` 涵蓋缺值、缺法人與部分回補失敗。真實樣本置於 `tests/fixtures/market/`；FRED 與期貨保留原始列節錄，上櫃信用明細節錄一列並保留完整官方合計。
- 公開檔案檢查涵蓋白名單、欄位、數值、日期、UTC 時區及官方來源網址。`test_personal_column_in_an_approved_market_file_is_blocked` 驗證即使檔名獲准，額外欄位仍會被阻擋。完整 `python -m pytest -q` 實測 **24 passed**。另執行 `python scripts/check_public.py` 成功退出。
- `market.yml` 排程為 UTC 10:40（台北 18:40），即使資料失敗仍提交本輪狀態，抓取步驟保留非零退出，提交前重跑公開資料檢查。本次實測在工作分支本機執行；平日排程須在預設分支採用 workflow 後才會生效。
