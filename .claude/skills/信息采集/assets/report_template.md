# 📊 A 股市场日报

**日期**：{{DATE}}（{{WEEKDAY}}）
**生成时间**：{{TIME}}

---

## 📰 时政要闻

### 人民日报
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

### 央视新闻
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

### 国务院
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

### 国家发改委
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

### 中国人民银行（央行）
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

### 财政部
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

### 国际要闻
1. [标题](链接)
2. [标题](链接)
3. [标题](链接)

---

## 📈 主要指数

<!-- 颜色规则：🔴上涨 🟢下跌；变量含正负号和颜色emoji，如 "🔴 +1.23%" -->
| 指数 | 收盘点位 | 涨跌幅 |
|------|----------|--------|
| 上证指数 | {{SH_PRICE}} | {{SH_CHANGE}} |
| 深证成指 | {{SZ_PRICE}} | {{SZ_CHANGE}} |
| 创业板指 | {{CY_PRICE}} | {{CY_CHANGE}} |
| 科创50 | {{KC_PRICE}} | {{KC_CHANGE}} |

{{INDEX_FALLBACK_NOTE}}
<!-- 如果指数数据来自备用WebSearch，在此处插入: > ⚠️ 备用数据源：指数数据通过搜索引擎获取 -->

---

## 📊 市场概况

| 指标 | 数据 |
|------|------|
| 今日两市总成交额 | {{TODAY_VOLUME}} |
| 昨日两市总成交额 | {{YESTERDAY_VOLUME}} |
| 上涨家数 | {{UP_COUNT}} |
| 下跌家数 | {{DOWN_COUNT}} |
| 涨停家数 | {{ZT_COUNT}} |
| 跌停家数 | {{DT_COUNT}} |

{{BREADTH_FALLBACK_NOTE}}
<!-- 如果涨跌家数来自备用WebSearch，在此处插入备用数据源标注 -->

---

## 💰 资金流向

### 北向资金（外资 → A股）

| 通道 | 买入 | 卖出 | 净流入 | 成交额 |
|------|------|------|--------|--------|
| 沪股通 | {{N_HK2SH_BUY}} | {{N_HK2SH_SELL}} | {{N_HK2SH_NET}} | {{N_HK2SH_TURNOVER}} |
| 深股通 | {{N_HK2SZ_BUY}} | {{N_HK2SZ_SELL}} | {{N_HK2SZ_NET}} | {{N_HK2SZ_TURNOVER}} |
| **北向合计** | | | **{{N_NORTH_NET}}** | **{{N_NORTH_TURNOVER}}** |

### 南向资金（内资 → 港股）

| 通道 | 买入 | 卖出 | 净流入 | 成交额 |
|------|------|------|--------|--------|
| 沪港通 | {{N_SH2HK_BUY}} | {{N_SH2HK_SELL}} | {{N_SH2HK_NET}} | {{N_SH2HK_TURNOVER}} |
| 深港通 | {{N_SZ2HK_BUY}} | {{N_SZ2HK_SELL}} | {{N_SZ2HK_NET}} | {{N_SZ2HK_TURNOVER}} |
| **南向合计** | | | **{{N_SOUTH_NET}}** | **{{N_SOUTH_TURNOVER}}** |

{{CAPITAL_FALLBACK_NOTE}}
<!-- 如果资金数据来自备用WebSearch，在此处插入备用数据源标注 -->

---

## 🔥 板块涨跌榜（同花顺全部板块混排）

> 合并同花顺行业板块（{{HY_COUNT}}个）和概念板块（{{GN_COUNT}}个），统一按涨跌幅排序。

### 🔴 涨幅前 5

<!-- 按涨幅从大到小排列；变量含正负号、颜色emoji和%号，如 "🔴 +5.63%" -->
| 排名 | 板块 | 类型 | 涨幅 |
|------|------|------|------|
| 1 | {{UP1_NAME}} | {{UP1_TYPE}} | {{UP1_CHANGE}} |
| 2 | {{UP2_NAME}} | {{UP2_TYPE}} | {{UP2_CHANGE}} |
| 3 | {{UP3_NAME}} | {{UP3_TYPE}} | {{UP3_CHANGE}} |
| 4 | {{UP4_NAME}} | {{UP4_TYPE}} | {{UP4_CHANGE}} |
| 5 | {{UP5_NAME}} | {{UP5_TYPE}} | {{UP5_CHANGE}} |

### 🟢 跌幅前 5

<!-- 按跌幅从大到小倒序排列（跌幅最大的排第1）；变量含正负号、颜色emoji和%号，如 "🟢 -3.98%" -->
| 排名 | 板块 | 类型 | 跌幅 |
|------|------|------|------|
| 1 | {{DOWN1_NAME}} | {{DOWN1_TYPE}} | {{DOWN1_CHANGE}} |
| 2 | {{DOWN2_NAME}} | {{DOWN2_TYPE}} | {{DOWN2_CHANGE}} |
| 3 | {{DOWN3_NAME}} | {{DOWN3_TYPE}} | {{DOWN3_CHANGE}} |
| 4 | {{DOWN4_NAME}} | {{DOWN4_TYPE}} | {{DOWN4_CHANGE}} |
| 5 | {{DOWN5_NAME}} | {{DOWN5_TYPE}} | {{DOWN5_CHANGE}} |

{{SECTOR_FALLBACK_NOTE}}
<!-- 如果板块数据来自备用WebSearch，在此处插入备用数据源标注 -->

---

## 🔍 市场观察

### ① 结构变化

| 风格 | 主线 | 情绪 | 结构 |
|------|------|------|------|
| {{STRUCT_STYLE}} | {{STRUCT_THREAD}} | {{STRUCT_SENTIMENT}} | {{STRUCT_PATTERN}} |

### ② 资金行为

| 风险偏好 | 主导资金 | 资金行为 |
|----------|----------|----------|
| {{CAP_RISK}} | {{CAP_LEADER}} | {{CAP_BEHAVIOR}} |

### ③ 驱动因素

{{DRIVER_LIST}}

---

> ⚠️ 数据来源：市场数据 — 同花顺 DOM/API（板块排名/涨跌家数）、新浪 `hq.sinajs.cn`（指数/成交额）、东方财富 `push2.eastmoney.com`（资金流向）；新闻 — 国务院/发改委/央行/财政部/证监会/财联社/人民日报/央视新闻（WebSearch `site:` 官网限定）+ CNBC/全网（国际要闻双搜索）。数据仅供参考，不构成投资建议。
