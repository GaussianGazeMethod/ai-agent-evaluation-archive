# chapter1 实验总结报告

**报告对象**：`chapter1`（第 1 章 Agent 基础）下有实测数据支撑的 4 个子实验
**生成时间**：2026-11-05
**数据来源**：各子项目已产出的分析报告、评测报告与结果文件（见文末证据索引）。本报告对关键指标逐一回读结果文件核对，不以文档中的结论表述为准。

> 排除说明：本章 4 个子项目全部有独立的测试/评测报告，均纳入本报告。

---

## 一、总览

| 实验 | 验证命题 | 模型 / 规模 | 样本量 | 实测结论 | 证据强度 |
|---|---|---|---|---|---|
| `context` | 消融 Agent 上下文组件后任务完成能力的变化 | deepseek-v3，5 种消融 × 3 套任务 | 15 组单例 | **原始判定 86.7%（FINAL ANSWER 字符串匹配）→ 真实判定 53.3%（6 维内容校验）**；5/15 次为假成功 | 高（JSON + 完整轨迹 + 校验器三层证据） |
| `learning-from-experience` | LLM 上下文学习 vs Q-Learning 的样本效率 | GLM-5（20 局训练 + 10 局评估）vs Q-Learning（5000 局训练 + 100 局评估） | 两侧样本量不对称 | 训练 LLM 100% vs RL 0.02%；**评估 LLM 30% vs RL 0%**；训练→评估 LLM 掉 70 pp | 中（训练侧结论可靠，评估侧 10 局置信区间宽） |
| `search-codegen` | 百炼 Responses API + qwen3.7-plus 能否对齐 GPT-5 原生工具设计 | qwen3.7-plus，8 组用例 × 单轮 | 8 用例 | web_search / code_interpreter 完整可用；推理力度对比设计有缺陷 | 中（能力验证可靠，耗时/token 无重复） |
| `web-search-agent` | Kimi API 内置 `$web_search` 工具端到端可用性 | kimi-k3 → kimi-k2.6（平台 bug 规避），7 次运行 | 7 次运行（前 5 失败） | kimi-k3 + `$web_search` 第二轮必然 400（平台 bug）；kimi-k2.6 完整跑通 | 中高（7 次运行有完整日志与代码修改清单） |

一句话总结：**4 个实验里，1 个发现了 Agent 评测里最常见的假信号（"模型说 FINAL ANSWER 就算成功"的致命缺陷），1 个给出了经典 RL vs LLM 对照且暴露了训练-评估落差，1 个做了平台迁移的能力对齐验证，1 个完整记录了"5 次失败→2 次成功"的真实排障过程。最值得记录的是：四个实验里有三个碰到了"推理模型 temperature 限制"与"平台工具兼容性 bug"——这类基础设施问题比算法调优更先成为阻塞。**

---

## 二、context：五次假成功暴露评测协议的致命缺陷

### 2.1 设计

跨国公司 Q1 2024 区域费用分析任务：解析 PDF、换算 GBP/JPY/EUR/SGD → USD、计算总额/均值/占比、按 8% 削减后回兑。五种上下文消融模式：

| 模式 | 理论消融对象 | 实际效果 |
|---|---|---|
| `full` | 无（对照组） | 基准 |
| `no_history` | 历史工具调用记录 | **未生效**：`execute_task` 直接用完整 `conversation_history` |
| `no_reasoning` | 模型推理过程 | **空操作**：deepseek-v3 无 `reasoning_content` 字段 |
| `no_tool_calls` | 工具调用能力 | 真实消融：不传 `tools` / `tool_choice` |
| `no_tool_results` | 工具返回结果 | 真实消融：工具照常执行，回填占位符 |

**三套渐进运行**：

| 轮次 | 输入 | 结果 JSON 完整性 | 校验来源 |
|---|---|---|---|
| 纯文本 V1 | 任务内联金额 | 缺轨迹与完整答案 | verbose 日志离线回放 + 旧 GT |
| PDF V1 | 本地 PDF | 缺轨迹与完整答案 | verbose 日志离线回放 + 错误 GT |
| PDF V2 | 本地 PDF | **完整轨迹 + FINAL ANSWER 全文 + validation** | 运行时直接产出 |

**两套判定口径**：
- **原始判定**：只要模型输出 `FINAL ANSWER:` 就算成功。
- **真实判定**：6 维内容校验全部通过才算成功。

运行日期 2026-08-11，Provider dashscope（阿里百炼 OpenAI 兼容端点）。

### 2.2 实测数据

三套实验共 15 组，原始判定成功 13 组（86.7%），真实判定成功 8 组（53.3%），假成功 5 组。以下以 PDF V2 为主（唯一可信），辅以 V1/纯文本 V1：

**PDF V2（运行时完整轨迹）**

| 模式 | 原始 | 真实 | C1 | C2 | C3 | C4 | C5 | C6 | 耗时(s) | 迭代 | 工具序列 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|---:|---|---|
| full | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 33.72 | 5 | parse_pdf → convert×4 → code_interpreter → convert×4 |
| no_history | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 28.02 | 4 | parse_pdf → convert×4 → code_interpreter |
| no_reasoning | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | 31.17 | 4 | 同 no_history（空操作） |
| no_tool_calls | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | 29.94 | 1 | 空 |
| no_tool_results | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | 14.25 | 3 | parse_pdf（结果被隐藏） |

