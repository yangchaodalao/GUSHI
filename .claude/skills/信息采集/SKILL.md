---
name: 信息采集
description: A股收盘后（15:00+）的完整市场日报——当日指数/板块涨跌/资金流向/时政要闻。这是获取A股当天实际收盘表现的唯一入口。当用户提到"收盘""大盘数据""今日股市""A股行情""今天涨跌""行情怎么样""涨了没""今天大盘""股市数据""市场日报""财经简报""财经新闻汇总""股市日报""财经日报"等收盘后场景时使用此 skill。即使只模糊提到"今天行情怎么样"或"今天涨了还是跌了""大盘数据"也应该触发此 skill。不要自己拼凑数据，不要凭记忆回答指数点位。⚠️ 如果用户说的是开盘前场景（早盘/盘前/隔夜），请用 早盘要闻。
compatibility: 需要 Playwright (pip install playwright) + Chromium (python -m playwright install chromium)
---

# 每日新闻与股市数据采集

生成当日 A 股市场结构化日报，保存为 Markdown 文件。

**核心原则：市场数据 → 直接 API/DOM 提取（零幻觉）；时政新闻 → WebSearch。**

## 数据采集架构

```
直接 API（纯 HTTP，零浏览器）:
  hq.sinajs.cn ─────────→ 4 指数 价格/涨跌幅/成交额 (scrape_sina.py)
  push2.eastmoney.com ──→ 北向/南向 资金流向 (scrape_capital_flow.py)

Playwright DOM/API（从官方页面提取）:
  q.10jqka.com.cn 首页 ──→ 涨跌家数/涨停跌停 (scrape_market_breadth.py)
  q.10jqka.com.cn/thshy/ ─→ 行业板块排名 (scrape_thshy.py)
  q.10jqka.com.cn/gn/ ────→ 概念板块排名 (scrape_gn.py)
  paper.people.com.cn ────→ 人民日报头版 (scrape_rmrb.py)

WebSearch（仅新闻）:
  国务院/发改委/央行/财政部/证监会/财联社/央视新闻 (site: 官网限定)
  + CNBC + 全网搜索（国际要闻双通道）→ 8次搜索
  （人民日报由 Playwright 脚本负责，不再走 WebSearch）

读取昨日日报 → 对比分析 → 生成市场观察 ①②③
```

> 为什么用直接 API？新浪 `hq.sinajs.cn` 和东财 `push2.eastmoney.com` 是公开行情 API，返回结构化数据，不存在搜索引擎"找错日期""混入盘中数据"等风险。同花顺数据从页面 DOM/内部 AJAX 提取，不经过搜索引擎，同样零幻觉。

---

## 备用机制（Fallback）

每个脚本输出 JSON 中都有 `source` 字段：

| source 值 | 含义 | 处理方式 |
|-----------|------|----------|
| `direct_api` | 直接 API 获取成功（新浪/东财 HTTP API） | 正常使用 |
| `direct_dom` | 同花顺 DOM/AJAX 提取成功 | 正常使用 |
| `playwright_dom` | Playwright DOM 提取成功（人民日报） | 正常使用 |
| `playwright_fallback` | API 失败，Playwright 回退 | 使用数据但保留 `note` 提示 |
| `fallback_needed` | 完全失败，需 WebSearch | 执行 WebSearch 兜底，**报告中必须标记 `⚠️ 备用数据源`** |

**脚本备用规则：**

1. 如果脚本返回 `fallback_needed`，执行对应 WebSearch（搜索词见下方兜底表）
2. WebSearch 获取的数据在报告中必须标注 `⚠️`，区别于直接 API 数据
3. 涨跌家数/涨停跌停是市场情绪判断的关键输入，备用数据必须标注来源

**新闻搜索备用规则：**

搜索引擎对 `.gov.cn` 域名的索引不稳定——同一搜索词有时返回结果有时不返回。采用**两级回退**：

**第一级：`site:.gov.cn` → `site:news.cn`**

如果 `site:` 搜索返回 **0 条结果**，改用 `site:news.cn`（新华网）重新搜索。新华网是国家通讯社官网，各部委政策全文同步转载，权威性等同 `.gov.cn`，**无需 ⚠️ 标注**。

**第二级：`site:news.cn` → 去 `site:` 自由搜索**

如果 `site:news.cn` 也返回 0 条，去掉 `site:` 限定，用精准关键词搜索。此项在报告中标注 `⚠️`：
```
> ⚠️ 本条来自备用搜索（官网索引暂不可用），非官网直接链接。
```

