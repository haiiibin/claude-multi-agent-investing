---
description: 全组合多智能体周报 -- 并行运行所有分析师和人格智能体，交叉比对 YouTube 信号，生成统一投资建议并自动推送 Notion。
---

# /weekly-brief -- 全组合智能体综合简报

并行调度所有子智能体，交叉比对 YouTube 频道最新信号，对每个持仓给出统一行动建议，并自动推送 Notion 投资日志。

## 参数

- 无参数 → 全组合简报（所有持仓 + 关键自选股）
- `focus TICKER1 TICKER2` → 对指定标的深度分析，其余轻量过一遍

---

## 第 0 步 -- 加载上下文（并行前必须先完成）

1. 读取 `portfolio/holdings.json`：
   - 提取所有持仓 ticker（CDR 解析：NVDA.NE → NVDA，COST.NE → COST）
   - 提取自选股前 5 条（按 price_snapshot.date 最近排序）
   - 记录各账户类型和当前现金余额
2. 扫描 `memory/short_term/` 目录，找出近 14 天内已有转录文件（`audio_*_transcript.txt`）的视频 ID -- 这些无需重复转录。
3. 建立 **主标的列表** = 持仓 ticker + 自选股 ticker（去重）。

---

## 第 1 步 -- 并行数据采集（全部同时发起，不等待任何一个完成）

以下任务**全部并行**：

### A. YouTube RSS 抓取（5 个频道同时 WebFetch）

| 频道 | RSS |
|---|---|
| 阳光财经 | `https://www.youtube.com/feeds/videos.xml?channel_id=UC2I5em6UyBpQiO-8ZW0nV3w` |
| 视野环球财经 | `https://www.youtube.com/feeds/videos.xml?channel_id=UCFQsi7WaF5X41tcuOryDk8w` |
| 美投君 | `https://www.youtube.com/feeds/videos.xml?channel_id=UCBUH38E0ngqvmTqdchWunwQ` |
| 美投News | `https://www.youtube.com/feeds/videos.xml?channel_id=UCGpj3DO_5_TUDCNUgS9mjiQ` |
| 贝拉聊财金 | `https://www.youtube.com/feeds/videos.xml?channel_id=UCVomjkM_t0EcctTWSE1Jvxg` |

提取格式：`VIDEO_ID | YYYY-MM-DD | 标题`（来自 `<yt:videoId>` 标签）。
只保留近 14 天内的视频，排除已有转录文件的 ID。

### B. 宏观快照（调度 `macro-analyst` 子智能体）

调用 Agent 工具，subagent_type=macro-analyst，简报：
> 拉取 SPY/QQQ/VIX/^TNX/DXY/CL=F/GC=F/CAD=X 的 1日、1月、3月涨跌幅。识别当前市场 regime。用 `python tools/polymarket.py` 查询 Fed + 关税 + 衰退市场的预测概率。包含 USD/CAD。返回 JSON（按 macro-analyst agent spec）。

### C. 新闻扫描（调度 `news-analyst` 子智能体）

调用 Agent 工具，subagent_type=news-analyst，简报：
> 对以下标的拉取最近新闻：{主标的列表}。每个标的打情绪分，标出高重要性事件（财报、分析师评级变化、产品发布、监管动作）。返回 JSON（按 news-analyst agent spec）。

### D. 基本面快照（调度 `fundamentals-analyst` 子智能体）

调用 Agent 工具，subagent_type=fundamentals-analyst，简报：
> 对每个持仓标的，拉取：前瞻/追踪 PE、PEG、营收同比增速、毛利率、FCF yield、债务/权益比、分析师共识评级。异常指标高亮。返回紧凑表格。

### E. 财报日历（WebSearch + earnings 数据）

查询主标的列表中未来 21 天内的财报日期：
```
WebSearch: "{ticker} earnings date Q2 2026"
```
或使用 `mcp__yahoo-finance__get_stock_info` 的 `earningsDate` 字段。

输出格式：`TICKER | 预计财报日期 | 预期 EPS | 上季度实际 vs 预期`

财报前 5 天内的持仓标的在第 5 步中高亮标注为 ⚠️ 即将财报。

等待第 1 步全部完成后继续。

