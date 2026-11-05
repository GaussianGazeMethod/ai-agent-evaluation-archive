# chapter3 实验总结报告

**报告对象**：`chapter3`（第 3 章 检索增强与用户记忆）下有实测数据支撑的 6 个子实验
**生成时间**：2026-11-05
**数据来源**：各子项目已产出的评测报告、测试分析报告、运行分析报告与结果文件（见文末证据索引）。本报告对关键指标逐一回读结果文件核对，不以文档中的结论表述为准。

> 排除说明：`dense-embedding`、`sparse-embedding` 只有服务实现与 README，无独立评测产物；`structured-index`、`structured-knowledge-extraction` 只有索引实现与说明文档，无结果文件；`user-memory-evaluation` 只提供 60 个测试用例与评测框架，本身不产生结果（作为 `agentic-rag-for-user-memory` 与 `contextual-retrieval-for-user-memory` 的数据集使用）；`chapter3-retrieval-docker` 只有 Dockerfile。以上均不纳入本报告。`retrieval-pipeline` 的启动排障记录作为基础设施证据引用，不计为独立实验。

---

## 一、总览

| 实验 | 验证命题 | 模型 / 规模 | 样本量 | 实测结论 | 证据强度 |
|---|---|---|---|---|---|
| `agentic-rag` | 多轮检索能否提升法律问答的信息覆盖 | deepseek-v4-flash，15 个法律问答 | 15 例 × 2 模式，单次 | 关键词召回 83.33% vs 36.67%（+46.67 个百分点）；耗时 8.12 倍 | 中低（复杂题回答未落盘，成功率指标失真） |
| `agentic-rag-for-user-memory` | Agent 记忆检索在三层难度上的表现 | glm-4.5-air 作答，deepseek-v4-flash 评分，9 例 | 每层 3 例，单次 | 通过 4/9；reward 0.95→0.73→0.42；耗时 39s→147s→961s | 中（耗时可复核，分数仅存于报告） |
| `contextual-retrieval` | 给 chunk 加 LLM 上下文能否提升检索准确率 | kimi-k3，7 个科技财报问答 | 7 例 × 2 模式，单次 | Agentic 与 Non-Agentic 召回同为 90.48%，无质量增益；慢 1.54 倍 | 中低（核心对照缺失，索引数据混杂） |
| `contextual-retrieval-for-user-memory` | 上下文检索 + 卡片双层记忆的端到端效果 | deepseek-v4-flash，60 例 | 每层 20 例，单次 | 实得 48 通过 / 8 失败 / 4 未评分；layer1 100%、layer2 95%、layer3 45% | 中（层间梯度清晰，但报告与结果文件多处不符） |
| `multimodal-agent` | 多模态提取三种模式在真实网关上的可用性与成本 | qwen3.7-plus / qwen3.8-max，7 级验证 | 每路径 1 次 | 图像 native 2.92s，extract 55.67s（约 19 倍）；音频全链路不可用 | 中低（能力矩阵可靠，耗时 n=1） |
| `user-memory` | 分离式记忆架构的单元正确性与端到端可用性 | kimi-k2.6，97 个离线单测 + 3 种运行模式 | 97 个单测 + 各模式 1 次 | 单测 97/97 通过；修复水位线 bug 前记忆系统实际失效 | 中（单测全 mock，端到端为定性观察） |

一句话总结：**6 个实验里，3 个给出了可复核的量化差异（agentic-rag 的召回-耗时权衡、记忆检索的难度梯度、多模态的路径成本），3 个的核心命题没有被数据支撑（contextual-retrieval 的检索增益、两层记忆的上下文增益、agentic-rag 复杂题的回答质量）。最值得记录的不是“Agentic 更好”，而是“这批实验的通过率指标普遍失真”。**

---

## 二、agentic-rag：多轮检索换来召回，付出 8 倍时间

### 2.1 设计

法律问答对比实验。知识库为本地三级检索：dense-embedding（4240，BGE-M3 + hnswlib）、sparse-embedding（4241，BM25）、retrieval-pipeline（4242，混合 + 重排）。模型 deepseek-v4-flash，经 OpenAI 兼容接口调用工具。

测试集 15 例：10 个简单题（easy/medium，覆盖故意杀人、盗窃、贪污等单一罪名）、5 个复杂题（hard，多罪并罚与竞合场景）。两种模式：

- `agentic`：ReAct 循环，自主多轮搜索、按需换关键词。
- `non_agentic`：单次检索 + 单次生成。

指标：关键词召回率、分析要点召回率、引用率、回答长度、耗时、成功率。运行时间 2026-08-27 13:39–14:56。

### 2.2 实测数据

| 指标 | Agentic | Non-Agentic | 差异 |
|---|---|---|---|
| 成功率（框架口径） | 15/15 | 15/15 | 0 |
| 平均耗时 | **271.23s** | 33.39s | **8.12 倍** |
| 总耗时 | 4068.4s | 500.9s | +3567.5s |
| 关键词召回率 | **83.33%** | 36.67% | **+46.67 个百分点** |
| 分析要点召回率 | 0.00% | 40.00% | -40.00 个百分点 |
| 有引用用例 | 9/15（60%） | 9/15（60%） | 0 |
| 平均回答长度 | 514.9 字 | 306.6 字 | +208.3 字 |