**假成功案例**：

| 实验 | 模式 | 声称总额 | GT 总额 | 偏差 | 编造区域 |
|---|---|---:|---:|---|---|
| PDF V1 | no_tool_calls | $37,859 | $11,990,955 | 316 倍 | North America / Europe / Asia / Australia |
| PDF V2 | no_tool_calls | $15,200 | $11,990,955 | 789 倍 | NorthAmerica / Europe / Asia / UK / Canada |
| PDF V1 | no_tool_results | 千级 | 千万级 | 量级错误 | North America / Asia / Australia |
| PDF V2 | no_tool_results | — | — | — | 输出 "Please provide the PDF..." |
| PDF V2 | no_reasoning | — | — | — | 工具轨迹正确，但 FINAL ANSWER 写 "as detailed above" |

**GT 修正历程**：V1 用 SGD=1.35 → GT $11,973,266；V2 用错误 China+Germany 区域 → GT $12,154,620；最终修正为 `agent.py` 实际汇率 + 真实 PDF 区域 → GT $11,990,955.43。

### 2.3 结论

1. **"FINAL ANSWER 字符串匹配"是不可接受的成功判定**。15 组中原始判定比真实判定高 33.4 个百分点，假成功全部出现在被消融的模式上。`no_tool_calls` 编造完整假报表且秒交卷；`no_tool_results` 工具日志全绿但产出物是推诿。

2. **工具调用是硬约束，工具结果是更隐蔽的软约束**。`no_tool_calls` 的假成功最显眼（数字偏差 300~800 倍），`no_tool_results` 更危险（工具全绿 → 生产监控以为正常 → 实际上毫无产出）。

3. **两次名义上的消融（no_history / no_reasoning）实际是空操作**。前者因 `execute_task` 直接跳过 `_build_context` 的组装逻辑；后者因 deepseek-v3 没有 `reasoning_content` 字段。这两组数据不能用于"去掉历史/去掉推理过程"的消融结论。

4. **交付格式必须约束 FINAL ANSWER 携带关键字段**。PDF V2 的 full 模式用正确的工具序列算出 $11,990,955.43，但 FINAL ANSWER 被压缩成 326 字符的摘要；no_history 模式（同样正确的工具序列）却把总额、均值、5 个削减后金额全部自报家门。两者校验结果因此不同——这是协议设计问题，不是模型能力问题。

5. **同一消融模式在不同运行上的行为不可预测**。纯文本 V1 的 `no_tool_calls` 死循环 10 轮不交卷；PDF V1/V2 各自 1 轮内编造出一份数字不同的假报表。不能指望模型稳定地承认"我做不到"。

### 2.4 局限与问题

- **校验器 C5（编造区域检测）已失效**。别名表只做"期望区域的别名是否出现"的正向检查，不做"出现的区域是否全部属于期望集合"的反向检查。模型编造 NorthAmerica / Asia / Canada / Australia 时，这些新区域名永远不会被判为 extra。
- **前两套 JSON 缺 trajectory 序列化**。纯文本 V1 和 PDF V1 的 JSON 只有 `num_tool_calls` 整数，没有完整工具轨迹和 FINAL ANSWER 全文，校验必须从 verbose 日志离线回放（可能有精度损失）。只有 PDF V2 的 JSON 是自包含的。
- **GT 经历了三个版本演进**。V1 与 V2 的 GT 与 agent.py 实际汇率不一致，虽不影响 C4（偏差均在 ±20% 阈值内），但 C5 的"错误通过"与此有关。
- 没有重复实验。每模式单例运行，无法区分模型行为与采样随机性。
- 没有运行时 token 消耗与 API 调用计数，成本指标只能从日志估算。

---

## 三、learning-from-experience：LLM 省 250 倍样本，训练→评估掉 70 个百分点

### 3.1 设计

文本寻宝游戏（TreasureHuntGame，确定性环境），四类隐藏机制不告知 Agent：颜色对应钥匙开门、武器对不同敌人有效、物品合成配方、药水临时增益。胜利条件是背包里出现 `dragon's treasure`（+100 奖励），步数上限 50，每步移动 -0.5。单局理论满分约 250。

**两组对照**：

| 维度 | Q-Learning Agent | GLM-5 上下文学习 Agent |
|---|---|---|
| 训练局数 | 5000 | 20 |
| 评估局数 | 100 | 10 |
| 温度 | ε-greedy（初始 1.0 → 下限 0.1） | 0.7（非 reasoning 模型，保持） |
| 学习方式 | 表格型 Q-Learning + 折扣 γ=0.99 | 上下文内经验累积，零参数更新 |
| 知识载体 | Q 表状态哈希 | 最多 100 条经验（最近 50 条成功 + 最近 25 条失败） |

运行时间 2026-08-14 00:58 ~ 02:54。

Kimi K2.5 的同类运行：用旧版代码（`max_tokens=500`）训练 20 局全胜，但评估阶段因 reasoning 输出被截断（500 tokens 不够思考链 + `ACTION:` 行）触发 fallback 连锁，步数膨胀到 30-50 步后被中断；该模型的结果无独立落盘、无可复算。

### 3.2 实测数据

**核心对比（JSON 权威）**：