---

## 第 2 步 -- 顺序转录（CPU 密集，必须逐个执行）

对第 1A 步识别出的每个新视频 ID，逐个运行：

```bash
python tools/transcribe.py {VIDEO_ID}
```

每个 30 分钟视频约需 2–5 分钟。转录完成后立即读取生成的 `.txt` 文件。

---

## 第 3 步 -- 并行人格分析（全部同时发起）

对每个**持仓标的**，同时调度 7 个子智能体（全部 background=true）：

| 子智能体 | 职责 |
|---|---|
| `buffett` | 护城河 + 内在价值 + 安全边际 |
| `munger` | 反共识检验 + 六项红旗清单（会计、债务、护城河侵蚀、管理层、周期盲区、能力圈） |
| `burry` | 逆向思维 + 系统性风险识别 |
| `bull` | 构建最强买入理由 |
| `bear` | 构建最强卖出理由 |
| `technical-analyst` | 价格行为 + MA20/50/200 趋势栈 + RSI/MACD/Bollinger/ATR + 关键支撑阻力位 |
| `risk-analyst` | 5 维量化风险评分（市场波动、集中度、汇率、税务账户、基本面）+ 缓释建议 |

调用方式：Agent 工具，每个 subagent_type 对应，run_in_background=true，prompt 包含：目标 ticker、持仓成本、当前账户类型、持仓规模。

对**自选股**（前 5 只）：仅调度 `bull` + `bear` + `munger` + `technical-analyst`（技术面过滤入场时机）。

> ⚠️ **sec-filings-analyst 不在本命令运行**：读取真实 SEC 文件耗时过长（每支 10-20 分钟），仅在 `/deep-dive TICKER` 中单独调用。如需对某个持仓做 SEC 核查，在周报完成后手动运行 `/deep-dive`。

收集所有智能体结果后继续。

---

## 第 4 步 -- YouTube 信号提取

汇总所有转录文本（已有 + 新转录），对每条提取：
- **核心论点**（1 句话）
- **提及标的** + 方向信号（+/−/=）
- **关键数据点**（价格、%、财报数字）
- **催化剂 / 时间框架**

构建**频道信号矩阵**：标的 → [频道, 信号, 日期]

---

## 第 5 步 -- 统一综合

汇总所有输入：

```
每个持仓标的的共识块：

TICKER
├─ 宏观适配：[有利 / 中性 / 阻力]        ← macro-analyst
├─ 基本面：[关键指标异常]                 ← fundamentals-analyst
├─ 新闻情绪：[分数 + 高重要事件]          ← news-analyst
├─ Buffett：[信号 + 置信度]
├─ Burry：[信号 + 置信度]
├─ Bull / Bear：[信号 + 核心论点]
├─ 技术面：[趋势栈 + RSI + MACD + 关键位] ← technical-analyst
├─ 风险评分：[总分/25 + 最高维度]         ← risk-analyst（5维 1-5分，满分25）
├─ YouTube：[提及频道 + 方向]
└─ 终审：[Buy / Overweight / Hold / Underweight / Sell + 置信度%] ← portfolio-manager
```

**portfolio-manager 调用（第 5 步末尾，逐个持仓串行）**：
将上述共识块的全部 agent 输出传入 `portfolio-manager` 子智能体（subagent_type=portfolio-manager），让其输出 5 级评级 + 账户路由 + 高风险门控检查。周报最终行动建议以 portfolio-manager 输出为准。

然后生成：
1. **持仓行动表**（按紧迫程度排序，评级来自 portfolio-manager）
2. **压力测试快照**（3 个关键情景，参考 `/stress-test` 逻辑）：
   - 情景 A：关税升级 / 中美贸易恶化 → 各持仓预估损失 %
   - 情景 B：美联储意外加息或维持高利率 → 高估值成长股影响
   - 情景 C：AI capex 泡沫破裂信号出现 → 半导体 + AI 主题仓位
   每个情景只需 1-2 句影响判断，不需要完整 `/stress-test` 深度。
