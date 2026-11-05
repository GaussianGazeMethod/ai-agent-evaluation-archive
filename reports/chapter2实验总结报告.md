# chapter2 实验总结报告

**报告对象**：`chapter2`（第 2 章 上下文工程）下有实测数据支撑的 4 个子实验
**生成时间**：2026-11-05
**数据来源**：各子项目已产出的测试分析报告、实验对比报告与结果文件（见文末证据索引），本报告不引入未运行过的新数据

> 说明：`attention_visualization`、`local_llm_serving`、`log-sanitization` 三个子项目仅有设计与说明文档，没有独立的测试/结果产物，按约定不纳入本报告。

---

## 一、总览

| 实验 | 验证命题 | 模型 / 规模 | 样本量 | 实测结论 | 证据强度 |
|---|---|---|---|---|---|
| `kv-cache` | 上下文稳定性决定 KV 缓存利用率与耗时 | Kimi K3，6 种实现模式 | 6 组 × 单任务 | 稳定上下文缓存 40.3 万 tokens，反模式降至 0.5~1 万；总耗时最多 +97.5% | 中（数据完整在报告内，结果文件落盘失败） |
| `context-compression` | 压缩策略决定长任务能否跑完 | Kimi K3，128K 窗口，6 策略 × 20 轮 | 6 组 × 1 任务 | 不压缩第 5 轮即溢出；4/6 策略完成 11/11 查全；寿命延长 3~4 倍 | 中高（6 策略完整对比，但有早期不一致运行记录） |
| `prompt-engineering` | 提示质量下降会显著拉低任务成功率 | GPT-5（OpenRouter），tau-bench airline | 单任务 n=1，无基线 | **实测不支持**“30~80% 性能下降”的预期；已有运行无法形成对照 | 低（样本过小 + 一组结果为运行框架崩溃） |
| `system-hint` | 系统提示（TODO/计数/错误详情等）提升可靠性 | DeepSeek V4 Flash，5 类用例 | 5 用例 + 1 组对照 | 复杂任务显著收益；线性任务出现反向劣化（30 轮空转 vs 7 轮完成） | 高（有明确对照组与完整轨迹） |

一句话总结：**4 个实验里，2 个（kv-cache、context-compression）给出了稳健的量化结论，2 个（system-hint、prompt-engineering）给出了与预期相反或不足以支撑结论的结果。后者不是失败，反而更有价值：它们说明“提示/提示词层面的优化是任务相关的，且实验基础设施本身极易产出假信号”。**

---

## 二、kv-cache：上下文稳定性 = 缓存收益

### 2.1 设计

ReAct Agent（Kimi K3，标准 OpenAI 工具调用，本地文件系统工具）执行同一任务（分析 week1/week2 全部项目），只改动上下文构造方式，共 6 种模式：

| 模式 | 实现差异 | 预期 |
|---|---|---|
| `correct` | 首次构建 messages 后全程复用同一列表 | 缓存高效命中 |
| `dynamic_system` | 每轮在 system prompt 追加时间戳 | 前缀变化，缓存全失效 |
| `shuffled_tools` | 每轮随机打乱工具顺序 | 工具定义变化 |
| `dynamic_profile` | 每轮插入变化的用户积分 | 动态噪声污染前缀 |
| `sliding_window` | 只保留最近 6 条消息 | 截断破坏前缀连续性 |
| `text_format` | 历史转纯文本重新拼接 | 破坏结构化消息 |

运行时间 2026-08-24 00:53–01:18，`python main.py --compare`。

### 2.2 实测数据

| 模式 | 缓存 Token | 总耗时(s) | 相对 correct | 迭代 |
|---|---|---|---|---|
| correct | **403,456** | 210.4 | 基线 | 17 |
| text_format | 171,776 | 244.1 | +16.0% | — |
| shuffled_tools | 155,136 | 241.8 | +14.9% | — |
| dynamic_profile | 9,728 | 415.7 | **+97.5%** | — |
| dynamic_system | 5,120 | 340.9 | **+62.0%** | — |
| sliding_window | 1,536 | 21.4 | -89.8%（假象） | 仅 3 轮 |