按难度：

| 难度 | Agentic 平均耗时 | Non-Agentic 平均耗时 | Agentic 关键词召回 |
|---|---|---|---|
| easy（10 题） | 64.19s | 28.32s | 83% |
| medium（2 题） | 466.40s | 33.51s | 83% |
| hard（5 题） | 443.97s | 40.41s | 不适用（改用分析要点） |

两个被文档忽略的极值：Agentic 单例最长耗时并非 complex_1 的 940.3s，而是 simple_7 的 **1297.3s**（21.6 分钟），且该例回答仅 177 字、无引用；Non-Agentic 最长 51.7s。

索引持久化改造的验证数据：三个服务重启后自动加载 dense 1381 条、sparse 1456 条、pipeline 1381 条；持久化文件 dense 48.7MB + sparse 7.7MB + pipeline 7.9MB；加载为秒级，替代原先 42 分钟（部分文档写作 47 分钟）的全量重建。

### 2.3 结论

1. **多轮检索的收益是真实的，但只体现在简单题的关键词覆盖上**。83.33% vs 36.67% 的差值可逐例复核：Agentic 在 simple_1/4/5/6/8/10 达到 100%，Non-Agentic 只有 simple_4/5/10。收益来源是首次检索命中文档时能换词重查，而不是理解力提升。

2. **速度代价与题难度强相关**。简单题 64s vs 28s（2.3 倍），中等与难题约 450s vs 35s（约 13 倍）。中等难度只有 2 例，均值为 466s，样本过少，不能当作稳定估计。

3. **“成功率 100%”是框架默认值，不是模型成绩**。结果文件中 Agentic 的 complex_1/2/3/5 回答长度为 0，complex_4 仅 104 字，但 `success` 与 `gave_answer` 全部为 true。成功率只判断“是否抛异常”，空回答也计为成功。因此“两种模式成功率相同”不能说明质量相同。

4. **分析要点召回率 0% 与 40% 的对比不可解释为 Agentic 更差**。Agentic 的 5 道复杂题有 4 道回答为空，0 分来自没有文本可匹配，而非答错；Non-Agentic 的 40% 来自 complex_3 命中 100%、complex_4 命中 66.7%。这组数字同时污染了两边。

5. **索引持久化是本次最确定的工程收益**。288 篇文档、1397 个 chunk 的全量索引从 42 分钟降到秒级加载，且正常重启、索引缺失、增量索引三种场景均验证通过。

### 2.4 局限与问题

- **复杂题证据链断裂**：4/5 复杂题回答未落盘（B6，未修复），任何“Agentic 对复杂案例分析更全面”的说法在本仓库内都无法验证。
- **三个服务的数据量不一致**：索引记录为 1397 个 chunk，实际加载 dense 1381、sparse 1456、pipeline 1381。dense 比索引总数少 16 条，sparse 多 75 条，说明各服务写入/过滤口径不同，检索时的候选集合并不等价。
- **索引耗时口径不一致**：同一份 BUG 总结里同时出现“42 分钟”和“47 分钟”，测试报告背景写 47 分钟、附录写 42 分钟。对外引用时应以 42 分钟（有终端输出）为准，但差异未被解释。
- **`max_iterations` 配置不生效**：`AgentConfig` 中有该字段，`agent.py` 的 `query()` 仍以函数参数默认值 20 运行，硬任务无法通过配置放宽轮数。
- 知识库只有法律条文，没有司法解释，盗窃/贪污/交通肇事的数额标准类问题必然缺答案。
- 每例只跑 1 次，没有重复试验，`reward` 与耗时的方差未知。

---

## 三、agentic-rag-for-user-memory：难度上升，reward 下降，迭代次数几乎不变

### 3.1 设计

在 60 个用户记忆用例中按难度各取 3 个（共 9 个），验证 Agent 能否通过工具检索对话历史回答需要长期记忆的问题。分块 20 轮、重叠 2 轮，`hybrid`（Dense + Sparse）+ BGE-reranker-v2-m3 重排，开启前后文预览。

模型分工：Agent 作答为 BigModel `glm-4.5-air`，LLM Judge 评分与工具决策为 `deepseek-v4-flash`。通过标准文档写为 `reward >= 0.6`。运行日期 2026-08-28。

### 3.2 实测数据

| 层级 | 通过 | 平均 reward | 平均迭代 | 平均工具调用 | 平均耗时 |
|---|---|---|---|---|---|
| Layer1 简单检索 | 3/3（100%） | 0.95 | 2.7 | 1.7 | 39.3s |
| Layer2 多对话关联 | 1/3（33.3%） | 0.73 | 4.0 | 3.0 | 146.7s |
| Layer3 复杂推理 | 0/3（0%） | 0.42 | 4.3 | 3.3 | 961.0s |
| 合计 | 4/9（44.4%） | 0.70 | — | — | — |

逐例：0.95 / 1.00 / 0.90；0.85 / 0.55 / 0.78；0.50 / 0.45 / 0.32。耗时与迭代次数可从 `results/trajectory_*.json` 复核，与报告一致（如 layer3_12 为 1527.8s、5 轮、4 次工具调用）。