> 商业站点（`cls.cn` / `cctv.com` / `cnbc.com`）和人民日报电子报（`paper.people.com.cn`，`.com.cn` 域名）索引稳定，基本不需要回退。出问题的主要是 `.gov.cn`。

---

## 执行流程

### 第〇步：交易日判断（最先执行）

在执行任何数据采集之前，先判断今天是否为 A 股交易日：

- **周一至周五**（排除中国法定节假日）→ 交易日 → 执行「交易日流程」
- **周六、周日、法定节假日** → 休市日 → 执行「休市日流程」

> 中国法定节假日包括：元旦、春节、清明节、劳动节、端午节、中秋节、国庆节。春节和国庆节通常休市 5-7 天。遇到调休周末（如节前/节后补班周六），A 股通常仍休市。

---

### 交易日流程

#### 第一步：并行启动全部脚本

同时运行 6 个脚本，互不依赖：

```bash
python scripts/scrape_sina.py            # 指数（直接 API）
python scripts/scrape_market_breadth.py   # 涨跌家数/涨停跌停（DOM）
python scripts/scrape_capital_flow.py     # 北向/南向资金（直接 API）
python scripts/scrape_thshy.py           # 行业板块（AJAX API）
python scripts/scrape_gn.py              # 概念板块（hidden JSON）
python scripts/scrape_rmrb.py            # 人民日报头版（Playwright DOM）
```

脚本位置：`scripts/` 目录下，与 SKILL.md 同级。

### 第二步：新闻搜索（与第一步并行）

全部采用 `site:` 限定官网域名，确保链接一手来源。国际要闻双搜索并行（英文一手 + 中文亚洲视角）。

| 来源 | 搜索词 | 条数 |
|------|--------|------|
| 国务院 | `site:www.gov.cn 要闻 YYYY年MM月DD日` | 3-5 |
| 国家发改委 | `site:www.ndrc.gov.cn 要闻 YYYY年MM月` | 3-5 |
| 中国人民银行（央行） | `site:pbc.gov.cn 新闻 YYYY年MM月` | 3-5 |
| 财政部 | `site:mof.gov.cn 政策 YYYY年MM月` | 3-5 |
| 证监会 | `site:csrc.gov.cn 新闻 YYYY年MM月` | 3-5 |
| 财联社 | `site:cls.cn 财经 要闻 YYYY年MM月DD日` | 3-5 |
| 央视新闻 | `site:cctv.com 要闻 YYYY年MM月DD日` | 2-3 |
| 国际要闻 | ① `site:cnbc.com global markets YYYY年MM月` **+** ② `YYYY年MM月DD日 国际要闻 全球市场 美股 大宗商品 地缘` | 各3-5 |

> **关于 `site:`**：限定搜索引擎只返回该域名的页面，确保新闻链接来自官网而非聚合站/转载站。Token 消耗与不加 `site:` 完全相同。
>
> **关于国际要闻双搜索**：CNBC 是免费开放财经媒体中质量最高的，提供美股/宏观/商品/地缘的一手深度报道；全网搜索补亚洲视角（韩联社、中时、星岛等 CNBC 不覆盖的角度）。两者各取所长。
>
> **关于英文标题**：CNBC 等英文来源的标题必须翻译为中文后再写入报告。翻译格式：`[中文译题]（链接） — 英文原标题`。例如：
> ```
> 1. [伊朗战争100天：全球市场和经济如何被改变（图表）](url) — 100 days of the Iran war: How global markets... in charts
> ```
>
> **关于条数**：人民日报（Playwright 脚本）和央视新闻精简到 2-3 条——重点看头版定调+独家突发，不与其他政策源重复。财联社和四大部委（国务院/央行/财政部/证监会）是市场核心信号源，保持 3-5 条。
>
> **关于人民日报**：已从 WebSearch 切到 Playwright 脚本 `scrape_rmrb.py`——直接打开 `paper.people.com.cn` 电子版头版，DOM 提取 7 篇标题和链接。输出 ~200 tokens，比 WebSearch（~3000 tokens）省 ~2800 tokens/次。链接仍是 `paper.people.com.cn` 官方域名。

### 第三步：处理备用数据源

检查第一步输出的 `source` 字段。对 `fallback_needed` 的数据项执行 WebSearch 兜底：