| 指标 | Q-Learning | GLM-5 | 对比 |
|---|---|---|---|
| 训练局数 | 5000 | 20 | LLM 省 250 倍 |
| 训练耗时 | 2.39 秒 | 6960.32 秒（1h56m） | RL 快约 2910 倍 |
| 训练胜场/胜率 | 1 / 0.02% | 20 / 100% | — |
| 训练平均奖励 | 15.2 | 239.35 | LLM +224.2 |
| 训练平均步数 | 50.0（全部跑满） | 15.2 | LLM 少 34.8 步 |
| 评估胜场/胜率 | 0 / 0% | 3 / 30% | LLM 唯一有效者 |
| 评估平均奖励 | -44.0 | 86.1 | LLM +130.1 |
| 评估平均步数 | 50.0（全部超时） | 39.0 | LLM 少 11 步 |
| Q 表 / 经验条数 | 127 个状态 | 100 条经验 | — |
| API 调用 / tokens | — | 304 次 / 703,845 | — |

**Q-Learning 训练分段**：

| 区间（局） | 平均奖励 | 单局最高 | 通关局数 |
|---|---|---|---|
| 1-500 | 1.67 | 239.5 | 1 |
| 501-1000 | 7.86 | 37.5 | 0 |
| 1001-1500 | 12.91 | 49.5 | 0 |
| 1501-2000 | 16.87 | 61.5 | 0 |
| 2001-2500 | 18.20 | 73.5 | 0 |
| 2501-3000 | 17.05 | 71.5 | 0 |
| 3001-3500 | 17.95 | 76.5 | 0 |
| 3501-4000 | 19.18 | 77.5 | 0 |
| 4001-4500 | 17.64 | 90.5 | 0 |
| 4501-5000 | 22.68 | 87.5 | 0 |

唯一的通关出现在第 299 局（ε ≈ 0.86，高随机探索期的幸运撞通），后续 4701 局再未通关。5000 局后 ε ≈ 0.082，仍处于高探索期，说明确实"欠训练"（README 预期 7000-8000 局收敛、10000 局稳定通关）。

**GLM-5 训练→评估落差**：

| 阶段 | 胜率 | 平均奖励 | 平均步数 |
|---|---|---|---|
| 训练 20 局 | 100% | 239.35 | 15.2 |
| 评估 10 局 | 30% | 86.1 | 39.0 |

评估阶段前 3 局（241.5 / 240.5 / 241.5）与训练期一致，第 4 局起系统性崩坏，后 7 局得分完全相同（14.5）且都跑满 50 步——同一失败模式被重复触发（卡在某个无法推进的状态，反复执行无效动作，每步 -0.5，最终定格 14.5）。

**统计可信度（Wilson 95% CI）**：

| 统计量 | 观测值 | 95% CI | 解读 |
|---|---|---|---|
| GLM-5 训练胜率 | 20/20 | [83.9%, 100%] | 结论可靠 |
| GLM-5 评估胜率 | 3/10 | [10.8%, 60.3%] | 区间宽 50 pp，点估计 30% 不确定 |
| Q-Learning 训练胜率 | 1/5000 | [0.0035%, 0.113%] | 上限 0.11%，"几乎不能通关"可靠 |
| Q-Learning 评估胜率 | 0/100 | [0%, 3.7%] | 上限 3.7%，"完全失败"可靠 |

### 3.3 结论

1. **LLM 的 250 倍样本效率验证了"语言先验 + 推理"范式**。第 1 局即 243.0 分通关，零试错，说明 GLM-5 靠人类常识（"钥匙对应颜色""武器打怪"）直接执行正确路径。

2. **RL 的 2910 倍训练速度是它的竞争优势**。Q-Learning 2.39 秒跑完 5000 局，GLM-5 花了 1 小时 56 分钟。RL 在奖励稠密、状态空间可控的任务上仍是更优选择。

3. **"LLM 全面碾压 RL"是过度表述**。两者各有胜负：RL 快、成本低；LLM 省样本、泛化（按真实通关判定）更优。但真正的工程结论是——**训练阶段的 100% 通关率完全不能代表真实能力**，必须看评估阶段。

4. **上下文学习的"过拟合"表现为训练→评估掉 70 个百分点**。评估经验被冻结后，遇到稍有不同的布局（每局随机重置），Agent 只能模仿"最近 50 条成功经验"里的固定路径，缺少"如果前置条件缺失该如何恢复"的纠错知识。纯上下文学习的固有盲区是：**只能模仿成功轨迹，不能当场修正**。

5. **Kimi K2.5 的训练数据不可用**。旧版代码的 `max_tokens=500` 导致 reasoning 模型输出被截断，触发 fallback 连锁卡死评估阶段，额度也耗尽。该模型的结果没有独立落盘，无法与 GLM-5 严格对比。

### 3.4 局限与问题

- **评估样本量不对称**：RL 评估 100 局 vs LLM 评估 10 局，LLM 胜率置信区间宽达 50 pp。要收窄到 ±10 pp 需约 60-80 局评估。
- **单一随机种子序列，无重复实验**：RL 的"第 299 局唯一通关"高度依赖种子，不能区分"模型能力"与"种子运气"。
- **图表与训练日志用 `reward > 50` 当作胜利判定**，与 `game.victory`（拿到宝箱）不一致，会高估胜率约 10 pp。
- **Kimi K2.5 结果无独立落盘**，被 GLM-5 报告误引用（第 14-20 局数值来自 Kimi，跨模型串写）。
- **成本统计只计训练阶段**：评估 10 局另约 150-200 次 API 调用未记录。
- 所有运行均在确定性环境（未加 `--stochastic`），分布内泛化检验的力度有限。