失败模式按报告归纳为三类：跨对话最新约束丢失（layer2_14 漏掉“鼠尾草绿停产、11 月 1 日前需重选布料”）、执行细节遗漏（layer2_12 漏掉路由号、memo、电汇费）、隐式因果链未建立（layer3_12 的 17 项必要信息中 12 项为 0；layer3_09 的 9 项全部低于 0.2）。

### 3.3 结论

1. **难度梯度是本次最稳健的观察**：reward 0.95→0.73→0.42，通过率 100%→33%→0%，耗时 39s→147s→961s，三个维度同向单调。

2. **迭代次数几乎不随难度增长（2.7→4.3），reward 却断崖式下降**。这说明失败不是“检索次数不够”，而是“检索到了也不会用”：Layer3 的失败用例全部有检索返回，瓶颈在多线索汇聚与结论生成。这一条比“加大 max_iterations”的建议更有解释力。

3. **卡片层（第一层）在简单题上足够用**，Layer1 平均只需 1.7 次工具调用即可答对；一旦问题需要跨对话时间线，工具调用升到 3 次以上仍不够。

4. **“4/9 通过”建立在 n=3/层 的样本上，只能说明方向，不能给出稳定比率**。同一层内 0.55 与 0.85 并存，单例波动大于层间差异。

### 3.4 局限与问题

- **分数不可复核**：trajectory JSON 只保存时间、迭代、工具调用，没有 `reward`/`passed`。报告中的 9 个分数没有对应的结果文件字段，只能采信文档。
- **通过标准与判定结果自相矛盾**：文档写明 `reward >= 0.6` 通过，但 layer2_12 的 reward 为 0.78 仍被标为 FAIL。要么 LLM Judge 返回了显式 `passed=false`，要么阈值实际不是 0.6，两种情况下“通过标准”表述都不准确。
- **总耗时口径不明**：报告写“约 85 分钟”，但 9 例单例耗时之和为 3441.0s（57.4 分钟），差额应来自每例重建索引的时间，文档未说明是否计入。
- 每层只从 20 个用例中取 3 个，取法未说明（是否随机、是否覆盖失败模式未知）。
- 报告建议把 `max_searches_per_query` 从 3 提到 5~8、`max_iterations` 从 10 提到 15，但没有对应的验证运行，属于推测性建议。

---

## 四、contextual-retrieval：机制跑通，增益未测

### 4.1 设计

验证 Anthropic Contextual Retrieval：分块后先用 LLM 为每个 chunk 生成 2~3 句描述性上下文，拼接原文后再做 BM25 与 Embedding 双路索引。

按 L0~L6 逐层验证：L0 三服务启动、L1 Dense 检索、L2 BM25 检索、L3 Pipeline 混合 + 重排、L4 LLM 生成上下文并索引检索、L5 AgenticRAG 三模式问答、L6 7 个用例评测（5 simple + 2 complex）。模型 kimi-k3，本地推理在 Mac MPS 上。

### 4.2 实测数据

| 指标 | Agentic | Non-Agentic | 对比 |
|---|---|---|---|
| 成功率 | 7/7 | 7/7 | 持平 |
| 关键词召回率 | 90.48% | 90.48% | 持平 |
| 引用覆盖 | 7/7 | 7/7 | 持平 |
| 平均耗时 | 54.11s | 35.17s | Agentic 慢 1.54 倍 |
| 总耗时 | 378.8s | 246.2s | +132.6s |
| 平均回答长度 | 697.4 字 | 356.4 字 | Agentic 更长 |

L4 核心证据：1 个 chunk，Kimi K3 用 3.90s 生成 122 token 上下文；索引 2.1s；dense 检索约 13s/次；`contextual=true` 标记在 pipeline 元数据与最终引用 `[Doc: tech_2023_ctx_0]` 中均保留。

本地推理耗时：BGE-M3 加载 80.92s、单次 embedding 约 13s、BGE-Reranker 加载约 30s、单次重排约 22s、hybrid + rerank 合计约 35s/query。LLM 成本合计约 0.003 元。

### 4.3 结论

1. **数据结构层面验证成功**：`context` 字段、`contextualized_text` 拼接、索引元数据标记、下游引用四环完整，说明“先加上下文再索引”的工程链路可用。

2. **检索准确率层面的增益没有被测量**。7 个用例的答案全部集中在同一份 2023 科技财报文档中，单跳检索即可命中；Agentic 与 Non-Agentic 的关键词召回完全相同（90.48%），说明多轮检索在此语料上没有增量。更关键的是没有跑“contextual 开 / 关”的同语料对照。

3. **90.48% 是关键词写法造成的，不是检索差距**。两个 66.7% 的用例（simple_2、simple_4）是评测集把 `394B` 与 `$394 billion` 当成不同关键词，模型统一输出 `$XXX billion`；规范化为“数字 + 数字 billion”后实际为 100%。

4. **Agentic 在单跳语料上没有质量优势，只增加耗时**。easy 组 67.08s vs 30.72s（2.18 倍）；medium/hard 组 Agentic 反而更快（27.7s vs 54.1s、15.7s vs 38.5s），报告归因为 MPS 请求排队，而非机制优势。这组“反常”数据不能用来支持 Agentic 更高效。

5. **真实瓶颈在本地重排，不在 LLM**。单次 hybrid + rerank 约 35s，其中 rerank 占 22s；LLM 全流程成本约 0.003 元。优化方向应是重排设备与候选数，而不是提示词或模型选择。