| 失败脚本 | WebSearch 兜底词 |
|----------|-----------------|
| scrape_sina (all_failed) | `YYYY年MM月DD日 A股收盘 上证指数 深证成指 创业板指 科创50 涨跌幅 成交额` |
| scrape_market_breadth | `YYYY年MM月DD日 A股收盘 上涨家数 下跌家数 涨停 跌停` |
| scrape_capital_flow | `YYYY年MM月DD日 北向资金 主力资金净流入 行业资金流向` |
| scrape_thshy | `YYYY年MM月DD日 A股行业板块涨跌幅排名` |
| scrape_gn | `YYYY年MM月DD日 A股概念板块涨跌幅排名` |
| scrape_rmrb | `site:paper.people.com.cn 人民日报 YYYY年M月 要闻` |

> 注意：创业板指/科创50 不再需要单独搜索——新浪 API 已包含。只有 `scrape_sina.py` 返回 `all_failed` 或 `playwright_fallback` 时才需要 WebSearch 补全。
> 
> `scrape_rmrb.py` 的 fallback 是 `site:` 搜索（不加 `site:` 时混入大量转载站，不要用），且无需降级到去 `site:` 自由搜索——`paper.people.com.cn` 索引稳定。

### 第四步：合并板块排名

将行业板块和概念板块合并为全部板块涨跌榜：

1. 合并两个脚本的 `top` 列表，统一按 `change` 降序排列，取**前 5 名**为涨幅榜
2. 合并两个脚本的 `bottom` 列表，统一按 `change` 升序排列（跌幅最大排第1），取**前 5 名**为跌幅榜
3. 每项保留 `name`、`change` 和 `type`（标记为"行业"或"概念"）
4. 板块名称原样保留，不自行归类改名

> 全部混排的意义：行业和概念同台比较，全面反映资金流向。

### 第五步：数据校验

写入报告前逐条自检：

**来源追溯（防幻觉核心）**：
- 直接 API/DOM 数据天然防幻觉
- 备用 WebSearch 获取的每个数字必须在搜索结果原文中找到对应出处，找不到的填 `无法获取`
- 新闻链接必须是搜索返回的真实 URL

**容易出错的陷阱**：
- 盘中数据 ≠ 收盘数据（午评和收评数值不同）→ 只用明确标注"收盘"的数据
- 前一日数据 ≠ 当日数据（历史对比文章）→ 核对文章日期
- 板块名称不能自己归类改名 → 同花顺用什么名就用什么名

**合理性抽查**：
- 涨跌幅 ±20% 以内（指数 ±10%）
- 成交额 5000 亿 - 5 万亿
- 涨跌家数之和 ≈ 5000-5500

### 第六步：市场观察分析

采集完当日数据后，读取昨日日报文件（昨日），对比两日数据，输出 3 个标签化模块。**禁止长段分析叙述，只输出结构化标签。**

#### ① 结构变化（Market Structure Shift）

对比昨日 vs 今日，输出一张表格，4 个标签：

| 标签 | 可选值 | 判断依据 |
|------|--------|----------|
| **风格** | 蓝筹主导 / 小盘活跃 / 成长主导 / 防御为主 / 混合 | 沪深300 vs 创业板涨跌幅对比，权重股 vs 题材股表现 |
| **主线** | 维持 / 切换 / 弱化 / 新现 | 昨日领涨板块今日是否延续；是否出现全新领涨方向 |
| **情绪** | 恐慌 / 低迷 / 修复 / 积极 / 亢奋 | 涨跌家数比、涨停/跌停比、成交额变化方向 |
| **结构** | 普涨 / 普跌 / 分化 / 单边上涨 / 单边下跌 | 上涨 vs 下跌家数对比 |

输出格式：
```
| 风格 | 主线 | 情绪 | 结构 |
|------|------|------|------|
| xxx | xxx | xxx | xxx |
```

#### ② 资金行为（Capital Flow Behavior）

基于今日数据，输出一张表格，3 个标签：

| 标签 | 可选值 | 判断依据 |
|------|--------|----------|
| **风险偏好** | 上升 / 下降 / 平稳 | 涨停/跌停比、涨跌家数比 vs 昨日变化 |
| **主导资金** | 机构 / 游资 / 混合 | 大金融/权重股涨幅 vs 题材股活跃度；北向资金流向 |
| **资金行为** | 高切低 / 追涨 / 轮动 / 防御 / 进攻 | 领涨板块是低位周期还是高位题材；跌幅榜是否前期热门 |

输出格式：
```
| 风险偏好 | 主导资金 | 资金行为 |
|----------|----------|----------|
| xxx | xxx | xxx |
```

#### ③ 驱动因素（Market Drivers）

