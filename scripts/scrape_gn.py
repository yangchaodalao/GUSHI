"""同花顺概念板块排名抓取 - 使用 Playwright 从页面 hidden input 解析 JSON 数据。"""
from playwright.sync_api import sync_playwright
import json
import sys


def scrape() -> list[dict]:
    """返回概念板块列表，每项含 name(概念名) 和 change(涨跌幅%)，按涨幅降序排列。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        page = ctx.new_page()
        page.add_init_script(
            """Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"""
        )
        page.goto("https://q.10jqka.com.cn/gn/", timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(5000)

        raw = page.evaluate("""() => {
            const el = document.getElementById('gnSection');
            return el ? el.value : null;
        }""")

        if not raw:
            browser.close()
            return []

        data = json.loads(raw)
        sectors = []
        for k, v in data.items():
            name = v.get("platename", "")
            change = v.get("199112", 0)
            if name:
                sectors.append({"name": name, "change": float(change)})

        sectors.sort(key=lambda x: x["change"], reverse=True)

        browser.close()
        return sectors


if __name__ == "__main__":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    try:
        result = scrape()  # 已按涨幅降序排列
        top5 = result[:5]
        bottom5 = result[-5:] if len(result) >= 5 else result[-len(result):]
        output = {
            "source": "direct_api",
            "api": "q.10jqka.com.cn/gn hidden JSON",
            "top": top5,
            "bottom": bottom5,
            "total_count": len(result),
        }
    except Exception as e:
        output = {
            "source": "fallback_needed",
            "top": [],
            "bottom": [],
            "total_count": 0,
            "fallback_method": "websearch",
            "note": f"⚠️ 同花顺概念板块JSON不可用({e})，需通过WebSearch获取概念板块排名，报告中必须标注「备用数据源」。",
        }
    print(json.dumps(output, ensure_ascii=False))