---

## 四、search-codegen：百炼平台完整对齐 GPT-5 原生工具设计

### 4.1 设计

验证原项目基于 OpenRouter + GPT-5 的"原生工具"设计（`web_search` / `code_interpreter` 由模型平台侧调度，Python 端只声明工具并消费结果）能否在阿里百炼平台上对齐。改用百炼 Responses API + `qwen3.7-plus`，逐项验证工具类型、调用计数、结果格式、多轮上下文。

运行环境：Docker 容器（`python:3.12-slim`），宿主机 Anaconda Python 为 x86 架构且未装 Rosetta 2 无法执行；使用 `~/.zshrc` 中已配置的 token-plan 专属网关（公网 `dashscope.aliyuncs.com` 免费额度耗尽）。

测试用例 8 组：基础搜索、搜索 + 分析、复杂综合研究、推理力度三档、便捷方法、三步链式调用、代码解释器、交互式 CLI。

### 4.2 实测数据

**能力对齐汇总**：

| 原项目能力 | 实测证据 | 结论 |
|---|---|---|
| 原生联网搜索 | 响应 `output[].type = web_search_call`、`output[].status = completed`、`usage.x_tools.web_search.count ≥ 1` | 对齐 |
| 原生代码执行 | `output[].type = code_interpreter_call`、执行 Python 代码、返回 OSS 图片链接 | 对齐 |
| 平台侧调度 | Python 端拿不到中间调用细节，只消费最终结果 | 对齐 |
| 推理力度控制 | `reasoning.effort` 参数被接受（低/中/高三档） | 对齐（对比设计有缺陷） |
| 多轮对话记忆 | `input_message_count` 2→4→6，第 2 步正确引用第 1 步"Agentic AI" | 对齐 |
| 多工具协同 | 单请求内同时触发 `web_search` + `code_interpreter` | 对齐 |

**逐用例执行记录**：

| 用例 | 耗时 | 输入 token | 输出 token | 总计 | 工具调用 |
|---|---|---|---|---|---|
| basic | 45 s | 4,362 | 2,076 | 6,438 | web_search × 1 |
| analysis | 61 s | 5,531 | 2,444 | 7,975 | web_search × 1 |
| complex | 99 s | 14,072 | 3,971 | 18,043 | web_search × 2 |
| reasoning-low | — | 638 | 2,268 | 2,906 | 无 |
| reasoning-medium | — | 1,831 | 1,835 | 3,666 | 无 |
| reasoning-high | — | 3,053 | 2,333 | 5,386 | 无 |
| search_analyze | 71 s | 8,948 | 2,570 | 11,518 | web_search × 1 + code_interpreter × 1 |
| chain 第 1 步 | — | 9,889 | 2,947 | 12,836 | web_search × 2 |
| chain 第 2 步 | — | 1,365 | 2,292 | 3,657 | 无 |
| chain 第 3 步 | — | 2,303 | 1,936 | 4,239 | 无 |
| code | 57 s | 3,182 | 2,568 | 5,750 | code_interpreter × 1 |
| CLI /search | 52 s | 10,426 | 2,076 | 12,502 | web_search × 2 |

**资源总消耗**：13 次 API 调用，约 101,241 tokens，约 696 秒（11.6 分钟），工具调用 13 次（web_search 11 次 + code_interpreter 2 次），触发率约 69%。

**推理力度对比缺陷**：low → medium → high 三档共用同一 Agent 实例，输入 token 呈 638 → 1,831 → 3,053 递增来自对话历史累积，不是推理力度差异的真实效应。该对比设计无效。

### 4.3 结论

1. **百炼 Responses API + qwen3.7-plus 完整保留了 GPT-5 原生工具的核心设计**。工具能力完全由平台侧调度，Python 端只声明 `tools` 参数并消费 `output[]` 与 `usage.x_tools`，与原项目设计意图一致。

2. **两个原生工具都触发了真实执行并返回了训练数据之外的实时信息**。`web_search` 返回 2026 年 10-11 月的行业动态（大模型 token 调用量连超美国、OpenAI 新模型发布等）和比特币实时价格区间；`code_interpreter` 生成并执行 Python 代码，返回 OSS 图片临时链接。

3. **多工具编排能力在服务端完整闭环**。search_analyze 用例是唯一在单次请求内同时触发两个工具的场景，模型先用 `web_search` 获取标普 500 实时走势，再用 `code_interpreter` 执行用户提供的收益率/波动率计算代码，最后整合。

4. **推理力度对比实验设计无效**。三档力度共用同一 Agent 实例导致输入 token 单调递增来自历史累积，无法隔离 `reasoning.effort` 的真实影响；要修正需每档新建 Agent 实例或调用前 `clear_history()`。

5. **环境适配中暴露的两个基础设施问题**：宿主机 Anaconda Python 为 x86 架构且未装 Rosetta 2（彻底不可用），必须改用 Docker 容器；公网 `dashscope.aliyuncs.com` 端点免费额度耗尽（所有模型 403），必须切换到 token-plan 专属网关。这两个都不是代码缺陷，但会让"用给定 Key 直接运行 README"的预期落空。

### 4.4 局限与问题