### 2.3 结论

1. **缓存 Token 总量是唯一有效判别指标**：`correct` 是 `dynamic_system` 的 78 倍、`dynamic_profile` 的 41 倍。稳定上下文一次性缓存 40 万 tokens，动态元数据几乎全部摧毁缓存。
2. **代价体现在 wall time 上而非首字延迟**：`dynamic_profile` +97.5%、`dynamic_system` +62.0%，与缓存丢失量基本同序。
3. **`sliding_window` 的“最快”是假的**：仅 3 轮就因信息残缺提前收尾，任务未完成。激进截断换取的是速度假象、输掉任务质量。
4. **“命中率 100%”是统计口径伪信号**：代码按轮次二值计数（`cached_tokens > 0` 即算命中），Kimi 每轮都返回部分缓存，导致 6 种模式全部 100%，无法区分好坏。

### 2.4 局限与问题

- **TTFT 指标无效**：用非流式整次请求耗时近似 TTFT，且上下文逐轮增长，导致 `correct` 的“TTFT”反而 7.41s → 13.65s 单调上升。真实缓存收益无法从这组数据读出，需改流式首 token 计时或做“等长上下文有无缓存”对比。
- **结果文件没有落盘**：`compare_implementations` 把 `ToolCall` dataclass 直接塞进 `results`，`json.dump` 抛 `TypeError`，`comparison_20260824_011832.json` 仅 86 字节即被截断。数据只能从终端摘要与分析报告取得，无法二次复核。
- README/汇总文档中“缓存命中率 >90%”“TTFT 0.82s → 0.19s”等表述与本次实测不符，应以本报告数据为准。

---

## 三、context-compression：压缩策略决定 Agent 寿命

### 3.1 设计

任务为“查清 11 位 OpenAI 联合创始人当前任职”，需要多次真实搜索（Serper）并累积大量网页内容。窗口 128,000 tokens，最多 20 轮，Kimi K3。6 种策略：

1. `no_compression`：不压缩（基线）
2. `non_context_aware_individual`：逐页独立摘要后拼接
3. `non_context_aware_combined`：合并全部内容后单一摘要
4. `context_aware_summary`：查询聚焦摘要
5. `context_aware_with_citations`：查询聚焦 + 来源引用
6. `windowed_context`：80% 阈值前保留原文，触发后压缩历史并标记 `[COMPRESSED]`

### 3.2 实测数据

| 策略 | 结果 | 工具调用 | 溢出次数 | 耗时(s) | 总 Token | 压缩率 | 查全 |
|---|---|---|---|---|---|---|---|
| 1 no_compression | 失败（第 5 轮） | 11 | 1 | ~300 | 132,989 | 109.0% | ~5/11 |
| 2 individual | 失败（第 15 轮，429 限流） | 27 | 4 | ~1800 | 180,742 | 11.3% | ~9/11 |
| 3 combined | 成功（~14 轮） | 29 | 4 | 3087 | 213,261 | 22.5% | 11/11 |
| 4 context_aware | 成功（~17 轮） | 26 | **0** | 5564 | 116,114 | **9.0%** | 11/11 |
| 5 citations | 成功（**~11 轮**） | 20 | **0** | 1830 | **111,634** | 17.6% | 11/11 |
| 6 windowed | 成功（~10 轮） | **16** | 2 | **1171** | 165,865 | 107.9% | 11/11 |

### 3.3 结论