### 4.4 局限与问题

- **核心命题缺对照**：项目目标是证明“加上下文能提升检索准确率”，但唯一可引用的对比是 Agentic vs Non-Agentic，二者召回相同，且都不区分 contextual 与否。L4 的“检索正确”只是命中了包含答案的 chunk，不足以证明上下文前缀起了作用。
- **索引数据集混杂**：启动时 dense 只有 86 条（来自更早的客服对话测试），sparse 1542 条，pipeline 1466 条，且与本次 L4 的 2 条 contextual chunk 共用。检索结果的 score 对比（0.663 vs 0.642）在这种混杂索引上不具备解释力。
- **L4 的相关性存疑**：查询 “AI investment” 的 top1 返回 Apple 2023，而语料中 AI 研发支出增长 30% 的是 Google；“the company's revenue growth” 的 top1 也只能说明命中了含 revenue 的块。报告把这些都记为“检索正确”，口径偏宽。
- **时间口径不一致**：报告写 L6 执行 16:27~16:46（约 19 分钟），而指标中的两种模式总耗时为 625.0s（10.4 分钟），差额未说明。
- 引用数均值与结果文件不符：报告写 Agentic 2.7 / Non-Agentic 3.3，按逐例引用数计算为 2.57 / 3.0。
- 单例耗时受 MPS 排队影响显著，simple_3 的 122.1s 与 complex_2 的 15.7s 不能放在同一分布里比较。

---

## 五、contextual-retrieval-for-user-memory：60 用例的真实成绩与报告失真

### 5.1 设计

60 个用例，layer1/2/3 各 20 个，对话规模随层级递增（平均 103 / 218 / 331 条消息）。每例独立索引：对话分块 → LLM 生成上下文前缀 → LLM 抽取记忆卡片 → Agent 作答 → LLM Judge 评分。

双层记忆：第一层为 Advanced JSON Cards 常驻上下文，第二层为 Contextual Chunks 按需检索。检索服务为本机三件套，重排改 CPU（`RERANKER_DEVICE=cpu`、`RERANKER_MAX_LENGTH=512`），客户端超时 120s。模型 deepseek-v4-flash，评分走直接 API 调用（路径 B）。

### 5.2 实测数据（以结果文件为准）

| 层级 | 通过 / 评分 / 总数 | 平均 reward（已评分） | 检索块 | 总耗时 |
|---|---|---|---|---|
| layer1 无检索基线 | 18 / 20 / 20 | 0.943 | 0 | 21.5 min |
| layer1 真检索 | 20 / 20 / 20 | 0.985 | 74 | 21.5 min |
| layer2 | 19 / 19 / 20 | 0.854 | 137 | 33.8 min |
| layer3 | 9 / 16 / 20 | 0.566 | 209 | 43.9 min |
| 合计 | **48 通过 / 8 失败 / 4 未评分** | — | 420 | 99.2 min |

layer1 基线与真检索的两个差异用例，实际值为 insurance_claim 0.55→1.00、cellphone_upgrade 0.55→0.90（报告写成 0.55→0.90 与 0.55→1.00，两值互换）。

layer3 的 4 个未评分用例（layer3_12、layer3_11、layer3_08、layer3_17）在结果文件中 `llm_evaluation` 为 null、回答长度为 0，但 `success` 为 true。

报告值与结果文件的差异：

| 指标 | 报告值 | 结果文件实际值 |
|---|---|---|
| 总通过 | 52/60（86.7%） | 48 通过 + 4 未评分 = 52 个 success，但其中 4 个是空回答 |
| layer3 通过 | 13/20（65%） | 9 通过 + 4 未评分（有效分母 16，9/16=56.3%） |
| layer2 平均 reward | 0.73（三例 0.85/0.55/0.78） | 0.854（19 例） |
| layer3 平均 reward | 0.42（三例 0.50/0.45/0.32） | 0.566（16 例） |

报告 3.2/3.3 节的逐例数值（0.85、0.55、0.78、0.50、0.45、0.32）与 `agentic-rag-for-user-memory` 的 9 例评测完全一致，可判定为从另一份实验拷贝，而非本次 60 例运行的结果。

### 5.3 结论

1. **层间梯度真实存在**：layer1 20/20、layer2 19/20、layer3 9/20（含 4 个未评分），难度上升后通过率下降。以已评分样本计，layer3 为 9/16。

2. **真检索对 layer1 有可量化增益**：通过数 18→20，平均 reward 0.943→0.985，检索块 0→74，代价是单例耗时约翻倍（32s→64s）。两个原本失败的用例都是靠第二层检索补全细节。

3. **layer3 的失败不是检索故障**：8 个失败用例的 `chunks_retrieved` 均大于 0（2~21 块），说明检索链路正常返回，失败发生在多线索汇聚与最终结论生成。这与 `agentic-rag-for-user-memory` 的结论一致。

4. **“86.7% 通过率”被空回答抬高**。4 个空回答既没有评分也没有内容，却被计入 success；按有效样本计算为 48/56 = 85.7%，按全量且把未评分视为未通过则为 80.0%。对外只能引用后两个口径。

5. **同一份报告混用了两次实验的数据**。总表（20/19/13）来自 60 例运行，逐例分析表（3/3、1/3、0/3）来自 9 例运行，两者被拼在同一份文档里，这是本次最严重的数据可信度问题。