对今日市场变化总结最多 **3 条**核心驱动，每条一行，格式为：

```
- ① 分类 → 原因 → 结果
```

分类必须从以下 4 个中选取：**政策因素 / 国际因素 / 情绪资金因素 / 外部市场因素**

要求：
- 不超过 3 条
- 必须有因果链（因为 X → 所以 Y）
- 不罗列新闻标题

---

### 休市日流程

当第〇步判断为休市日时，**只采集当日新闻，不采集任何市场数据，不读取本地文件**。

#### 休市日报 = 今日新闻 + 休市标注

只做两件事——脚本拿人民日报头版 + 搜索其余新闻：

1. 先运行 `python scripts/scrape_rmrb.py`（Playwright，~200 tokens → 7 篇头版标题+链接）
2. 并行搜索其余 8 个新闻源，全部 `site:` 官网限定：

| 来源 | 搜索词 | 条数 |
|------|--------|------|
| 人民日报 | `python scripts/scrape_rmrb.py`（Playwright DOM）→ fallback: `site:paper.people.com.cn 人民日报 YYYY年M月 要闻` | 2-3 |
| 国务院 | `site:www.gov.cn 要闻 YYYY年MM月DD日` | 3-5 |
| 国家发改委 | `site:www.ndrc.gov.cn 要闻 YYYY年MM月` | 3-5 |
| 中国人民银行（央行） | `site:pbc.gov.cn 新闻 YYYY年MM月` | 3-5 |
| 财政部 | `site:mof.gov.cn 政策 YYYY年MM月` | 3-5 |
| 证监会 | `site:csrc.gov.cn 新闻 YYYY年MM月` | 3-5 |
| 财联社 | `site:cls.cn 财经 要闻 YYYY年MM月DD日` | 3-5 |
| 央视新闻 | `site:cctv.com 要闻 YYYY年MM月DD日` | 2-3 |
| 国际要闻 | ① `site:cnbc.com global markets YYYY年MM月` **+** ② `YYYY年MM月DD日 国际要闻 全球市场 美股 大宗商品 地缘` | 各3-5 |

生成纯新闻日报，**不含市场数据**：

```markdown
# 📊 A 股市场日报

**日期**：YYYY年MM月DD日（星期X）🔴 休市
**生成时间**：{{TIME}}

---

## 📰 时政要闻

（9个来源的今日新闻，格式与交易日一致）

---

> 📌 今日休市，股市数据见 [[{{LAST_TRADING_DATE}}/收盘日报|上一交易日报告]]。
```

**查找上一交易日文件名**：用 Glob 列出 `*/收盘日报.md`，按目录日期倒序取第一条，提取其日期填入 `[[YYYY-MM-DD/收盘日报]]`。

> 不需要读取文件内容——Glob 只返回文件名，消耗极低。双链语法 `[[...]]` 是 Obsidian 原生内部链接，约 50 字符 ≈ 12 tokens。

---

## 报告生成

参考 `assets/report_template.md` 的模板结构。模板使用 `{{VARIABLE}}` 占位符，将其替换为采集到的实际数据。

文件名：`YYYY-MM-DD\收盘日报.md`
保存路径：`E:\IDEA\cc\Personal Cognitive OS\00_每日笔记`

**颜色规则**（A 股特色）：🔴 上涨 / 🟢 下跌（红涨绿跌，与国际惯例相反）

**跌幅榜排序**：按跌幅从大到小倒序排列，跌幅最大的排第 1 名。

**备用数据源标注**：任何通过 WebSearch 兜底获取的市场数据（指数、涨跌家数、资金流向、板块排名），在该数据项的表格下方添加一行：
```
> ⚠️ 备用数据源：因直接 API 不可用，此项通过搜索引擎获取，数据可能受搜索时效性影响。
```

---

## 目录结构

```
信息采集/
├── SKILL.md                    # 本文件（流程说明）
├── scripts/
│   ├── scrape_sina.py          # 指数数据（直接 API → Playwright 回退）
│   ├── scrape_market_breadth.py # 涨跌家数/涨停跌停（同花顺 DOM）
│   ├── scrape_capital_flow.py  # 北向/南向资金（东财 API）
│   ├── scrape_thshy.py         # 行业板块（同花顺 AJAX API）
│   ├── scrape_gn.py            # 概念板块（同花顺 hidden JSON）
│   └── scrape_rmrb.py          # 人民日报头版（Playwright DOM）
├── assets/
│   └── report_template.md      # 报告模板
└── evals/
    └── evals.json              # 测试用例
```
