"""开盘前市场数据采集 — 新浪 + 东财混合 API
获取: 美股三大指数 / A50期货 / 黄金 / 原油 / 外汇 / 中概股
运行时间: 8:30 AM 北京时间（美股已收盘，商品外汇取最新价）

数据源优先级:
  美股指数:  东财 ulist (实际指数值) → 新浪 ETF SPY/QQQ/DIA (代理)
  A50期货:   东财 stock/get → WebSearch 兜底
  商品/外汇:  新浪 (hf_/fx_)
  中概股:    新浪 (gb_)
"""
import sys, json, urllib.request, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════
# 新浪 API
# ═══════════════════════════════════════════════════════════════
SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}


def fetch_sina(codes: list[str]) -> dict[str, list[str]]:
    """获取新浪行情数据，返回 {code: [field0, field1, ...]}"""
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    req = urllib.request.Request(url, headers=SINA_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("gbk")

    result = {}
    for line in raw.strip().split("\n"):
        if "=" not in line or '"' not in line:
            continue
        code = line.split("=")[0].replace("var hq_str_", "")
        vals = line.split('"')[1].split(",")
        if vals and vals[0]:
            result[code] = vals
    return result


def parse_us_stock(fields: list[str]) -> dict | None:
    """解析新浪美股字段 — 从最后一个 EDT 时间后取 prev_close"""
    if not fields or len(fields) < 5:
        return None
    try:
        price = float(fields[1])
    except (ValueError, IndexError):
        return None

    prev_close = None
    for i, f in enumerate(fields):
        if "EDT" in f and i + 1 < len(fields):
            try:
                prev_close = float(fields[i + 1])
            except ValueError:
                pass

    if prev_close is None:
        return {"name": fields[0], "price": price, "change_pct": None, "change_amt": None}

    change_amt = round(price - prev_close, 2)
    change_pct = round(change_amt / prev_close * 100, 2)
    return {"name": fields[0], "price": price, "prev_close": prev_close,
            "change_amt": change_amt, "change_pct": change_pct}


def parse_futures(fields: list[str]) -> dict | None:
    """解析新浪期货 (hf_GC/hf_CL): [0]=最新价, [7]=昨结算, [13]=名称"""
    if not fields or len(fields) < 10:
        return None
    try:
        price = float(fields[0])
    except (ValueError, IndexError):
        return None

    name = fields[13] if len(fields) > 13 and fields[13] else ""
    prev_settle = None
    if len(fields) > 7:
        try:
            prev_settle = float(fields[7])
        except ValueError:
            pass

    change_pct = None
    change_amt = None
    if prev_settle and prev_settle > 0:
        change_amt = round(price - prev_settle, 2)
        change_pct = round(change_amt / prev_settle * 100, 2)

    return {"name": name, "price": price, "prev_settle": prev_settle,
            "change_amt": change_amt, "change_pct": change_pct}


def parse_forex(fields: list[str]) -> dict | None:
    """解析新浪外汇: [1]=最新价, [9]=名称, [10]=涨跌额, [11]=涨跌幅%"""
    if not fields or len(fields) < 12:
        return None
    try:
        price = float(fields[1])
    except (ValueError, IndexError):
        return None

    name = fields[9] if len(fields) > 9 else ""
    change_pct = None
    if len(fields) > 11:
        try:
            change_pct = float(fields[11])
        except ValueError:
            pass
    change_amt = None
    if len(fields) > 10:
        try:
            change_amt = float(fields[10])
        except ValueError:
            pass
    return {"name": name, "price": price, "change_pct": change_pct, "change_amt": change_amt}


# ── 新浪 ETF 代理（东财不可用时）──────────────────────────
# SPY ≈ S&P500×0.1, QQQ ≈ NASDAQ-100×0.025, DIA ≈ DJIA×0.01
# 涨跌幅与指数几乎完全一致，用作代理完全足够
SINA_ETF_MAP = {
    "gb_spy": ("标普500", "SPY"),
    "gb_qqq": ("纳斯达克", "QQQ"),
    "gb_dia": ("道琼斯", "DIA"),
}


def fetch_sina_us_indices() -> dict | None:
    """新浪 ETF 代理 — 美股三大指数方向"""
    try:
        data = fetch_sina(list(SINA_ETF_MAP.keys()))
    except Exception:
        return None

    indices = {}
    for code, (label, etf_name) in SINA_ETF_MAP.items():
        raw = data.get(code)
        if raw:
            parsed = parse_us_stock(raw)
            if parsed and parsed.get("change_pct") is not None:
                indices[label] = {
                    "price": parsed["price"],
                    "change_pct": parsed["change_pct"],
                    "change_amt": parsed["change_amt"],
                    "code": etf_name,
                    "note": "ETF代理（东财API不可用）",
                }
    return indices if indices else None


# ═══════════════════════════════════════════════════════════════
# 东财 API
# ═══════════════════════════════════════════════════════════════
EM_HEADERS = {
    "Referer": "https://quote.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _em_request(url: str, max_retries: int = 2) -> dict:
    """东财 API 请求，带重试"""
    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=EM_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2.0)
    raise last_err  # type: ignore


def fetch_em_us_indices() -> dict | None:
    """东财 ulist.np/get — 美股三大指数（实际值）"""
    url = ("https://push2.eastmoney.com/api/qt/ulist.np/get?"
           "fltt=2&invt=2&fields=f2,f3,f4,f12,f14&secids=100.DJIA,100.NDX,100.SPX")
    data = _em_request(url)
    diff = data.get("data", {}).get("diff")
    if not diff:
        return None

    indices = {}
    for item in diff:
        indices[item["f14"]] = {
            "price": item["f2"],
            "change_pct": item["f3"],
            "change_amt": item["f4"],
            "code": item["f12"],
        }
    return indices


def fetch_em_a50() -> dict | None:
    """东财 stock/get — A50期货 (SGX, 104.CN00Y)"""
    url = ("https://push2.eastmoney.com/api/qt/stock/get?"
           "fields=f43,f44,f45,f46,f57,f58,f169,f170&secid=104.CN00Y")
    data = _em_request(url)
    d = data.get("data")
    if not d or d.get("f43") is None:
        return None

    raw_price = d["f43"]
    price = raw_price / 10
    chg_amt = d.get("f169", 0) / 10 if d.get("f169") else None
    if chg_amt is not None and price is not None:
        prev = price - chg_amt
        chg_pct = round(chg_amt / prev * 100, 2) if prev != 0 else 0
    else:
        chg_pct = None

    return {
        "name": d.get("f58", "A50期指当月连续"),
        "price": price,
        "open": d.get("f46", 0) / 10 if d.get("f46") else None,
        "high": d.get("f44", 0) / 10 if d.get("f44") else None,
        "low": d.get("f45", 0) / 10 if d.get("f45") else None,
        "change_amt": chg_amt,
        "change_pct": chg_pct,
        "code": d.get("f57"),
    }


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    result = {
        "source": "direct_api",
        "us_indices": None,
        "us_indices_source": None,  # "eastmoney" | "sina_etf"
        "a50_futures": None,
        "gold": None,
        "oil": None,
        "forex": {},
        "cn_adrs": [],
        "errors": [],
    }

    # ── 1) 美股指数：东财优先，新浪 ETF 备用 ──
    try:
        result["us_indices"] = fetch_em_us_indices()
        result["us_indices_source"] = "eastmoney"
    except Exception as e:
        result["errors"].append(f"美股(EastMoney): {e}")
        # 回退新浪 ETF
        try:
            result["us_indices"] = fetch_sina_us_indices()
            result["us_indices_source"] = "sina_etf"
        except Exception as e2:
            result["errors"].append(f"美股(SinaETF): {e2}")

    # ── 2) A50 期货：东财，失败则标记兜底 ──
    try:
        result["a50_futures"] = fetch_em_a50()
    except Exception as e:
        result["errors"].append(f"A50(EastMoney): {e}")

    # ── 3) 黄金/原油/外汇/中概股：新浪一次请求 ──
    sina_codes = [
        "hf_GC", "hf_CL",
        "fx_susdcny", "fx_susdcnh",
        "gb_baba", "gb_jd", "gb_pdd",
    ]
    try:
        sina_data = fetch_sina(sina_codes)

        for raw, setter in [
            (sina_data.get("hf_GC"), lambda p: result.update({"gold": p})),
            (sina_data.get("hf_CL"), lambda p: result.update({"oil": p})),
        ]:
            if raw:
                parsed = parse_futures(raw)
                if parsed:
                    setter(parsed)

        for code in ["fx_susdcny", "fx_susdcnh"]:
            raw = sina_data.get(code)
            if raw:
                parsed = parse_forex(raw)
                if parsed:
                    result["forex"][code] = parsed

        for code, label in [("gb_baba", "阿里巴巴"), ("gb_jd", "京东"), ("gb_pdd", "拼多多")]:
            raw = sina_data.get(code)
            if raw:
                parsed = parse_us_stock(raw)
                if parsed:
                    parsed["code"] = code
                    parsed["label"] = label
                    result["cn_adrs"].append(parsed)
    except Exception as e:
        result["errors"].append(f"新浪: {e}")

    # ── 4) 完整性检查 ──
    missing = []
    if not result["us_indices"]:
        missing.append("美股指数")
    if not result["a50_futures"]:
        missing.append("A50期货")
    if not result["gold"]:
        missing.append("COMEX黄金")
    if not result["oil"]:
        missing.append("WTI原油")

    if missing:
        result["fallback_items"] = missing
        result["fallback_note"] = "部分数据源不可用，需 WebSearch 兜底"

    # source 细化
    if result["us_indices_source"] == "sina_etf":
        result["source"] = "partial_fallback"
        result["fallback_note"] = "美股指数使用ETF代理（涨跌幅与指数一致），其余为直接API"

    if not result["a50_futures"]:
        result["source"] = "partial_fallback" if result["us_indices"] else "fallback_needed"

    print(json.dumps(result, ensure_ascii=False, indent=2))