1. **压缩是长任务的硬性前提**：不压缩在第 5 轮就把 132K 撑爆 128K 窗口；启用压缩后 4 条策略全部查全 11 人，Agent 可执行寿命延长 3~4 倍。
2. **查询聚焦 > 无上下文摘要**：策略 4/5 零溢出且 token 最低（11.2 万 ~ 11.6 万），而策略 3（合并摘要）虽然成功，但 4 次溢出、累计 21.3 万 tokens、耗时 3087s。
3. **引用版是综合最优**：策略 5 以最少的工具调用（20 次）与最快的收敛（~11 轮）达成同等结果，且保留可追溯性。
4. **没有全局最优，只有维度最优**：压缩率最优是策略 4（9.0%），wall time 最优是策略 6（1171s），token 最优是策略 5。

### 3.4 局限与问题

本实验最有价值的部分其实是暴露的 4 个 instrumentation 故障：

1. **token 记账 bug（`+=` 误用）**：`prompt_tokens` 本身就是“本次请求的完整历史长度”，用 `+=` 累加导致第 2 轮出现虚假 257K 告警，所有策略的溢出统计一度虚高，掩盖真实效果。修复为赋值 + 增量累加。
2. **推理模型 `max_tokens` 不足**：`SUMMARY_MAX_TOKENS=500` 时，reasoning 吃掉 497 tokens，正文只剩 3 tokens，压缩结果为空（`102,279 → 0 chars`）。调至 2000 后恢复。
3. **压缩率显示口径不一致**：`original_length` 只累计 `content` 字段，`compressed_length` 含格式化包装，导致策略 1/6 出现 >100% 的压缩率（`Space Saved` 为负），属显示问题。
4. **证据版本不一致**：`results/experiment_20260821_121346.json` 记录的是另一次更早的小规模运行（`no_compression` 10 轮成功、0 溢出、18 次工具调用），与实验报告中的完整对比数值不同。同一实验存在两套不一致数据，说明配置未被固化（搜索结果体量、轮数上限都会改变结论）。

---

## 四、prompt-engineering：链路可用，结论不成立

### 4.1 设计

基于 tau-bench（airline 域，GPT-5 经 OpenRouter），设计三个消融维度：语气风格（default / trump / casual）、wiki 规则随机化（打乱顺序、去除章节结构、破坏逻辑层级）、工具描述移除（函数与参数描述置空），以及三者叠加的最坏组合。

### 4.2 实测数据（`results_ablation/` 全部 4 个文件）

| 文件 | 消融配置 | 任务数 | reward |
|---|---|---|---|
| `...wiki_random_0917210850.json` | 仅 wiki 随机化 | 1（task 0） | 1.0 |
| `...tone_trump_trump_tone_0917203842.json` | trump 语气 | 1（task 0） | 1.0 |
| `...tone_trump_trump_tone_0917205443.json` | trump 语气（另一次） | 5（task 0–4） | 全部 0.0，但均非模型失败 |
| `...tone_casual_wiki_random_no_tool_desc_0917211809.json` | 最坏组合（casual + wiki 乱序 + 无工具描述） | 1（task 0） | **1.0** |

第三份文件的 5 个 0.0 全部来自运行框架崩溃，而非 Agent 答错：

```
ablation_agent.py, line 170
print(f"\nCost: ${res._hidden_params.get('response_cost', 0):.4f}")
TypeError: unsupported format string passed to NoneType.__format__
```

即 OpenRouter 返回的 `response_cost` 为 `None`，格式化直接抛异常，任务在被记录为 `reward=0.0`。

### 4.3 结论

1. **实测不支持已有文档的结论**。README 与两份汇总报告写的“提示工程不当导致 30~80% 性能下降”在现有数据中找不到对应证据；相反，最坏组合（语气休闲 + 规则打乱 + 无工具描述）在唯一被记录的任务上拿到了 1.0。
2. **现有数据不足以支撑任何消融结论**，三个原因叠加：样本量 n=1（单任务单 trial，且无 baseline 对照结果留存）；消融组与基线的任务与配置未对齐；崩溃被计为 0 分，会系统性压低消融组表现。
3. **链路本身是通的**：GPT-5 经 OpenRouter 可以在 tau-bench airline 上完成一次完整的多轮工具对话并拿到 1.0，说明框架适配（provider、`temperature=1.0`、`reasoning_effort=low`）可用。
4. **可确认的附带结论只有成本侧**：`GPT5_CONFIGURATION.md` 记录的 `reasoning_effort="low"` 使简单任务 token 从 1358 降到 333（-75%），复杂推理从 2000+ 降到 500–800（-60~75%）。这条属于 token 消耗经验值，与任务成功率无关，不能替代消融结论。