### 5.4 局限与问题

- 报告内部矛盾：“8 个失败中 1 个为空回答”与“空回答类失败 2 例”同时出现，实际结果文件里 layer2 与 layer3 各 1 类，共 2 个空回答（layer2_20 与 layer3 的 4 个 null 中的一部分），表述不统一。
- 4 个空回答的判定代码路径是 `llm_evaluation` 为空时沿用运行态 `success`，等价于“没评分就算通过”，与 `agentic-rag` 的 B6 是同一类缺陷。
- 没有跑 contextual 开 / 关对照；layer1 的基线是“无检索”，不是“无上下文”，因此不能把 0.943→0.985 归因于上下文感知。
- 每例只运行 1 次，层内方差未知。
- CPU 重排单次 7~38s，是 layer3 单例 132s 的主要来源，不同用例的耗时不可直接横向比较。
- 路径 B 判分未与框架原生路径 A 做过校准，分数口径只在本次运行内可比。

---

## 六、multimodal-agent：网关能力实测决定路由

### 6.1 设计

原设计对比 Gemini / OpenAI / Doubao 三家 provider 的 native / extract_to_text / tools 三种多模态提取方式。因缺少三家有效 key，改为全部走阿里云百炼专属网关（OpenAI 兼容模式），并先对网关做能力实测，再按实测结果确定路由。

验证按 L0~L7：依赖与 key、纯文本流式、图片 native、图片 extract（描述 + 问答两段式）、PDF extract（pypdf 本地解析）、tools 三工具、交互模式、三模式 × 三模型全量对比。

### 6.2 实测数据

网关能力矩阵：

| 能力 | 结论 | 证据 |
|---|---|---|
| 文本对话 / function calling | 可用 | qwen3.7-plus 等文本模型全部通过 |
| 图像理解（base64 image_url） | qwen3.8-max / 3.8-flash / 3.7-plus / 3.6-flash 可用；qwen3.7-max 拒绝 | 红蓝测试图均正确识别 |
| 音频（input_audio / audio_url / transcriptions） | 不可用 | ASR 400；omni 报 “modal audio not supported”；transcriptions 404 |
| PDF 文件上传（files.create / file-extract） | 不可用 | 404 Api not found |

性能（单次样本）：

| 路径 | 耗时 | 说明 |
|---|---|---|
| native 图片 | 2.92s | 1 次模型调用 |
| extract 图片 | 55.67s | 2 次串行调用（描述 + 问答） |
| extract PDF | 26.23s | pypdf 本地解析 + 1 次问答 |
| extract 后追问 | 11.03s | 追问实际无文件上下文 |

L0~L7 全部通过。

### 6.3 结论

1. **路由必须由实测决定，不能按公开文档推测**。同一网关内，图像能力按模型分裂（3.7-max 为纯文本），音频与文件上传完全缺失。最终路由：图像 → qwen3.8-max；PDF → pypdf 本地解析 + 文本模型；音频 → 明确报错。

2. **图像场景 native 全面占优**：2.92s vs 55.67s，约 19 倍差距，且 native 为单次调用、保真度更高。extract 的理论优势（文本可缓存复用）在当前实现中未兑现。

3. **PDF 场景没有选择余地**：网关无文件抽取接口，extract + pypdf 是唯一可用路径，本地解析成本可忽略，26.23s 主要来自问答调用。

4. **“明确失败”优于静默降级**：音频工具返回不可用说明，而不是返回空结果，这让上层能区分“模型没答”与“能力不存在”。

5. **修复 4 个会直接中断实验的问题**：requirements 中 4 个错误依赖（其中一个会装上假包覆盖标准库）、流式末尾空 `choices` 导致 IndexError、工具异常砸穿对话、旧 key 残留导致 401。

### 6.4 局限与问题

- **所有耗时均为 n=1**，没有重复与均值，19 倍差距只能当量级参考。
- **extract 的第二次调用内容不可复核**：报告未保存描述文本与问答文本，无法判断 55.67s 中有多少是重试或排队。
- **追问链路实测无上下文**：`process_multimodal_content()` 的结果不写入会话历史，追问回复 “there is no previous context”；交互模式能追问是因为 main.py 每轮重新传入文件，不是记忆生效。
- **抽取结果无缓存**，与 README 宣称的 “Can cache extractions” 不符，重复提问会重复计费。
- L7 “三模式 × 三模型全量对比通过”只有结论，没有输出对照表或指标，无法验证。
- 扫描版 PDF 无 OCR，pypdf 解析为空，属网关侧限制而非代码缺陷。

---

## 七、user-memory：97 个单测全过，端到端靠修 bug 才可用

### 7.1 设计

验证“对话 Agent 与记忆处理器分离”的架构：对话 Agent 只生成回复，后台记忆处理器按对话间隔分析上下文，通过 ReAct 工具调用（add / update / delete）维护记忆，四种存储模式（notes / enhanced_notes / json_cards / advanced_json_cards）持久化为 JSON。

两个层次：

1. 离线单元测试：pytest，97 个用例，OpenAI 客户端全部 Mock，无网络。
2. 端到端运行：quickstart 双 Session、demo、interactive 三种模式，模型 kimi-k2.6。

### 7.2 实测数据