- **单轮样本，无重复**。8 组用例都是单次运行，没有耗时与 token 的均值与方差。
- **长对话缺少历史裁剪**。chain 用例输入 token 从 9,889 降到 1,365 再升到 2,303（搜索注入差异），但总体趋势是历史只增不减；长对话下成本会持续上升。
- **`max_tokens` 未注入**：`DEFAULT_MAX_TOKENS` 环境变量未设置，CLI 显示 `Max Tokens: None`，请求体不带该字段走平台默认值。
- **`code_interpreter` 产出的图片是临时链接**（带 security-token），有时效性，不宜长期引用。
- **无重试机制**：`MAX_RETRIES` / `RETRY_DELAY` 在 `config.py` 定义但未使用；网络抖动或限流会直接失败。
- **token 统计只计 API 调用**：工具侧（搜索请求、代码执行）的资源消耗不计入，不是完整成本。
- 没有结果落盘，数据全部来自终端/日志。

---

## 五、web-search-agent：5 次失败暴露平台 bug 与 SDK 缺陷，换模型绕过

### 5.1 设计

验证 Moonshot 官方 API 的内置 `$web_search` 工具能否支撑"理解问题 → 调用搜索 → 多轮迭代 → 生成结构化答案"的完整链路。初始模型 `kimi-k3`，目标是跑通 `python main.py "问题"` 的单次问答模式。

运行环境：macOS，Python 3.10，openai SDK 2.41.1，Moonshot API Key 手动写入 `.env`。

### 5.2 实测数据（7 次运行）

| 运行 | 模型 | 动作 | 结果 | 根因 |
|---|---|---|---|---|
| 1 | kimi-k3 | `python agent.py` | `API key is required` | `agent.py` 独立运行不 import `config.py`，读不到 `.env`；项目从未调用 `load_dotenv()` |
| 2 | kimi-k3 | 同上 | 迭代 1 调用 `$web_search` 成功，迭代 2 立即 `400 tokenization failed` | 平台要求 `$web_search` 必须加 `extra_body={"thinking": {"type": "disabled"}}`；openai SDK 2.x 无法序列化 `builtin_function` 类型的 tool_calls 消息 |
| 3 | kimi-k3 | 加了 extra_body + 手动构造消息 | `invalid temperature: only 0.6 is allowed` | kimi-k3 禁用 thinking 后只接受 temperature=0.6，但 `_reasoning_safe_temperature` 对 kimi-k3 强制返回 1 |
| 4 | kimi-k3 | 温度改 0.6 | 仍 `tokenization failed` | **Moonshot 官方 bug**：kimi-k3 上 `$web_search` 工具结果回传必然 400；官方论坛有报告，唯一解法是换模型或改 Formula API |
| 5 | kimi-k2.6 | 切换模型 + 回滚 kimi-k3 的临时补丁 | `invalid temperature: only 1 is allowed` | kimi-k2.6 同为 reasoning 模型，只接受 temperature=1；`_reasoning_safe_temperature` 检测列表漏了 k2.6 |
| 6 | kimi-k2.6 | 全部修复 | **完整跑通** | 迭代 1 调用 `$web_search` 返回 8375 tokens，迭代 2 生成完整答案 |
| 7 | kimi-k2.6 | `python main.py "2026年8月最新的开源大模型有哪些？"` | **单次问答成功** | 迭代 1 约 7s，迭代 2 约 62s，输出约 1500 字结构化答案 |

**验证结果矩阵**：

| 验证项 | 结果 |
|---|---|
| 依赖安装（requirements.txt 全部满足） | 通过 |
| `.env` 加载（`config.py` + `agent.py` 两处均生效） | 通过 |
| API Key 鉴权 | 通过 |
| `kimi-k2.6` 模型权限 | 通过 |
| 第一轮 `$web_search` 工具调用 | 通过 |
| 第二轮工具结果回传 + 服务端搜索 | 通过 |
| 多轮迭代循环终止并生成最终答案 | 通过 |
| `main.py` 单次问答模式 | 通过 |
| `kimi-k3` + `$web_search` 组合 | **不通过（平台 bug，已规避）** |

**成本参考**：单次问答约 70 秒、2 次 API 调用、约 8K tokens 搜索结果；模型回答质量高（结构化表格 + 榜单 + 选型建议）。

**最终代码修改清单**（7 处最小修改）：

| 文件 | 修改 |
|---|---|
| `config.py` | 补 `load_dotenv()`；`DEFAULT_MODEL` 改为 `kimi-k2.6` |
| `agent.py` | 补 `load_dotenv()`；`self.model` 改为 `kimi-k2.6`；`_reasoning_safe_temperature` 检测列表加 `kimi-k2.6`；tool_calls 回传处改为手动构造 assistant 消息字典（绕开 openai SDK 2.x 序列化 `builtin_function` 丢字段） |

### 5.3 结论

1. **5 次失败里 3 个是项目代码缺陷、2 个是平台 bug**。代码缺陷：`.env` 从未被加载、reasoning 模型温度白名单漏了 k2.6、openai SDK 2.x 无法序列化 `builtin_function` 类型的 tool_calls 消息。平台 bug：kimi-k3 + `$web_search` 第二轮必然 400（Moonshot 官方论坛有对应报告），客户端无法修复。