### 4.4 局限

- 结果文件不含工具定义，无法从产物反证“工具描述移除”是否真的生效。
- 缺少 baseline 与同一 task 的多次 trial，`reward` 的方差完全未知。
- 崩溃→0 分的计分方式使历史结论不可信，需先修 `response_cost` 为空的问题再重跑。

---

## 五、system-hint：提示增强是任务相关的双刃剑

### 5.1 设计

在 ReAct Agent 上注入“系统提示”（时间戳、`Tool call #N` 计数器、四态 TODO 列表、详细错误与修复建议、系统状态感知），提示作为调用前的临时用户消息注入、不入历史。模型 DeepSeek V4 Flash（推理模型，`temperature` 强制 1），2026-08-24 12:38–13:05。

### 5.2 实测数据

| 用例 | 条件 | 迭代 | 工具调用 | 结果 |
|---|---|---|---|---|
| 适配验证 | 写并运行 hello 脚本 | 5/20 | 6 | 成功 |
| 简单任务对比 | 有系统提示 | 3/10 | 2 | 成功 |
| 简单任务对比 | 无系统提示 | 3/10 | 2 | 成功 |
| 复杂分析（环境不匹配） | 有系统提示 | 22/30 | 大量 | 成功，产出 268 行分析报告 |
| 交互分析任务 | 有系统提示 | 7/25 | 11 | 成功 |
| **错误恢复对照** | **有系统提示** | **30/30** | 4 | **失败（空转耗尽）** |
| **错误恢复对照** | **无系统提示** | **7/30** | 5 | **成功，答案清晰** |

错误恢复对照组使用同一份含 3 处错误（缺冒号、递归名拼写、主调用拼写）的脚本、同一段任务文本，唯一差别是 `--no-timestamps --no-counter --no-todo --no-errors --no-state`。

### 5.3 结论

1. **简单任务零增益**：写一个 hello 脚本，有/无提示都是 3 轮 2 次调用，完全一致。
2. **复杂任务显著正收益**：面对“week1/week2 目录不存在”的环境不匹配，有提示的 Agent 没有死循环也没有放弃，约 8 轮后自主改向分析实际存在的 chapter1/chapter2，产出 268 行结构化报告。工具计数（发现重复搜索无效）+ TODO 重规划在此起作用。
3. **线性任务出现反向劣化**：错误恢复组中，有提示版本第 3 轮就修好了 bug（`fibonacci(10) = 55`），但随后 25 轮不再调用任何工具、只反复“思考”，最终耗尽 30 轮没有输出最终答案；无提示版本第 4 轮修复、第 7 轮收尾，答案完整列出 3 处修复。机制解释：TODO 列表中残留的 `in_progress` 项制造了“还有事没做完”的虚假压力，推理模型本身倾向多轮思考，两者叠加导致空转；而工具计数器只统计调用次数，检测不到“连续无工具调用”的空转。
4. **Agent 自查发现配置架构问题**：交互任务产出的 `analysis.txt` 指出 `config.py` 的 `AgentConfig` 与 `agent.py` 的 `SystemHintConfig` 平行重复、`agent.py` 并未 import `config.py`、`max_iterations` 与 `timeout` 配置实际不生效。该结论与人工审查一致，可视为提示质量对分析深度有正向作用的旁证。

### 5.4 局限

- 5 类用例各只跑 1 次，无重复试验；简单任务与复杂任务的差异明确，但中等复杂度的边界未测。
- sample 任务文本仍指向不存在的 `week1/week2` 目录，第二次复测时 Agent 全盘 find 8 轮被手动停止，说明任务描述与目录结构不匹配会显著消耗预算。
- 各入口 `max_iterations` 写死（30/25/20），环境变量不生效，导致难任务无法通过配置放宽上限重测。