单元测试（2026-08-21）：

| 指标 | 数值 |
|---|---|
| 用例总数 | 97 |
| 通过 | 97 |
| 失败 / 错误 / 跳过 | 0 / 0 / 0 |
| 总耗时 | 约 2.8s |

模块分布：config 11、memory_manager 29、conversation_history 9、memory_operation_formatter 8、agent 19、conversational_agent 14、background_memory_processor 17。

端到端（2026-11-05）：

| 模式 | 结果 | 关键观察 |
|---|---|---|
| quickstart（notes） | 修复后通过 | 3 轮自我介绍抽 8 条记忆，2909 字节落盘；Session 2 召回全部关键事实 |
| demo（json_cards） | 通过 | 完整运行无异常 |
| interactive（advanced_json_cards） | 修复后通过 | 生成含 backstory / person / relationship 的卡片 |
| 工具链路单测 | 通过 | 单次任务触发 6 次 add_memory，全部 success |
| 去重 | 通过 | 重复处理返回 0 added / 0 updated / 0 deleted |

### 7.3 结论

1. **单元层覆盖是真实的，但验证对象是状态机而非模型**。97 个用例全部 Mock OpenAI，覆盖的是配置解析、四种存储的增删改查与持久化、格式化、ReAct 循环的分片拼接、后台处理器的水位线判断；真实模型行为不在覆盖范围内。

2. **分离式架构在端到端可用**：后台处理器按轮次间隔更新记忆，对话流程不被阻塞；quickstart 的跨 Session 召回证明持久化有效。

3. **抽取具备跨轮归纳能力**：从“切换到 JAX”推断出“PyTorch → JAX 的技术栈切换”，而不是逐条复述字面内容。

4. **本次最严重的问题是一个水位线缺陷**。`process_recent_conversations()` 的两个提前 return 分支不更新 `last_processed_count`，导致 `should_process()` 永远为 true：后台线程每秒空转刷屏、用户输入的 `quit` 被日志冲乱成 `我uit` 发往 API、分析逻辑从未执行导致记忆始终为空。三个表面症状来自一个根因，修复 2 行后同时消失。修复前 interactive 模式的记忆系统实际处于完全失效状态。

5. **另有 4 个问题会让实验直接跑不起来或被误判**：quickstart 接口版本不匹配、`MODEL_NAME` 未接线（8 处硬编码默认值）、模型名在当前账号不存在（404）、推理模型 temperature 限制漏配 K2.6/K2.7（400）。

### 7.4 局限与问题

- `evaluation` 模式与 LOCOMO 基准均未执行，缺少可量化的端到端记忆指标。
- 单测全部 Mock，没有真实 API 调用、流式输出与工具调用行为验证。
- 端到端每模式只跑 1 次，结论是定性观察。
- Advanced JSON Cards 的 `date_created` 由 LLM 生成，实测编造为 `2024-01-20`，不是系统时间；修复方案明确但未实施，会影响记忆时效判断。
- 系统 Anaconda Python 损坏（`bad CPU type in executable`），所有运行必须显式激活项目 venv，否则会误用不可用的解释器。
- `logs/` 目录未自动创建，`LOG_FILE` 配置实际只写终端。

---

## 八、证据不足或与预期不一致的三处

### 8.1 Contextual Retrieval 的核心增益未被测量

预期：给 chunk 加上下文前缀后，检索准确率应上升。

实际：7 个用例的语料只有一份财报文档，所有答案单跳可得；两种模式召回同为 90.48%，且没有 contextual 开/关对照。L4 只证明了“带上下文前缀的 chunk 能被索引、检索、引用”，没有证明“它比不带前缀的更准”。

这属于**机制验证通过、效果验证缺失**，不能按“教学验证成功”引用。唯一可确认的是结构化收益：chunk 带有可追溯的上下文与来源标记。

### 8.2 Agentic 在单跳语料上没有增益，只有成本

预期：Agentic 多轮检索应优于单次检索。

实际：`contextual-retrieval` 中 7 个用例两种模式召回完全相同，Agentic 耗时是 1.54 倍；`agentic-rag` 中增益只出现在简单题（10 例），而复杂题因回答未落盘无法评价。

两台实验共同指向：**Agentic 的收益来自“单次检索可能打偏”的场景，而不是“任务本身复杂”**。当语料小、问题单跳可解时，多轮循环只增加延迟。

### 8.3 迭代次数增加没有带来对应收益

预期：难任务应通过更多轮检索与工具调用补全信息。

实际：`agentic-rag-for-user-memory` 的迭代从 2.7 升到 4.3、工具调用从 1.7 升到 3.3，reward 却从 0.95 掉到 0.42；`contextual-retrieval-for-user-memory` 的 8 个失败用例检索块全部大于 0。

结论：**在难任务上，“检索更多”与“答得更好”之间没有观测到因果关系**，瓶颈在信息汇聚与结论生成。报告里“提高 max_iterations / max_searches”的建议缺少证据支持。

---

## 九、跨实验结论

### 结论 1：多轮检索买的召回，价格是 1.5~8 倍延迟

| 实验 | 召回变化 | 延迟变化 | 适用条件 |
|---|---|---|---|
| agentic-rag | +46.67 个百分点 | 8.12 倍 | 单次检索会打偏、需要多法条组合 |
| contextual-retrieval | 0 | 1.54 倍 | 单跳、小语料，无收益 |
| 记忆检索（L1→L3） | reward -0.53 | 24 倍 | 难度升高后收益反转 |

