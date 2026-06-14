"""同花顺行业板块排名抓取 - 使用 Playwright + 内部 API 提取所有分页数据。"""
from playwright.sync_api import sync_playwright
import re
import json
import sys


def scrape() -> list[dict]:
    """返回行业板块列表，每项含 name(板块名) 和 change(涨跌幅%)。"""
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
        # 先加载主页获取 cookies / session
        page.goto("https://q.10jqka.com.cn/thshy/", timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(3000)

        all_sectors = []
        # 通过内部 API 获取所有分页数据（共 2 页）
        for page_num in [1, 2]:
            html = page.evaluate(
                f"""async () => {{
                    const r = await fetch('/thshy/index/field/199112/order/desc/page/{page_num}/ajax/1/');
                    const buf = await r.arrayBuffer();
                    const decoder = new TextDecoder('gbk');
                    return decoder.decode(buf);
                }}"""
            )
            # 解析表格行
            # 每行格式: <tr><td>序号</td><td><a ...>板块名</a></td><td class="c-fall|c-rise">涨跌幅</td>...
            rows = re.findall(
                r"<tr[^>]*>.*?<td>\d+</td>\s*<td><a[^>]*>([^<]+)</a></td>\s*<td[^>]*>([+-]?\d+\.\d+)</td>",
                html,
                re.DOTALL,
            )
            for name, change_str in rows:
                all_sectors.append({"name": name.strip(), "change": float(change_str)})

        browser.close()
        return all_sectors


if __name__ == "__main__":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    try:
        result = scrape()  # 已按涨幅降序排列
        top5 = result[:5]
        bottom5 = result[-5:] if len(result) >= 5 else result[-len(result):]
        output = {
            "source": "direct_api",
            "api": "q.10jqka.com.cn/thshy AJAX",
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
            "note": f"⚠️ 同花顺行业板块API不可用({e})，需通过WebSearch获取板块排名，报告中必须标注「备用数据源」。",
        }
    print(json.dumps(output, ensure_ascii=False))