---

## 六、跨实验结论

### 结论 1：上下文“稳定性”是性能前提，“管理”是生存前提

kv-cache 证明同任务下仅因前缀不稳定，缓存从 40.3 万 tokens 掉到 5 千，耗时 +62%~97%；context-compression 证明完全不管理上下文，第 5 轮就撞墙。两者是不同层面的同一件事：**前缀稳定决定快不快，主动压缩决定活不活**。

### 结论 2：所有优化手段都存在反向代价，没有免费收益

| 手段 | 得到 | 付出 |
|---|---|---|
| 稳定上下文 | 缓存 40 万 tokens | 不能带时间戳、动态资料、重排工具 |
| 激进截断 | 总耗时 -89.8% | 任务未完成（3 轮草率收尾） |
| 查询聚焦压缩 | 零溢出、低 token | 策略 4 耗时 5564s（摘要本身要反复调 LLM） |
| 系统提示 | 复杂任务自纠偏、产出 268 行报告 | 线性任务空转 25 轮、不交付 |

这条是本次 4 个实验最有工程价值的横向发现：**优化项必须绑定“任务形态”评估，脱离任务形态的单一指标（耗时、token、缓存量）都会给出错误建议。**

### 结论 3：提示层面的收益是任务相关的，不能当作普适规律

system-hint 给出了正反两个方向的实测证据，prompt-engineering 则连“负面证据”都没能产出。与已有汇总文档中“提示工程 = 员工培训、做不好会掉 30~80%”的表述相比，实测给出的更准确的说法是：**结构化提示在需要规划与纠偏的多步任务上有效，在目标明确的线性任务上可能因过度规划而有害；而提示质量对成功率的影响强度目前尚未被本项目的实验量化。**

### 结论 4：实验基础设施的可靠性低于被测量的对象

4 个实验中有 3 个出现“指标/记账错误产生的假信号”，且都足以推翻原始结论：

| 实验 | 假信号 | 后果 |
|---|---|---|
| kv-cache | 轮次命中率 100%、非流式伪 TTFT | 6 种模式无法区分、缓存延迟收益不可读 |
| kv-cache | `ToolCall` 未序列化 | 结果文件 86 字节截断，数据不可复核 |
| context-compression | `prompt_tokens +=`、压缩率口径不一致 | 溢出次数虚高、压缩率 >100% |
| prompt-engineering | `response_cost=None` 崩溃记为 reward 0 | 消融组被系统性判负 |

统一教训：**先验证指标定义与落盘链路，再相信实验结论**。具体到可执行规则：

- 缓存类实验只认“缓存 token 总量”与“流式首 token 延迟”，不认轮次命中率；
- 延迟类指标必须说明是流式首字还是整次耗时，且需控制上下文长度不变；
- 计数类指标（token、溢出、工具调用）区分“本次请求值”与“会话累计值”；
- 失败必须区分“模型答错”“运行框架崩溃”“被限流/超时”三类，否则 reward 均值无意义。

### 结论 5：推理模型是本次实验中的共性约束

kv-cache、context-compression、system-hint 三个实验都踩到同一类问题：推理模型只接受 `temperature=1`（否则请求被拒），且 `reasoning_content` 会先消耗 token 预算，`max_tokens` 给小会导致正文为空。context-compression 里 500 tokens 的摘要上限直接产出空摘要，就是最典型的例子。

---

## 七、方法学与复现性问题的处置清单

