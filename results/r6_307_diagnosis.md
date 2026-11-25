# R6 上市信用交易單次診斷

2026-11-25T01:33:34.477914+00:00

GET https://wwwc.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20231101&selectType=MS&response=json

HTTP 200，Location = （無）。回應共 1849 bytes。

    server: envoy
    date: Wed, 25 Nov 2026 01:33:33 GMT
    content-type: application/json;charset=UTF-8
    x-application-context: application:production
    set-cookie: [公開版遮蔽工作階段值]
    vary: accept-encoding
    content-encoding: gzip
    content-security-policy: frame-ancestors 'self' *.twse.com.tw *.tdcc.com.tw http://digitalprocesssyst-epassbook.cdn.hinet.net digitalprocesssys-epassbook.cdn.hinet.net;
    x-content-type-options: nosniff
    referrer-policy: strict-origin-when-cross-origin
    permissions-policy: camera=(),microphone=(),geolocation=(),sync-xhr=*,gyroscope=()
    strict-transport-security: max-age=31536000; includeSubDomains; preload
    access-control-allow-origin: *
    x-envoy-upstream-service-time: 3339
    transfer-encoding: chunked

回應本文前 2,048 bytes（短於此長度則完整保留）

~~~~
{"stat":"OK","date":"20231101","tables":[{"title":"112年11月01日 信用交易統計","fields":["項目","買進","賣出","現金(券)償還","前日餘額","今日餘額"],"data":[["融資(交易單位)","163,679","159,865","33,536","7,519,942","7,490,220"],["融券(交易單位)","22,520","25,399","2,636","324,321","324,564"],["融資金額(仟元)","6,821,881","5,906,402","392,658","223,458,771","223,981,592"]],"notes":["本公司市場融資融券餘額的資料來源係為各授信機構(含證金公司及自辦信用交易證券商)，待各授信機構整體作業結束且傳輸完成，復經本公司彙整後於當日晚間即時公布於本公司網站。前述作業程序或因當日市場成交量值多寡，或因各授信機構傳輸過程順遂與否、更帳次數及作業時間長短等因素，均將影響本公司完成本表時間。","由於各授信機構於該信用交易成交的次日，仍繼續處理相關調帳作業，本公司待各授信機構整體作業結束且傳輸最終正確餘額數字完成後，始完整揭露於『前日餘額』欄位中，故請以『前日餘額』為準，而以『今日餘額』為輔助參考資料。","遇上櫃證券轉上市，且得為融資融券交易時，本報表於該證券上市交易日即列入信用交易資訊，並將該證券之融資融券餘額列計後，調整當日報表『前日餘額』之統計數字；該證券融資融券餘額，請參閱本公司MIS即時公告。","當日如有臨時新增之變更交易有價證券標的，網頁右上角會呈現點選框，屆時請點選明細查詢，另外，歷史資料也可點選此 <a href='/zh/trading/bfihbu.html' target='_blank'>連結<\u002fa> 查詢。當日臨時新增之變更交易有價證券，若該證券原得為融資融券交易，將被暫停融資融券。"]},{}]}
~~~~

單次重查回 200。這筆紀錄無法確認先前 307 的成因。

## 官方批次查詢實測

