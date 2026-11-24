"""官方統計的來源網址與公開 CSV 欄位。"""
FRED = ("SP500", "VIXCLS", "DGS10", "DFF", "DEXTAUS")
GROUPS = ("dealer", "trust", "foreign")
INDEX = ("tw_index", "otc_index")
DAILY = ("tw_institution", "otc_institution", "tw_margin", "otc_margin")
COLUMNS = {
    **dict.fromkeys(INDEX, ("close", "change_points", "turnover_twd")),
    **dict.fromkeys(DAILY[:2], ("dealer_net_twd", "trust_net_twd", "foreign_net_twd", "total_net_twd")),
    **dict.fromkeys(DAILY[2:], ("financing_units", "short_units", "financing_thousand_twd")),
    "tx_oi": tuple(f"{group}_{side}" for group in GROUPS for side in ("long", "short", "net")),
    **dict.fromkeys(FRED, ("value",)),
}
def endpoint(name, start, end):
    tw = "https://wwwc.twse.com.tw/rwd/zh/"
    otc = "https://www.tpex.org.tw/www/zh-tw/"
    day = start.strftime("%Y%m%d")
    slash = start.strftime("%Y/%m/%d")
    if name in FRED:
        return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={name}&cosd={start}"
    return {
        "tw_index": tw + f"afterTrading/FMTQIK?date={day}&response=json",
        "otc_index": otc + f"afterTrading/tradingIndex?date={slash}&response=json",
        "tw_institution": tw + f"fund/BFI82U?dayDate={day}&type=day&response=json",
        "tw_margin": tw + f"marginTrading/MI_MARGN?date={day}&selectType=MS&response=json",
        "otc_institution": otc + f"insti/summary?date={slash}&response=json",
        "otc_margin": otc + f"margin/balance?date={slash}&response=json",
        "tx_oi": ("https://www.taifex.com.tw/cht/3/futContractsDateDown?"
                  f"queryStartDate={slash}&queryEndDate={end:%Y/%m/%d}&commodityId=TXF"),
    }[name]
