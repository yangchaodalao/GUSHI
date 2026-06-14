"""指数数据抓取 - 优先使用新浪 HTTP API，失败时回退 Playwright。
获取: 上证/深证/创业板/科创50 价格、涨跌幅、成交额（两市合计）。
"""
import json, sys, io, re, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SINA_API_URL = "https://hq.sinajs.cn/list=sh000001,sz399001,sz399006,sh000688"
INDEX_MAP = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
}


def scrape_via_api() -> dict | None:
    """方案A: 纯 HTTP 调用新浪行情 API（零浏览器，零幻觉）。"""
    req = urllib.request.Request(SINA_API_URL, headers={"Referer": "https://finance.sina.com.cn"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("gbk")

    indices = {}
    for line in raw.strip().split("\n"):
        if "=" not in line or '"' not in line:
            continue
        code = line.split("=")[0].replace("var hq_str_", "")
        name = INDEX_MAP.get(code)
        if not name:
            continue
        vals = line.split('"')[1].split(",")
        price = float(vals[3])
        prev_close = float(vals[2])
        change_pct = round((price - prev_close) / prev_close * 100, 2)
        amount_yuan = float(vals[9]) if vals[9] else 0

        indices[name] = {
            "price": price,
            "change_pct": change_pct,
            "amount_yi": round(amount_yuan / 100_000_000, 2),
            "open": float(vals[1]),
            "high": float(vals[4]),
            "low": float(vals[5]),
            "prev_close": prev_close,
            "date": vals[30],
            "time": vals[31],
        }

    if len(indices) < 4:
        return None  # 数据不完整

    sh_amt = indices["上证指数"]["amount_yi"]
    sz_amt = indices["深证成指"]["amount_yi"]
    total_yi = round(sh_amt + sz_amt, 2)

    return {
        "source": "direct_api",
        "api": "hq.sinajs.cn",
        "indices": indices,
        "total_amount_yi": total_yi,
    }


def scrape_via_playwright() -> dict | None:
    """方案B: Playwright 回退 — 渲染新浪页面后正则提取（旧方案）。"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = ctx.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', {get: () => undefined});""")
        page.goto("https://finance.sina.com.cn/realstock/company/sh000001/nc.shtml", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        text = page.inner_text("body")

        indices = {}
        for label, code in [("上证指数", "sh000001"), ("深证成指", "sz399001")]:
            m = re.search(rf"{label}[：:](\d+\.\d+)\s+([+-]\d+\.\d+)%\s+(\d+\.\d+)亿元", text)
            if m:
                indices[label] = {
                    "price": float(m.group(1)),
                    "change_pct": float(m.group(2)),
                    "amount_yi": float(m.group(3)),
                }

        browser.close()

    if len(indices) < 2:
        return None

    total_yi = round(sum(v["amount_yi"] for v in indices.values()), 2)
    return {
        "source": "playwright_fallback",
        "api": "sina finance page regex",
        "indices": indices,
        "total_amount_yi": total_yi,
        "note": "新浪API不可用，使用Playwright页面提取备用方案。创业板/科创50需从WebSearch补全。",
    }


# ============================================================
if __name__ == "__main__":
    result = None

    # 1) 优先直接 API
    try:
        result = scrape_via_api()
    except Exception as e:
        print(f"[scrape_sina] 直接API失败: {e}", file=sys.stderr)

    # 2) 回退 Playwright
    if result is None:
        try:
            result = scrape_via_playwright()
        except Exception as e:
            print(f"[scrape_sina] Playwright回退也失败: {e}", file=sys.stderr)

    # 3) 完全失败
    if result is None:
        result = {
            "source": "all_failed",
            "indices": {},
            "total_amount_yi": None,
            "note": "新浪API和Playwright均不可用。需通过WebSearch获取全部指数数据，并在报告中标注⚠️备用数据源。",
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