同一个机制在三组数据里给出三种结果，说明**“Agentic 是否更好”不是模型属性，而是语料与任务形态的函数**。

### 结论 2：难度是主导变量，聚合均值会掩盖断崖

三个分层实验都呈现同向梯度：通过率 100%→95%→45%（60 例记忆），reward 0.95→0.73→0.42（9 例记忆），耗时 39s→147s→961s。任何只报总体均值的评测（如“平均 reward 0.70”“通过率 86.7%”）都会把 layer3 的失效隐藏在一个尚可的数字后面。

### 结论 3：难任务的瓶颈不在检索，在汇聚与生成

两组记忆实验的失败用例 `chunks_retrieved` 全部大于 0（2~21 块），说明检索正常返回；失败原因是跨对话的最新约束丢失、执行细节遗漏、隐式因果链未建立。**继续加检索次数不会改善这类失败**。

### 结论 4：这批实验的“成功率”指标普遍失真

| 实验 | 判定方式 | 失真表现 |
|---|---|---|
| agentic-rag | 是否抛异常 + `gave_answer` | 4/5 复杂题回答为空仍计成功 |
| agentic-rag-for-user-memory | `reward >= 0.6`（文档） | 0.78 被判 FAIL，阈值与结果矛盾 |
| contextual-retrieval-for-user-memory | `passed` 缺失时沿用运行态 `success` | 4 个空回答计入通过，86.7% 虚高 |
| user-memory 端到端 | 人工观察 | 水位线 bug 期间系统失效但无判定 |
| multimodal-agent | 人工观察 | L7 无指标，只有“通过” |

统一教训：**成功必须定义为“回答非空 AND 评分达标”，否则任何成功率都不可引用**。

### 结论 5：本地推理是延迟地板，LLM 成本可忽略

`contextual-retrieval` 实测：BGE-M3 embedding 约 13s/query，rerank 约 22s，pipeline 合计约 35s；LLM 全流程成本约 0.003 元。`contextual-retrieval-for-user-memory` 的 CPU 重排单次 7~38s，layer3 单例 132s。**优化重排设备与候选数比优化提示词更有效**。

### 结论 6：基础设施故障数量超过算法发现数量

| 子项目 | 记录在案的基础设施/环境问题 |
|---|---|
| agentic-rag | 8 类（索引丢失、配额、Python 环境、端口、模型白名单、截断、计分、配置） |
| agentic-rag-for-user-memory | 7 个检索服务问题 + 5 个客户端问题 |
| retrieval-pipeline | 6 个启动问题（端口脚本、依赖、tokenizer、索引损坏、HF 超时、rerank 0-d） |
| contextual-retrieval-for-user-memory | 4 个检索链路问题（MPS 挂死、字段为空、跨用例污染、候选过少） |
| user-memory | 5 个运行问题，其中 1 个阻塞性 |
| multimodal-agent | 4 个依赖/流式/工具/环境问题 |

即使只统计会中断实验的问题也有 20 个以上。本项目的实际工作量主要花在“让实验能跑”上，而不是“让结论成立”上。这本身就是一条工程结论：**多服务 RAG 实验的默认状态是不可复现，必须先固化启动、索引、计分三条链路**。

---

## 十、方法学与复现性问题处置清单

| 问题 | 涉及实验 | 处置 |
|---|---|---|
| 空回答计入 success | agentic-rag、contextual-retrieval-for-user-memory | 判定改为 `len(answer)>0 && score>=threshold`，空回答记 `unscored` |
| `llm_evaluation` 为 null 时沿用 `success` | contextual-retrieval-for-user-memory | 评分缺失时 `passed=None`，不参与通过率分子分母 |
| exact 关键词匹配 | agentic-rag、contextual-retrieval | 关键词归一化（`394B` / `394 billion` 合并）或改语义/LLM 评分 |
| 报告混用两次运行数据 | contextual-retrieval-for-user-memory | 3.2/3.3 节替换为本次 60 例结果；总表与逐例表必须同源 |
| 阈值与 `passed` 矛盾 | agentic-rag-for-user-memory | 明确 `passed` 的来源（Judge 显式返回还是阈值比较） |
| 总耗时口径不明 | agentic-rag-for-user-memory、contextual-retrieval | 区分“模型耗时 / 含索引耗时 / 含重排耗时”三个口径 |
| 三个服务索引条数不一致 | agentic-rag | 1397 / 1381 / 1456 需对齐写入与过滤逻辑，或记录每服务的实际候选集 |
| 索引耗时 42 vs 47 分钟 | agentic-rag | 统一为 42 分钟并注明来源 |
| trajectory 无 reward | agentic-rag-for-user-memory | 轨迹中落盘 `reward`/`passed`/judge 理由 |
| 无重复试验 | 全部 | 关键结论至少 3 次重复，报均值与范围 |
| MPS/CPU 排队污染耗时 | contextual-retrieval、contextual-retrieval-for-user-memory | 记录 pipeline 队列长度，或串行化后重测 |
| 跨用例索引污染 | contextual-retrieval-for-user-memory | 每例 `DELETE /clear`（已修，需在结果中记录） |
| 复杂题回答未落盘 | agentic-rag | 修复 B6 后再评价分析要点召回 |
| 依赖版本未锁定原因 | contextual-retrieval | requirements 中标注 `transformers==4.36.2` 等锁定理由 |

