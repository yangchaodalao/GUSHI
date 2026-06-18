"""市场广度数据 - 同花顺首页 DOM 提取涨跌家数、涨停跌停。
失败时标记回退 WebSearch。
"""
from playwright.sync_api import sync_playwright
import json, sys, io, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def scrape() -> dict:
    """方案A: 同花顺首页 body text 正则提取。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = ctx.new_page()
        page.add_init_script("""Object.defineProperty(navigator, 'webdriver', {get: () => undefined});""")
        page.goto("https://q.10jqka.com.cn/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        body = page.inner_text("body")
        browser.close()

    up_m = re.search(r'上涨[：:]\s*(\d[\d,]*)\s*只', body)
    down_m = re.search(r'下跌[：:]\s*(\d[\d,]*)\s*只', body)
    zt_m = re.search(r'涨停[：:]\s*(\d[\d,]*)\s*只', body)
    dt_m = re.search(r'跌停[：:]\s*(\d[\d,]*)\s*只', body)

    up = int(up_m.group(1).replace(",", "")) if up_m else None
    down = int(down_m.group(1).replace(",", "")) if down_m else None
    zt = int(zt_m.group(1).replace(",", "")) if zt_m else None
    dt = int(dt_m.group(1).replace(",", "")) if dt_m else None

    # 提取涨跌分布直方图（10档: 跌停 -8% -6% -4% -2% 0 +2% +4% +6% +8% 涨停）
    dist = None
    dist_m = re.findall(r'(\d+)\s*\n\s*(?:跌停|-[86４６]|[0９]|涨停|\+?[0-9]+%)', body)
    if len(dist_m) >= 10:
        dist = [int(x) for x in dist_m[:10]]

    # 提取大盘评级
    rating_m = re.search(r'大盘评级\s*\n\s*([\d.]+)分', body)
    rating = float(rating_m.group(1)) if rating_m else None

    if up is None and down is None:
        return None

    return {
        "source": "direct_dom",
        "page": "q.10jqka.com.cn",
        "up_count": up,
        "down_count": down,
        "limit_up": zt,
        "limit_down": dt,
        "distribution": dist,
        "market_rating": rating,
    }


# ============================================================
if __name__ == "__main__":
    result = None
    try:
        result = scrape()
    except Exception as e:
        print(f"[scrape_market_breadth] 同花顺首页失败: {e}", file=sys.stderr)

    if result is None:
        result = {
            "source": "fallback_needed",
            "up_count": None,
            "down_count": None,
            "limit_up": None,
            "limit_down": None,
            "fallback_method": "websearch",
            "note": "⚠️ 同花顺首页不可用，涨跌家数/涨停跌停需通过 WebSearch 获取，报告中必须标注「备用数据源」。",
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