2. **推理模型 temperature 限制是四个实验反复碰到的共性问题**。本章 web-search-agent 的 kimi-k3（thinking 禁用后只接受 0.6）、kimi-k2.6（只接受 1）、learning-from-experience 的 Kimi K2.5（强制 1）、context 的 deepseek-v3（非推理，无此限制但换推理模型会有）——**每个推理模型都有不同的 temperature 限制，必须实测后硬编码或动态检测**，不能假设通用值。

3. **SDK 序列化缺陷是隐性陷阱**。openai Python SDK 2.x 把 tool_calls 消息当作 Pydantic 对象 append 到历史里时，会丢弃 `builtin_function` 类型的字段。这个 bug 在本地跑不出来（因为本地不触发该路径），只有在"调用外部工具 → 把工具结果回填到历史 → 第二轮请求"时才暴露。解法是手动构造 assistant 消息字典，不走 SDK 的对象序列化。

4. **平台 bug 必须被纳入"模型选型决策"**。kimi-k3 的 `$web_search` 兼容问题是平台层面的（不是项目代码错），唯一解法是换模型。这个决策在实验开始前无法通过阅读 README 发现，必须实测。

5. **"项目代码 vs 平台 bug"的区分对可维护性至关重要**。运行 2-4 的临时改动（thinking 禁用、kimi-k3 温度特判 0.6）在确认是平台 bug 后已全部回滚，不残留在最终代码里。这种"试错→确认→回滚"的过程在报告里被完整记录，避免了把临时补丁当成正式功能。

### 5.4 局限与问题

- **交互模式未验证**：`quickstart.py` 与 `main.py`（无参）的交互模式需要 TTY 终端，报告只做了单次问答验证。
- **README 未同步**：README 仍声称默认模型为 `kimi-k3`，与实际修复后的 `kimi-k2.6` 不一致，且未记录 k3 的平台兼容性问题。
- **`env.example` 过期**：其中模型名 `kimi-k2-0905-preview` 已过期，应改为 `kimi-k2.6`。
- **API Key 安全**：实验过程中 Key 曾在对话中明文出现，应作废重生成。
- 没有重复实验。单次问答只跑 1 次，无法验证稳定性。
- 没有结果落盘，数据全部来自终端日志。

---

## 六、跨实验结论

### 结论 1：Agent 实验里"成功判定"是最容易伪造的环节

| 实验 | 原始判定 | 真实判定 | 假成功数 | 根因 |
|---|---|---|---|---|
| context（15 组） | 86.7%（13/15） | 53.3%（8/15） | **5** | 只检查 `FINAL ANSWER:` 是否存在 |
| learning-from-experience LLM | 训练 100%（20/20） | **评估 30%（3/10）** | 训练期过拟合 | 训练 vs 评估未分开；评估经验冻结后暴露真实能力 |
| search-codegen | "8/8 能力对齐" | 推理力度对比设计无效 | 1（对比组） | 共用实例导致无法隔离变量 |
| 前两章（chapter2/3 汇总） | agentic-rag 100% 成功率 | 复杂题 4/5 回答为空 | **至少 5** | 只检查是否抛异常 |

**统一教训**：任何"成功"都必须至少两层判定——**运行层（工具日志非空、无崩溃）+ 内容层（对照 Ground Truth）**。靠"模型说 FINAL ANSWER"或"没抛异常"来判定成功，是 Agent 实验里最常见、也最昂贵的假信号来源。

### 结论 2：推理模型 temperature 限制是本章四个实验里出现频率最高的基础设施问题

| 实验 | 模型 | temperature 限制 | 处理方式 |
|---|---|---|---|
| web-search-agent | kimi-k3 | thinking 禁用后只接受 0.6 | 换模型规避 |
| web-search-agent | kimi-k2.6 | 只接受 1 | 加白名单 |
| learning-from-experience | Kimi K2.5 | 只接受 1 | 强制 1 |
| context | deepseek-v3 | 非推理，无限制 | — |
| search-codegen | qwen3.7-plus | 未明确 | — |

**统一教训**：推理模型的 temperature 限制不是可选项，是每个模型独有的约束条件。**必须在实验开始前先跑一次单请求实测 temperature 范围**，把结果固化到配置里。不能假设"所有推理模型都接受 temperature=1"（kimi-k3 在禁用 thinking 后只接受 0.6 就是反例）。

### 结论 3：消融模式必须先验证"模式真的生效了"

context 实验里，`no_history` 和 `no_reasoning` 在代码里都没真正实现（前者跳过了组装逻辑、后者模型本身就没有 `reasoning_content`）。把"没有生效的消融"的数据当结论发表，会传播错误认知。**做消融实验之前必须先跑单例验证消融是否真的改变了 Agent 的行为**——验证指标至少是：工具调用数、迭代次数、产出结构。

### 结论 4：LLM "250 倍样本效率"是模型先验的结果，不是"上下文学习范式天生优秀"

GLM-5 第 1 局即通关靠的是"钥匙开门""武器打怪"这类人类常识，不是上下文里的经验累积。它的优势来自**预训练语言知识**给了强先验，RL 则从完全随机初始化开始探索。**把 RL 换成"零先验 LLM"（从未接触过"钥匙开门"语义的模型），结果可能反转**。

### 结论 5：训练→评估落差是纯上下文学习的固有盲区

GLM-5 训练 100% → 评估 30%（掉 70 pp）的直接根因是**评估期经验被冻结**：Agent 只能模仿"最近 50 条成功经验"里的固定路径，遇到新布局时没有"从失败中补充经验"的机制。这和 chapter3 里 layer3 的失败（检索返回但不会用）是同一种盲区。