- [fund/BFI82U?type=month&monthDate=20231101](https://wwwc.twse.com.tw/rwd/zh/fund/BFI82U?type=month&monthDate=20231101&response=json)，HTTP 200，日期 20231101，標題 112年11月01日至112年11月30日 三大法人買賣金額統計表，欄位 ['單位名稱', '買進金額', '賣出金額', '買賣差額']，首列 ['自營商(自行買賣)', '79,997,988,322', '79,785,952,876', '212,035,446']。

- [marginTrading/MI_MARGN?date=20231101&startDate=20231101&endDate=20231130&selectType=MS](https://wwwc.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20231101&startDate=20231101&endDate=20231130&selectType=MS&response=json)，HTTP 200，日期 20231101，標題 112年11月01日 信用交易統計，欄位 ['項目', '買進', '賣出', '現金(券)償還', '前日餘額', '今日餘額']，首列 ['融資(交易單位)', '163,679', '159,865', '33,536', '7,519,942', '7,490,220']。

BFI82U 官網列有日、週、月報；月報按法人分類彙總。MI_MARGN 的區間參數未取得逐日批次表。網路資訊商店另提供訂購，未列入本次免費來源。

證交所融資融券查詢表只有查詢日期與分類欄位。網頁說明當日餘額須待各授信機構傳輸完成後公布。本文比對同日官方數值；月合計與次日的前日餘額均未用來填補缺日。[融資融券官方表單](https://www.twse.com.tw/zh/trading/margin/mi-margn.html) · [三大法人官方表單](https://wwwc.twse.com.tw/zh/trading/foreign/bfi82u.html)

## 手動工作流程結果

2026-11-25 手動啟動公開 main 的 market.yml，七項台灣來源 OK。SP500、VIXCLS、DGS10、DFF、DEXTAUS 讀取逾時，均為 FAIL 並保留舊檔；run 標紅，狀態提交成功。[Actions](https://github.com/JC0303/jc-market-data/actions/runs/45526540767) · [逐來源狀態](https://github.com/JC0303/jc-market-data/blob/d1aa823/data/market/status.csv)

## 擴大回補停批日的單次診斷

GET https://wwwc.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20240606&selectType=MS&response=json

HTTP 200；Location = （無）。本文大小 1850 bytes。

    server: envoy
    date: Wed, 25 Nov 2026 01:42:17 GMT
    content-type: application/json;charset=UTF-8
    x-application-context: application:production
    set-cookie: [公開版遮蔽工作階段值]
    vary: accept-encoding
    content-encoding: gzip
    content-security-policy: frame-ancestors 'self' *.twse.com.tw *.tdcc.com.tw http://digitalprocesssyst-epassbook.cdn.hinet.net digitalprocesssys-epassbook.cdn.hinet.net;
    x-content-type-options: nosniff
    referrer-policy: strict-origin-when-cross-origin
    permissions-policy: camera=(),microphone=(),geolocation=(),sync-xhr=*,gyroscope=()
    strict-transport-security: max-age=31536000; includeSubDomains; preload
    access-control-allow-origin: *
    x-envoy-upstream-service-time: 1755
    transfer-encoding: chunked

~~~~
{"stat":"OK","date":"20240606","tables":[{"title":"113年06月06日 信用交易統計","fields":["項目","買進","賣出","現金(券)償還","前日餘額","今日餘額"],"data":[["融資(交易單位)","412,063","337,368","5,695","8,779,475","8,848,475"],["融券(交易單位)","22,337","19,629","4,669","265,031","257,654"],["融資金額(仟元)","17,490,176","16,037,457","188,083","302,355,018","303,619,654"]],"notes":["本公司市場融資融券餘額的資料來源係為各授信機構(含證金公司及自辦信用交易證券商)，待各授信機構整體作業結束且傳輸完成，復經本公司彙整後於當日晚間即時公布於本公司網站。前述作業程序或因當日市場成交量值多寡，或因各授信機構傳輸過程順遂與否、更帳次數及作業時間長短等因素，均將影響本公司完成本表時間。","由於各授信機構於該信用交易成交的次日，仍繼續處理相關調帳作業，本公司待各授信機構整體作業結束且傳輸最終正確餘額數字完成後，始完整揭露於『前日餘額』欄位中，故請以『前日餘額』為準，而以『今日餘額』為輔助參考資料。","遇上櫃證券轉上市，且得為融資融券交易時，本報表於該證券上市交易日即列入信用交易資訊，並將該證券之融資融券餘額列計後，調整當日報表『前日餘額』之統計數字；該證券融資融券餘額，請參閱本公司MIS即時公告。","當日如有臨時新增之變更交易有價證券標的，網頁右上角會呈現點選框，屆時請點選明細查詢，另外，歷史資料也可點選此 <a href='/zh/trading/bfihbu.html' target='_blank'>連結<\u002fa> 查詢。當日臨時新增之變更交易有價證券，若該證券原得為融資融券交易，將被暫停融資融券。"]},{}]}
~~~~

## 以試驗的 User-Agent 與 Referer 核對停批日期（單一請求）

2026-11-25T01:42:32.789230+00:00，GET https://wwwc.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date=20240606&selectType=MS&response=json，HTTP 200。Location = （無）。本文共 1850 bytes。

    server: envoy
    date: Wed, 25 Nov 2026 01:42:32 GMT
    content-type: application/json;charset=UTF-8
    x-application-context: application:production
    set-cookie: [公開版遮蔽工作階段值]
    vary: accept-encoding
    content-encoding: gzip
    content-security-policy: frame-ancestors 'self' *.twse.com.tw *.tdcc.com.tw http://digitalprocesssyst-epassbook.cdn.hinet.net digitalprocesssys-epassbook.cdn.hinet.net;
    x-content-type-options: nosniff
    referrer-policy: strict-origin-when-cross-origin
    permissions-policy: camera=(),microphone=(),geolocation=(),sync-xhr=*,gyroscope=()
    strict-transport-security: max-age=31536000; includeSubDomains; preload
    access-control-allow-origin: *
    x-envoy-upstream-service-time: 159
    transfer-encoding: chunked

~~~~
{"stat":"OK","date":"20240606","tables":[{"title":"113年06月06日 信用交易統計","fields":["項目","買進","賣出","現金(券)償還","前日餘額","今日餘額"],"data":[["融資(交易單位)","412,063","337,368","5,695","8,779,475","8,848,475"],["融券(交易單位)","22,337","19,629","4,669","265,031","257,654"],["融資金額(仟元)","17,490,176","16,037,457","188,083","302,355,018","303,619,654"]],"notes":["本公司市場融資融券餘額的資料來源係為各授信機構(含證金公司及自辦信用交易證券商)，待各授信機構整體作業結束且傳輸完成，復經本公司彙整後於當日晚間即時公布於本公司網站。前述作業程序或因當日市場成交量值多寡，或因各授信機構傳輸過程順遂與否、更帳次數及作業時間長短等因素，均將影響本公司完成本表時間。","由於各授信機構於該信用交易成交的次日，仍繼續處理相關調帳作業，本公司待各授信機構整體作業結束且傳輸最終正確餘額數字完成後，始完整揭露於『前日餘額』欄位中，故請以『前日餘額』為準，而以『今日餘額』為輔助參考資料。","遇上櫃證券轉上市，且得為融資融券交易時，本報表於該證券上市交易日即列入信用交易資訊，並將該證券之融資融券餘額列計後，調整當日報表『前日餘額』之統計數字；該證券融資融券餘額，請參閱本公司MIS即時公告。","當日如有臨時新增之變更交易有價證券標的，網頁右上角會呈現點選框，屆時請點選明細查詢，另外，歷史資料也可點選此 <a href='/zh/trading/bfihbu.html' target='_blank'>連結<\u002fa> 查詢。當日臨時新增之變更交易有價證券，若該證券原得為融資融券交易，將被暫停融資融券。"]},{}]}
~~~~

## 上市法人停批診斷

2026-11-25T01:43:10.518408+00:00，GET https://wwwc.twse.com.tw/rwd/zh/fund/BFI82U?dayDate=20260115&type=day&response=json，HTTP 200，Location = （無），本文 1565 bytes。

    server: envoy
    date: Wed, 25 Nov 2026 01:43:10 GMT
    content-type: application/json;charset=UTF-8
    x-application-context: application:production
    set-cookie: [公開版遮蔽工作階段值]
    vary: accept-encoding
    content-encoding: gzip
    content-security-policy: frame-ancestors 'self' *.twse.com.tw *.tdcc.com.tw http://digitalprocesssyst-epassbook.cdn.hinet.net digitalprocesssys-epassbook.cdn.hinet.net;
    x-content-type-options: nosniff
    referrer-policy: strict-origin-when-cross-origin
    permissions-policy: camera=(),microphone=(),geolocation=(),sync-xhr=*,gyroscope=()
    strict-transport-security: max-age=31536000; includeSubDomains; preload
    access-control-allow-origin: *
    x-envoy-upstream-service-time: 172
    transfer-encoding: chunked

~~~~
{"stat":"OK","date":"20260115","title":"115年01月15日 三大法人買賣金額統計表","fields":["單位名稱","買進金額","賣出金額","買賣差額"],"data":[["自營商(自行買賣)","4,808,834,081","6,061,529,979","-1,252,695,898"],["自營商(避險)","23,341,920,748","27,932,493,109","-4,590,572,361"],["投信","12,325,643,345","15,104,754,858","-2,779,111,513"],["外資及陸資(不含外資自營商)","226,377,838,206","226,588,062,689","-210,224,483"],["外資自營商","0","0","0"],["合計","266,854,236,380","275,686,840,635","-8,832,604,255"]],"params":{"dayDate":"20260115","type":"day","response":"json","controller":"fund","action":"BFI82U","lang":"zh","monthDate":null,"weekDate":null},"notes":["自營商表示證券自營商專戶。","投信表示本國投資信託基金。","外資及陸資表示依「華僑及外國人投資證券管理辦法」及「大陸地區投資人來臺從事證券投資及期貨交易管理辦法」辦理登記等投資人。","因外資自營商買賣金額已計入自營商買賣金額，故不納入三大法人買賣金額之合計數計算。","本統計資訊含一般、零股、盤後定價、鉅額，不含拍賣、標購。","本資訊以當日原始成交情形統計，不以證券商申報錯帳、更正帳號等調整後資料統計。","外幣成交值係以本公司當日下午3時30分公告匯率換算後加入成交金額。<br>公告匯率請參考本公司首頁>產品與服務>交易系統>雙幣ETF專區>代號對應及每日公告匯率。"],"hints":"單位：元"}
~~~~

## 十日試驗與停批條件

採用同一 requests.Session、官方首頁與該頁 Referer，使用標明研究用途的 User-Agent。兩個上市來源選相同十個原缺日：2024-07-11、07-12，2026-01-15、01-16、01-19、01-20、01-21、01-22、01-23、01-26。

| 來源 | 十日試驗 | 擴大結果 |
|---|---|---|
| 上市融資融券 | 10 成功、0 失敗，均 HTTP 200 且資料日相符 | 原節流下另補 115 日；2024-06-06 連續 307 後停批。該日後續獨立診斷取得 200，又核實 1 日。 |
| 上市法人 | 首頁 HTTP 307，該批成功 0 日，10 日未送出 | 未擴大。另一次停批診斷取得 2026-01-15 官方資料，核實 1 日。 |
| 台指期 | 0 成功、10 失敗；9 次 HTTP 200 但無法解析成官方期貨 CSV，2023-11-09 讀取逾時，無 HTTP 狀態碼 | 未擴大。試驗日期是 2023-11-01 至 11-14 的前十個缺日；均已超過期交所說明的三年查詢期。 |

本次 307 的發生已觀測到；當時試驗器只保留狀態碼，未保存該回應的原始 headers、Location 或本文。獨立單次診斷均回 200，不能由這些 200 推斷 307 的 Location 或根因。公開紀錄保留回應標頭名稱，Set-Cookie 值遮蔽。未擴大重試次數。已新增 response hook，後續受准執行回補入口時會在第一次 307 返回當下保存標頭及本文前 2 KB。

免費逐日批次端點未找到，批次法未執行。新分支的完整固定版本環境通過 38 項測試；連續三次 307 停批且舊檔位元組不變、同工作階段首頁與 Referer、首次 307 捕捉及安裝清單均有測試。

## 缺口盤點

依 743 個台股指數交易日核對。下表 FRED 的 0 是上輪已核實觀測區間內的歷史缺口，本次手動抓取逾時，無法重新核對後續發布日。

|來源|回補前缺日|回補後缺日|
|---|---:|---:|
|tw_index|0|0|
|otc_index|0|0|
|tw_institution|151|150|
|otc_institution|0|0|
|tw_margin|655|529|
|otc_margin|0|0|
|tx_oi|18|18|
|SP500|0|0|
|VIXCLS|0|0|
|DGS10|0|0|
|DFF|0|0|
|DEXTAUS|0|0|

### tw_institution 仍缺日期

- 2024-07：11、12
- 2026-01：16、19、20、21、22、23、26、27、28、29、30
- 2026-02：02、03、04、05、06、09、10、11、23、24、25、26
- 2026-03：02、03、04、05、06、09、10、11、12、13、16、17、18、19、20、23、24、25、26、27、30、31
- 2026-04：01、02、07、08、09、10、13、14、15、16、17、20、21、22、23、24、27、28、29、30
- 2026-05：04、05、06、07、08、11、12、13、14、15、18、19、20、21、22、25、26、27、28、29
- 2026-06：01、02、03、04、05、08、09、10、11、12、15、16、17、18、22、23、24、25、26、29、30
- 2026-07：01、02、03、06、07、08、09、13、14、15、16、17、20、21、22、23、24、27、28、29、30、31
- 2026-08：03、04、05、06、07、10、11
- 2026-09：01、02、03、04、07
- 2026-10：12、13、14、15、16、19、20、21

### tw_margin 仍缺日期

- 2024-06：07、11、12、13、14、17、18、19、20、21、24、25、26、27、28
- 2024-07：01、02、03、04、05、08、09、10、15、16、17、18、19、22、23、26、29、30、31
- 2024-08：01、02、05、06、07、08、09、12、13、14、15、16、19、20、21、22、23、26、27、28、29、30
- 2024-09：02、03、04、05、06、09、10、11、12、13、16、18、19、20、23、24、25、26、27、30
- 2024-10：01、04、07、08、09、11、14、15、16、17、18、21、22、23、24、25、28、29、30
- 2024-11：01、04、05、06、07、08、11、12、13、14、15、18、19、20、21、22、25、26、27、28、29
- 2024-12：02、03、04、05、06、09、10、11、12、13、16、17、18、19、20、23、24、25、26、27、30、31
- 2025-01：02、03、06、07、08、09、10、13、14、15、16、17、20、21、22
- 2025-02：03、04、05、06、07、10、11、12、13、14、17、18、19、20、21、24、25、26、27
- 2025-03：03、04、05、06、07、10、11、12、13、14、17、18、19、20、21、24、25、26、27、28、31
- 2025-04：01、02、07、08、09、10、11、14、15、16、17、18、21、22、23、24、25、28、29、30
- 2025-05：02、05、06、07、08、09、12、13、14、15、16、19、20、21、22、23、26、27、28、29
- 2025-06：02、03、04、05、06、09、10、11、12、13、16、17、18、19、20、23、24、25、26、27、30
- 2025-07：01、02、03、04、07、08、09、10、11、14、15、16、17、18、21、22、23、24、25、28、29、30、31
- 2025-08：01、04、05、06、07、08、11、12、13、14、15、18、19、20、21、22、25、26、27、28、29
- 2025-09：01、02、03、04、05、08、09、10、11、12、15、16、17、18、19、22、23、24、25、26、30
- 2025-10：01、02、03、07、08、09、13、14、15、16、17、20、21、22、23、27、28、29、30、31
- 2025-11：03、04、05、06、07、10、11、12、13、14、17、18、19、20、21、24、25、26、27、28
- 2025-12：01、02、03、04、05、08、09、10、11、12、15、16、17、18、19、22、23、24、26、29、30、31
- 2026-01：02、05、06、07、08、09、12、13、14、27、28、29、30
- 2026-02：02、03、04、05、06、09、10、11、23、24、25、26
- 2026-03：02、03、04、05、06、09、10、11、12、13、16、17、18、19、20、23、24、25、26、27、30、31
- 2026-04：01、02、07、08、09、10、13、14、15、16、17、20、21、22、23、24、27、28、29、30
- 2026-05：04、05、06、07、08、11、12、13、14、15、18、19、20、21、22、25、26、27、28、29
- 2026-06：01、02、03、04、05、08、09、10、11、12、15、16、17、18、22、23、24、25、26、29、30
- 2026-07：01、02、03、06、07、08、09、13、14、15、16、17、20、21、22、23、24、27、28、29、30、31
- 2026-08：03、04、05、06、07、10
- 2026-09：01、02、03、04、07
- 2026-10：12、13、14、15、16、19、20

### tx_oi 仍缺日期

- 2023-11：01、02、03、06、07、08、09、10、13、14、15、16、17、20、21、22、23
- 2026-08：03