---

## 十一、面向工程的实践结论

1. **先定义“答对”，再谈通过率**。本批数据里没有一份报告的成功率可以被直接引用，原因都是判定把“没崩”当成“答对”。

2. **Agentic RAG 应按场景开关，而不是默认开启**。单跳、小语料、低延迟场景用 non-agentic；多法条、多文档、单次检索易打偏时用 agentic。判断依据不是“问题看起来复杂”，而是“首次检索是否可能命中错误文档”。

3. **难度分层评测是必需项**。layer1/2/3 的梯度（100%→95%→45%）比总体 86.7% 更能指导优化；只报总体会得出“系统基本可用”的错误结论。

4. **检索指标与生成指标必须分开记账**。关键词召回衡量的是用词是否命中，不是法律结论是否正确；分析要点召回在回答为空时无法计算。两类指标混在一起会产出互相矛盾的结论（如 Agentic 关键词更高但分析要点为 0）。

5. **验证“上下文增强”必须做同语料 ablation**。只证明“带上下文的块能被检索到”不等于“它比不带上下文的更准”。缺这一组对照时，应把结论降级为“机制可用”。

6. **把本地推理成本算进方案设计**。重排 22s、embedding 13s 的量级决定了任何在线问答方案都必须做候选裁剪或换设备；LLM 调用成本（0.003 元/次）不是瓶颈。

7. **多服务 RAG 的启动与索引持久化要先于业务逻辑**。agentic-rag 的 42 分钟重建、retrieval-pipeline 的 6 个启动问题、记忆项目的 4 个检索链路问题，都会以“结果为空/超时”的形式伪装成算法问题。

---

## 十二、待补测项

| 优先级 | 事项 | 目标 |
|---|---|---|
| P0 | contextual-retrieval 做 contextual 开/关同语料对照 | 量化上下文前缀对 recall@k / MRR 的真实影响 |
| P0 | 修复空回答计分并重跑 agentic-rag 复杂题 | 让 5 道 hard 题有可评价的回答 |
| P0 | 统一 `passed` 判定并重跑 9 例记忆评测 | 消除 0.78 FAIL 与阈值 0.6 的矛盾 |
| P1 | contextual-retrieval-for-user-memory 按结果文件重写报告 | 消除 52/60 与 4 个未评分的统计错误 |
| P1 | 每个关键用例重复 3 次 | 给出 reward / 耗时的方差，判断层内波动 |
| P1 | 记忆实验加 non-contextual 对照（而非仅无检索） | 分离“有检索”与“有上下文前缀”的贡献 |
| P1 | 关键词匹配归一化 | 修正 90.48% 的写法偏差 |
| P2 | 重排迁 GPU 或减少候选 | 压缩 layer3 单例 132s 的延迟地板 |
| P2 | agentic-rag 补充司法解释入库 | 覆盖数额标准类问题 |
| P2 | multimodal 每路径重复 5 次 | 把 19 倍差距从单点变成区间 |
| P2 | user-memory 跑 evaluation 模式与 LOCOMO | 用外部基准替代定性观察 |

---

## 十三、证据索引

| 实验 | 实测文档 | 结果文件 |
|---|---|---|
| agentic-rag | `evaluation/测试分析报告.md`、`evaluation/评测分析报告.md`、`evaluation/BUG分析总结.md` | `evaluation/results/evaluation_results_20260827_145623.json` |
| agentic-rag-for-user-memory | `评测报告.md`、`LLM_EVALUATION.md`、`RETRIEVAL_PIPELINE_INTEGRATION.md` | `results/trajectory_layer{1,2,3}_*.json`（9 条，无 reward 字段） |
| contextual-retrieval | `EVALUATION_REPORT.md` | `results/evaluation_results_20261104_164600.json` |
| contextual-retrieval-for-user-memory | `EVALUATION_REPORT.md` | `results/evaluation_20261104_105838.json`（layer1 基线）、`..._220604.json`（layer1 检索）、`..._235142.json`（layer2）、`..._004133.json`（layer3） |
| multimodal-agent | `RUN_ANALYSIS_REPORT.md` | 无独立结果文件，数据在报告内 |
| user-memory | `RUN_TEST_REPORT.md`、`reports/SUMMARY.md`、`reports/junit_report.xml`、`reports/test_report.html` | `reports/junit_report.xml`、`quickstart_user_memory.json`、`memory_trajectory.json` |
| 基础设施（辅助） | `retrieval-pipeline/启动问题排查记录.md` | — |

**数据取舍原则**：本报告以“结果文件 + 运行时间 + 原始输出”为准。文档与结果文件冲突时按以下顺序取值：

1. 有单例记录（`elapsed_time`、`iterations`、`reward`）的结果文件；
2. 有终端输出片段的测试报告；
3. 只有结论表述的汇总/评测报告。

据此，`contextual-retrieval-for-user-memory` 的 52/60、13/20、0.73、0.42 以及两处基线 reward 均不采用；`agentic-rag` 的“成功率 100%”仍作为框架口径记录，但不作为质量结论引用。