| 问题 | 涉及实验 | 处置 |
|---|---|---|
| 轮次命中率统计口径 | kv-cache | 改为 `cached_tokens / prompt_tokens` 的占比 |
| 伪 TTFT | kv-cache | 改流式首 token 计时；或固定上下文长度做有无缓存对照 |
| 结果落盘 TypeError | kv-cache | `tool_calls` 转 dict 后再 dump |
| `prompt_tokens +=` | context-compression | 改为赋值；completion/total 保留累加 |
| 压缩率口径 | context-compression | 原文与压缩后都按同一字段口径统计 |
| `SUMMARY_MAX_TOKENS=500` | context-compression | 推理模型建议 2000+ |
| `response_cost` 为 None | prompt-engineering | 取值加 `or 0`，崩溃不写入 reward |
| 单样本无基线 | prompt-engineering | 多 task × 多 trial + 同 task 基线对照 |
| 配置漂移（重复配置类） | system-hint | 整合为单一 `AgentConfig`，`max_iterations`/`timeout` 从配置读取 |
| 缺空转检测 | system-hint | 增加“连续 N 轮无工具调用”阈值，触发后强制输出最终答案 |

---

## 八、面向工程的实践结论

1. **上下文构造优先保证前缀不变**：固定 system prompt、固定工具顺序、不注入时间戳/动态资料、保持标准消息结构。这比任何模型侧调优都便宜。
2. **长任务必须配压缩策略，优先“查询聚焦 + 保留引用”**：它在 token、溢出与收敛轮次上同时最优，并保留溯源能力。
3. **截断只能作为最后手段**：它的“快”来自提前放弃，必须配答案质量校验，否则会得到漂亮的假结果。
4. **系统提示按任务形态启用**：复杂多步任务开 TODO 与工具计数；目标明确的线性任务（如修一个 bug）关闭或精简，避免过度规划。
5. **不要在没有基线、样本量为 1 的情况下宣布消融结论**。目前 prompt-engineering 的“30~80% 下降”属于预期而非实测，任何对外表述都应标注为待验证。
6. **推理模型统一按 `temperature=1`、`max_tokens` ≥ 2000 处理**，并把 `reasoning_content` 计入预算。

---

## 九、待补测项

| 优先级 | 事项 | 目标 |
|---|---|---|
| 高 | prompt-engineering 补齐 baseline + 每配置 ≥ 5 个 task × 3 trial，并修复 `response_cost` 崩溃 | 才能对“提示质量影响幅度”给出量化结论 |
| 高 | kv-cache 修复结果落盘并改用流式 TTFT 重跑 | 才能证明缓存对延迟的真实收益 |
| 中 | context-compression 固化配置（窗口、轮数、搜索返回体量）并重跑一次，解释与早期 JSON 的数值差异 | 消除“同一实验两套数据” |
| 中 | system-hint 增加空转检测后重跑错误恢复对照 | 验证负向结论是否可被机制修复 |
| 低 | system-hint sample 任务文本改为实际存在的 `chapter1`/`chapter2` 目录 | 避免全盘搜索浪费预算 |

---

## 十、证据索引

| 实验 | 实测文档 | 结果文件 |
|---|---|---|
| kv-cache | `kv-cache/测试分析报告.md` | `kv-cache/comparison_20260824_011832.json`（86 字节，落盘失败） |
| context-compression | `context-compression/EXPERIMENT_REPORT.md`（6 策略完整对比） | `context-compression/results/experiment_20260821_121346.json`（仅 2 策略，早期运行） |
| prompt-engineering | `prompt-engineering/README.md`（含预期结论）、`prompt-engineering/GPT5_CONFIGURATION.md` | `prompt-engineering/results_ablation/` 4 个 JSON |
| system-hint | `system-hint/测试分析报告.md`（含第十节错误恢复对照）、`system-hint/analysis.txt`、`system-hint/NOTES.md` | `system-hint/demo_output/`、`trajectory.json` |

**数据取舍原则**：多处文档与实测数据冲突时，以带具体运行时间、原始输出与结果文件的数据为准；`chapter2/project_analysis_report.md` 与 `system-hint/project_analysis_report.md` 中的部分表述（如 kv-cache “TTFT 0.82s→0.19s”、prompt-engineering “30~80% 下降”）为预期或早期版本，本报告不沿用。
