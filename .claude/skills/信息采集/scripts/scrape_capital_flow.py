"""资金流向 - 优先东方财富 HTTP API，失败回退 WebSearch。
获取: 北向/南向 沪深港通 买入/卖出/净流向。
"""
import json, sys, io, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EASTMONEY_API = (
    "https://push2.eastmoney.com/api/qt/kamt/get"
    "?fields1=f1,f2,f3,f4"
    "&fields2=f51,f52,f53,f54,f56,f60,f61,f62,f63,f65,f66"
    "&ut=fa5fd1943c7b386f172d6893dbfba10b"
)
DIRECTION_LABELS = {
    "hk2sh": {"name": "北向-沪股通", "direction": "北向"},
    "hk2sz": {"name": "北向-深股通", "direction": "北向"},
    "sh2hk": {"name": "南向-沪港通", "direction": "南向"},
    "sz2hk": {"name": "南向-深港通", "direction": "南向"},
}


def scrape_via_api() -> dict | None:
    """方案A: 纯 HTTP 调东方财富 push2 API。"""
    req = urllib.request.Request(EASTMONEY_API, headers={"Referer": "https://data.eastmoney.com/hsgt/index.html"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw = data.get("data", {})
    if not raw:
        return None

    flows = {}
    for key, label in DIRECTION_LABELS.items():
        item = raw.get(key, {})
        buy = item.get("buyAmt", 0) or 0
        sell = item.get("sellAmt", 0) or 0
        net = round((buy - sell) / 10000, 2)          # 万 → 亿
        turnover = round((item.get("buySellAmt", 0) or 0) / 10000, 2)

        flows[key] = {
            "label": label["name"],
            "direction": label["direction"],
            "buy_yi": round(buy / 10000, 2),
            "sell_yi": round(sell / 10000, 2),
            "net_yi": net,
            "turnover_yi": turnover,
            "date": item.get("date2"),
            "status": item.get("status"),
        }

    north_net = round(sum(v["net_yi"] for k, v in flows.items() if v["direction"] == "北向"), 2)
    south_net = round(sum(v["net_yi"] for k, v in flows.items() if v["direction"] == "南向"), 2)
    north_turnover = round(sum(v["turnover_yi"] for k, v in flows.items() if v["direction"] == "北向"), 2)

    return {
        "source": "direct_api",
        "api": "push2.eastmoney.com",
        "flows": flows,
        "north_net_yi": north_net,
        "south_net_yi": south_net,
        "north_turnover_yi": north_turnover,
    }


# ============================================================
if __name__ == "__main__":
    result = None
    try:
        result = scrape_via_api()
    except Exception as e:
        print(f"[scrape_capital_flow] 东财API失败: {e}", file=sys.stderr)

    if result is None:
        result = {
            "source": "fallback_needed",
            "flows": {},
            "north_net_yi": None,
            "south_net_yi": None,
            "north_turnover_yi": None,
            "fallback_method": "websearch",
            "note": "⚠️ 东方财富API不可用，北向/南向资金需通过 WebSearch 获取，报告中必须标注「备用数据源」。",
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