3. **现金部署建议**（结合当前现金 + 宏观 regime + 账户税务规则）
4. **自选股入场信号**（任何自选股出现明显入场机会？参考 technical-analyst 入场时机）
5. **本周关键风险**（宏观事件 + 第 1E 步财报日历 + ⚠️ 即将财报标的高亮）
6. **智能体分歧点**（哪些标的智能体意见分裂？munger 和 bull 分歧最有参考价值；technical 与 fundamentals 背离也需标注）
7. **风险热力表**（risk-analyst 各持仓总分排序 -- 总分 ≥ 15/25 高亮为 ⚠️）

**税务路由**：任何 Add/Trim 建议都必须标明账户（按 holdings.json 中的账户 id，如 broker-a-taxable / broker-b-tfsa / broker-b-taxable），并引用 CLAUDE.md 路由规则。

---

## 第 6 步 -- 保存并推送 Notion（Notion 推送为可选步骤）

**保存到本地（始终执行）：**
```
memory/short_term/{YYYY-MM-DD}-weekly-brief.md
```

**推送 Notion 日志（仅当仓库根目录存在 notion_config.json 时执行；该文件由 notion_config.example.json 复制并填入你自己的 token。未配置则跳过本节，只保留本地文件）：**
```bash
# 从仓库根目录运行
python tools/notion_push.py journal \
  "{YYYY-MM-DD} Weekly Portfolio Brief" \
  "{第5步完整综合文本}" \
  "YouTube Pulse" \
  "{所有持仓 ticker，逗号分隔}" \
  "{总体信号: Bullish|Bearish|Neutral}"
```

**同步持仓表（同样仅在已配置 notion_config.json 时执行）：**
```bash
python tools/notion_push.py sync
```

---

## 输出格式

```markdown
# 📊 Weekly Portfolio Brief -- {YYYY-MM-DD}

## 宏观环境
[Regime 判断 + 关键数据 + 近期催化剂]

## 持仓建议

| 持仓 | 宏观适配 | 基本面 | 新闻 | 人格共识(5) | 技术面 | 风险分 | YouTube | 终审 |
|---|---|---|---|---|---|---|---|---|
| NVDA | ✅ 有利 | PE 42x 正常 | 中性 | 看涨 4/5，munger 中性 | 看涨 72% | 11/25 | 贝拉+视野 (+) | **Hold 68%** |
| TSLA | ⚠️ 阻力 | FCF 负 | 偏空 | 看跌 4/5 | 中性 | 18/25 ⚠️ | 视野 (−) | **Underweight 75% @ broker-a-taxable** |

## 风险热力表
[各持仓 risk-analyst 总分 / 25，≥15 标 ⚠️]

## 现金部署
[各账户现金 + regime 匹配建议 + 分批计划]

## 自选股信号
[有入场机会的自选股 + 技术面入场时机 + 理由]

## 本周关键风险
[宏观事件 + 财报日期 + 地缘触发点]

## 智能体分歧
[分歧最大的标的 + 多空核心论点对比；技术面与基本面背离单独标注]
```

---

## 规则

- **并行优先**：第 1 步和第 3 步必须同时发起 -- 能并行的绝不串行。portfolio-manager 在第 5 步末尾串行逐仓调用（需要接收其他 agent 输出后才能综合）。
- **禁止捏造**：所有智能体输出必须基于工具调用返回的真实数据。
- **YouTube 是观点，不是事实**：频道信号明确标注为创作者意见，非价格目标。
- **税务意识**：每个 Add/Trim 建议必须标明账户路由，遵循 CLAUDE.md 规则。portfolio-manager 的输出中必须包含账户字段。
- **高风险门控**：触发 CLAUDE.md 高风险条件（单笔 >5% 组合、集中度 >12% 等）的建议必须标 DRAFT。portfolio-manager 已内置门控逻辑，但主流程也须二次确认。
- **risk-analyst 热力图阈值**：总分 ≥ 15/25（满分）在输出中标 ⚠️；≥ 20/25 标 🔴 HIGH-RISK。
- **Notion 推送为可选**：仅当仓库根目录存在 notion_config.json（由 notion_config.example.json 复制并填好 token）时才推送；未配置则跳过，仅保存本地文件。
- **输出语言**：综合报告用中文。智能体 JSON 块保持英文（按各 agent spec）。