### 结论 6：工具调用是硬约束（没工具做不成），工具结果是软约束（没结果能编造）

context 实验的 `no_tool_calls` 和 `no_tool_results` 给出了精确画像：
- `no_tool_calls`：无数据可查，直接编造一份"结构完整、数字全错"的报表（偏差 300~800 倍），秒交卷。
- `no_tool_results`：工具日志全绿（看起来"正在工作"），但产出物要么是一句推诿、要么是编造的低量级数字。

后者对生产环境监控的威胁更大——监控只看"有没有调工具"，不看"工具调了之后产出了什么"。

### 结论 7：平台 bug vs 代码缺陷必须区分，临时补丁不能残留

web-search-agent 的 7 次运行里，kimi-k3 + `$web_search` 的兼容性问题最终被确认是平台 bug（官方论坛有报告），不是项目代码错。运行 2-4 的临时补丁（thinking 禁用、kimi-k3 温度特判 0.6）在确认后已全部回滚，不残留在最终代码里。这种"试错→确认→回滚"的过程值得在每个实验里保留，避免把临时补丁当成正式功能。

---

## 七、方法学与复现性问题处置清单

| 问题 | 涉及实验 | 处置 |
|---|---|---|
| 原始判定用 FINAL ANSWER 字符串匹配 | context | 必须加内容校验层；PDF V2 的 6 维校验器可作为模板 |
| JSON 缺 trajectory 序列化 | context V1/PDF V1 | 所有结果文件必须落盘完整工具轨迹 + 最终答案全文 |
| 消融模式未生效（no_history 跳过组装、no_reasoning 空操作） | context | 消融前先跑单例验证行为变化 |
| GT 版本不统一（三个版本） | context | 用代码实际汇率表做单一 GT 来源 |
| C5（编造区域）校验器失效 | context | 从正向检查改为反向：检查答案里出现的区域名是否全部属于期望集合 |
| 训练/评估共用模型但经验处理不同步 | learning-from-experience | 明确区分"训练期经验累积"与"评估期经验冻结"两套流程 |
| 评估样本量不对称（RL 100 vs LLM 10） | learning-from-experience | 对 LLM 提高评估局数（至少 30 局）或统计置信区间并在结论里说明 |
| 单随机种子无重复 | learning-from-experience | 固定种子序列后重复 3-5 次 |
| 胜利判定用 reward > 50 而非 game.victory | learning-from-experience | 统一为布尔 `victory` 信号 |
| 推理力度对比共用实例（历史累积污染） | search-codegen | 每档新建 Agent 实例或调用前 clear_history() |
| max_tokens 未注入 | search-codegen | 环境变量 DEFAULT_MAX_TOKENS 必须显式设置 |
| Kimi K2.5 结果无独立落盘 | learning-from-experience | 每次运行强制写入独立结果目录 |
| 宿主 Anaconda 架构不兼容 | search-codegen + 其他 | 固化 Docker 运行方式并写进 README |
| 免费额度耗尽后切换网关 | search-codegen | 测试前核对 provider 可用网关与密钥状态 |
| `.env` 未被 load_dotenv() 加载 | web-search-agent | 所有入口（`config.py` + `agent.py` 两处）必须显式调用 |
| 推理模型 temperature 白名单漏新模型 | web-search-agent + 其他 | 维护模型→temperature 映射表，新增模型先实测 |
| openai SDK 2.x 无法序列化 builtin_function | web-search-agent | 手动构造 assistant 消息字典，不走 SDK 对象序列化 |
| README / env.example 与实际配置不同步 | web-search-agent | 修复后立即更新文档，或在 CI 中加一致性检查 |

---

## 八、面向工程的实践结论

1. **验收标准必须是"内容正确"，不是"协议正确"**。原始 Agent 实验里，模型只要输出 `FINAL ANSWER:` 就算通过——这是最低成本的假成功来源。必须在协议层（工具调用非空、迭代未耗尽）之上加一层内容校验。

2. **上下文消融实验做之前先验证消融是否生效**。代码里的一行 `if something in msg_dict`（实际上 something 永远不存在）可以让整个消融组白跑。

3. **LLM + RL 混合是"冷启动 → 长期部署"的标准范式**。LLM 用 20 局探索出规则与最优路径（零样本先验 + 少量经验），产出可解释轨迹；再把轨迹蒸馏进 RL 策略，用大量廉价 episode 精调。两者各有优势，不存在"谁碾压谁"。

4. **长对话必须有历史裁剪或压缩**。search-codegen 的 chain 用例和 chapter3 的多层记忆实验都观察到输入 token 随历史单调递增，成本不可控。

5. **推理模型必须给足 `max_tokens` + 容错解析**。Kimi K2.5 的 500 tokens 截断导致整个评估阶段卡死的教训，与 chapter3 的 context-compression 实验里 `SUMMARY_MAX_TOKENS=500` 导致空摘要、chapter2 的 reasoning model `max_tokens` 问题是同一条规律。

6. **Docker 固化运行方式**比依赖宿主机 Python 更可靠。本章 search-codegen 和 chapter3 的 multimodal-agent 都发现了宿主 Anaconda 架构不兼容问题（x86 vs ARM），Docker 容器是最低成本的解法。

