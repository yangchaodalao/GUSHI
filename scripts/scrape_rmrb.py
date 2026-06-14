"""人民日报电子版头版抓取 — Playwright DOM 提取
URL: https://paper.people.com.cn/rmrb/pc/layout/YYYYMM/DD/node_01.html
这是印刷版报纸的数字化版本，每篇文章都有独立链接。
"""
import sys, json
from datetime import datetime
from playwright.sync_api import sync_playwright

DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m/%d")
# e.g. "202606/14"

URL = f"https://paper.people.com.cn/rmrb/pc/layout/{DATE}/node_01.html"

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=15000, wait_until="domcontentloaded")

        # 提取所有文章链接和标题
        # 电子版页面中，文章链接通常在 div.news 或 ul.list 中的 a 标签
        articles = page.locator("a[href*='content_']").evaluate_all("""
            els => els.map(el => ({
                title: el.textContent.trim(),
                url: el.href
            })).filter(a => a.title.length > 5)
        """)

        browser.close()

    if articles:
        # 去重（同一篇文章可能出现多次）
        seen = set()
        unique = []
        for a in articles:
            if a['url'] not in seen:
                seen.add(a['url'])
                unique.append(a)

        print(json.dumps({
            "source": "playwright_dom",
            "date": DATE.replace("/", "-"),
            "url": URL,
            "count": len(unique),
            "articles": unique
        }, ensure_ascii=False))
    else:
        print(json.dumps({
            "source": "fallback_needed",
            "error": "未提取到任何文章",
            "fallback_method": "site:paper.people.com.cn"
        }, ensure_ascii=False))

except Exception as e:
    print(json.dumps({
        "source": "fallback_needed",
        "error": str(e),
        "fallback_method": "site:paper.people.com.cn"
    }, ensure_ascii=False))