7. **网关可用性与模型约束先于代码编写**。百炼平台免费额度耗尽、kimi-k3 与 `$web_search` 的平台级兼容性 bug、kimi-k2.6 的 temperature 限制——这些都是实验前必须先实测的约束条件，读 README 或 API 文档发现不了。

8. **临时补丁必须在确认后回滚**。web-search-agent 的 kimi-k3 临时兼容补丁已全部回滚，最终代码里不留痕迹。如果当初没回滚，这份"废弃模型的临时补丁"就会作为正式逻辑留在仓库里，后续维护者会被误导。

9. **SDK 序列化陷阱需要专项测试**。openai SDK 2.x 的 `builtin_function` 丢字段、tool_calls 消息 append 方式、reasoning_content 提取——这些是 SDK 内部实现细节，不会在 SDK 自带单测里覆盖，必须在"调工具→回填→再调"的端到端链路里专门验证。

---

## 九、待补测项

| 优先级 | 事项 | 目标 |
|---|---|---|
| P0 | context：用生效的消融 + 完整 trajectory 重跑 5 种模式 | 让 no_history 和 no_reasoning 真正改变 Agent 行为；得到消融效应的真实数据 |
| P0 | learning-from-experience：LLM 评估局数扩到 30 局以上 | 把 Wilson 置信区间从 50 pp 收窄到 ±20 pp 内 |
| P0 | learning-from-experience：同一代码版本下重跑 Kimi K2.5 完整训练 + 评估 | 得到推理模型 vs 非推理模型的严格对照 |
| P0 | web-search-agent：交互模式验证 | 覆盖 `quickstart.py` 与 `main.py` 无参入口 |
| P1 | learning-from-experience：固定种子序列后重复 3 次 | 区分"模型能力"与"种子运气" |
| P1 | search-codegen：推理力度对比隔离变量后重跑 | 得到 reasoning.effort 的真实效应 |
| P1 | context：GT 重建脚本自动化 | 消除 GT 版本演进对校验精度的干扰 |
| P1 | learning-from-experience：奖励阈值胜利判定代码改为 game.victory | 统一图表、日志、评估的胜利口径 |
| P1 | web-search-agent：README / env.example 同步更新 | 消除文档与实际配置的不一致 |
| P2 | 全章节统一：所有结果 JSON 强制落盘完整轨迹 + 最终答案全文 + validation 字段 | 消除前两章出现的"结果文件不完整导致无法复核"的问题 |
| P2 | context：换 reasoning 模型（如 kimi-k2.6）重跑消融 | 验证 no_reasoning 消融的真实效应（deepseek-v3 是非 reasoning 模型，当前是名义消融） |
| P2 | search-codegen：长对话历史裁剪验证 | 测试不同压缩策略对能力的影响 |
| P2 | web-search-agent：单次问答重复 3 次 | 验证稳定性，得到耗时方差 |

---

## 十、证据索引

| 实验 | 实测文档 | 结果文件 |
|---|---|---|
| context | `ablation_study_report.md`（纯文本 V1，无校验）、`ablation_pdf_study_report.md`（PDF V1，无校验）、`ablation_pdf_v2_report.md`（PDF V2，含校验）、`results/deepseek-v3_上下文消融实验评测报告.md`（三套统一修正） | `ablation_results.json`（5 组，缺轨迹）、`ablation_pdf_results.json`（5 组，缺轨迹）、`ablation_pdf_v2_results.json`（5 组，含完整 trajectory + final_answer + validation） |
| learning-from-experience | `results/完整实验评测报告.md`（权威）、`results/GLM-5_实验结果报告.md`（过程记录，第 14-20 局数值与 JSON 不一致）、`results/Kimi-K2.5_实验结果报告.md`（仅终端片段，无独立落盘） | `results/20260814_005831/experiment_results.json`（RL 5000 局 + LLM 20+10 局逐局记录，权威来源） |
| search-codegen | `search-codegen/实验测试分析报告.md`（唯一报告） | 无独立结果文件，数据全部来自终端/日志 |
| web-search-agent | `web-search-agent/实验评测报告.md`（唯一报告，含 7 次运行完整日志 + 代码修改清单） | 无独立结果文件，数据全部来自终端日志 |
| 基础设施（辅助） | `multimodal-agent/RUN_ANALYSIS_REPORT.md`（同一容器+网关环境下的能力矩阵，辅助证明网关可用性） | — |

**数据取舍原则**：本报告以"结果文件 + 运行时间 + 原始输出"为准。文档与结果文件冲突时按以下顺序取值：

1. 带完整 trajectory 与 validation 字段的结果 JSON（PDF V2 的 `ablation_pdf_v2_results.json`、learning-from-experience 的 `experiment_results.json`）；
2. 有终端输出片段且数值可在 JSON 中定位一致的报告；
3. 只有结论表述的汇总报告。

据此，`GLM-5_实验结果报告.md` 第 14-20 局数值不采用（与 JSON 不一致，且判断为跨模型数据串写）；`Kimi-K2.5_实验结果报告.md` 只有训练阶段数字且无独立落盘，仅能作为"旧代码在推理模型上暴露的问题"的定性引用；`context` 实验里纯文本 V1 与 PDF V1 的"真实成功率"来自日志离线回放，存在精度损失，本报告只引用其辅助意义，核心结论以 PDF V2 为准。web-search-agent 与 search-codegen 没有独立结果文件，全部依赖终端日志与代码修改清单，证据强度降一级（从"高"降到"中高"）。
