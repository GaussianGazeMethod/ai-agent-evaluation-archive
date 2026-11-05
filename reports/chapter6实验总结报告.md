# chapter6 实验总结报告

**报告对象**：`chapter6` 下有实测数据支撑的 3 个子实验（AndroidWorld 基线评测、android-world 本地复现、elo-leaderboard 合成数据排行榜）
**生成时间**：2026-11-05
**数据来源**：各子项目已产出的评测报告、运行日志、轨迹文件与图片产物（见文末证据索引）。本报告对关键指标逐一回读结果文件核对，不以文档中的结论表述为准。

> 排除说明：
> - `elo-leaderboard` 的 `main.py` 真实 Chatbot Arena 数据链路：目录内无 `arena_data.json`，无任何结果 JSON/CSV，README 中的"2GB 数据、2-3 分钟处理、并行加速"均无运行产物可核对，不纳入实测结论。
> - `elo-leaderboard` 的 `animation.py`、`parallel_processing.py`、`optimized_elo.py`、`leaderboard.py`、`benchmark.py`：仅有实现代码，无独立运行记录或输出文件。
> - `android-world` 的 `t3a_summary.md` 中"按能力标签 × 难度"的诊断矩阵：无法回溯到逐任务明细，仅作为背景信息引用，不作为独立证据。

---

## 一、总览

| 实验 | 验证命题 | 模型/规模 | 样本量 | 实测结论 | 证据强度 |
|---|---|---|---|---|---|
| AndroidWorld 基线评测 | GUI Agent 能否在真实 Android 上完成 116 个跨应用任务 | Claude 4 Sonnet；116 任务 | 日志 110 次运行 / 汇总表 116 行 | 真实成功率 35.3%（41/116），非文档声称的 88%；88% 实为"正常终止率" | 中低 |
| android-world 本地复现 | 用 Mock 设备 + 纯无障碍树文本能否完成同一批任务 | qwen3.8-flash；Clock 单应用 | 1 个任务 / 7 步 | 7 步完成"16 分 35 秒定时器且不启动"，原版同任务 10 步失败 | 中低 |
| elo-leaderboard 合成数据 | Bradley-Terry MLE 与 Online Elo 能否恢复预设的能力排序 | 10 个模型；5000 条对战 | 5000 条（固定 seed=7） | 两法排名相关系数 0.9971，预设排序被完整恢复 | 中 |

一句话总结：三项实测中仅 Elo 指标自洽，AndroidWorld 的 88% 成功率回读为 35%，本地复现仅 1 条轨迹。

---

## 二、AndroidWorld 基线评测：116 任务中真实成功 35%，88% 是正常终止率

### 2.1 设计

- 任务集：116 个任务，覆盖 Clock、Contacts、Expense、Markor、OsmAnd、Recipe、SimpleCalendar、SimpleSMS、SportsTracker、System、VLC 等应用。
- 感知输入：屏幕截图 + 无障碍树；动作空间为 `open_app` / `click` / `input_text` / `scroll` / `navigate_home` / `navigate_back` / `status`。
- 验证方式：任务结束后由环境校验器（如 `sqlite_validators.py` 对比数据库前后状态）判定成败，非 Agent 自报。
- 运行形态：每个任务 1 次试验（`num_complete_trials` 为 0 或 1，无重复试验，故无方差估计）。
- 产物：
  - `t3a.md`：完整逐步推理日志，含 `W0702 HH:MM:SS` 运行时间戳；
  - `t3a_failed.md`：失败任务日志子集；
  - `t3a_summary.md`：116 行汇总表；
  - `t3a_failed_analysis.md`：按失败类型的归因分析。

### 2.2 实测数据

对 `t3a_summary.md` 表格逐行解析（116 行，6 列：`task_num`、`num_complete_trials`、`mean_success_rate`、`mean_episode_length`、`total_runtime_s`、`num_fail_trials`），并回读 `t3a.md` / `t3a_failed.md` 交叉核对：

| 指标 | 文档声称值 | 结果文件实测值 | 核对结论 |
|---|---|---|---|
| 任务总数 | 116 | 汇总表 116 行；`t3a.md` 仅 110 次运行 | 冲突（日志缺 6 个任务） |
| 总体成功率 | 88%（写作"102/116"） | 汇总表 `mean_success_rate` 列：41 行 = 1.0，61 行 = 0.0，14 行 = NaN；41/116 = 35.3%；若只计正常终止的 102 行则为 41/102 = 40.2% | 冲突 |
| `num_complete_trials` 均值 | 被表述为"成功率 0.88" | 0.8793（102/116） | 文档把终止率读成败率 |
| `num_fail_trials` 均值 | 0.12，即"12% 失败率" | 0.1207，仅覆盖 14 个"未完成回合"；实际失败 61/116 = 52.6% | 冲突（口径） |
| 平均回合长度 | 13.45 步 | 13.45（102 个非 NaN 行均值；仅 41 个成功任务为 10.85） | 一致（源文档"仅成功任务参与平均"的表述有误） |
| task 0-81 成功率 | 全部 1.00 | 37 成功 / 45 失败，成功率 45.1%（失败率 54.9%） | 冲突 |
| task 93-101 成功率 | 全部 1.00 | 4 成功 / 5 失败，44.4% | 冲突 |
| 步数耗尽失败数 | 28（`t3a_failed_analysis.md`） | `t3a_failed.md` 出现 28 次 `Reached max number of steps`；`t3a.md` 出现 33 次 | 部分一致（28 仅为失败日志子集） |
| 失败原因构成 | 未给出可核对的动作序号 | `t3a_failed.md` 52 次失败 = 28 次超时 + 3 次声明不可行 + 21 次校验不通过 | 文档未拆解 |
| `ClockTimerEntry` | 归入"复杂 UI 理解失败" | 日志第 10 步 `Reached max number of steps` 后 `Task Failed`；汇总表 `success=0.0` 但 `num_fail_trials=0.00` | 结果一致，行内字段自相矛盾 |
| Agent 主动声明不可行 | 日志标记 `Task Successful` | 4 个任务（`ClockStopWatchPausedVerify`、`OsmAndTrack`、`SimpleSmsResend`、`SimpleSmsSendReceivedAddress`）在日志中均出现 `infeasible`；其中仅 `ClockStopWatchPausedVerify` 判 `Task Successful`，其余 3 个判 `Task Failed`；汇总表 4 行均为 `complete=1.00`、`fail=0.00` | 冲突（汇总表未记录失败计数） |

失败任务按应用聚合（61 个失败任务）：

| 应用 | 失败数 | 代表任务 |
|---|---|---|
| SimpleCalendar | 15 | `AddOneEvent`、`EventsOnDate`、`NextEvent` |
| Markor | 12 | `TranscribeReceipt`、`TranscribeVideo`、`EditNote` |
| Recipe | 7 | `DeleteDuplicateRecipes1/2/3`、`AddMultipleRecipesFromImage` |
| SportsTracker | 6 | `ActivitiesCountForWeek`、`TotalDurationForCategoryThisWeek` |
| System | 6 | `BrightnessMax/Min`、`CopyToClipboard`、`WifiTurnOff` |
| SimpleSms | 5 | `Reply`、`Resend`、`Send` |
| 其他（Audio/Browser/Clock/Expense/OsmAnd/Retro/SimpleDraw） | 10 | `ClockTimerEntry`、`ExpenseAddMultipleFromGallery` |

### 2.3 结论

1. 116 个任务里真正通过环境校验的只有 41 个，成功率 35.3%；日志侧独立统计为 38/110 = 34.5%，两路数据基本一致，说明"88%"不是成功率。
2. 88% 对应的是 `num_complete_trials` 均值 0.8793，即"Agent 正常结束回合的比例"；把终止率当成功率，使成功率被高估 53 个百分点（0.88 与 0.35）。
3. 失败并非集中在文档所说的"task 82 与 102-115"：0-81 区间也有 45 个失败（失败率 54.9%），93-101 区间也有 5 个失败。
4. 52 次失败中 28 次是步数耗尽、21 次是"Agent 自报完成但数据库校验不通过"，后者占比 40.4%，属于"假完成"，比超时更隐蔽。
5. 4 个任务在日志中都出现 `infeasible`，但汇总表把它们全部记为 `complete=1.00`、`fail=0.00`；日志里仅 `ClockStopWatchPausedVerify` 判成功，其余 3 个判失败。汇总表的 `complete` 与 `success` 字段混用，使这 4 个任务的成败归属无法从表格判断。

### 2.4 局限与问题

1. 指标口径错误（最严重）：汇总表第三列 `mean_success_rate` 均值实为 0.4（40.2%），而文档第 54 行把第二列 `num_complete_trials` 的 0.88 写成"88% 总体成功率"。
2. `num_fail_trials` 语义不清：61 个 `success=0` 的行全部为 `num_fail_trials=0`；14 个 `num_fail_trials=1` 的行恰好是 `success=NaN` 的 14 个未完成回合。失败任务没有被计入失败计数，0.1207 的均值只反映未完成回合。
3. `ClockTimerEntry` 行内矛盾：`success=0.0`、`num_fail_trials=0.00`、`mean_episode_length=10.00` 三个字段不能同时成立（既失败又无失败计数、且有完整步数）。
4. 日志不完整：116 个任务中 `t3a.md` 只出现 110 次运行，缺 6 个任务（`AudioRecorderRecordAudio`、`AudioRecorderRecordAudioWithFileName`、`BrowserDraw`、`BrowserMaze`、`BrowserMultiply`、`CameraTakePhoto`）；另有 10 个运行片段在文件中没有结果标记（无 `Task Successful` / `Task Failed` / `Agent stopped`）。
5. 失败分析文档的"28 个超时"仅统计 `t3a_failed.md`，全量日志为 33 次，存在 5 次遗漏。
6. `t3a_failed_analysis.md` 对 `SportsTrackerActivitiesCountForWeek` 的表述自相矛盾：同段既写"在第 10 步它给出了答案 2"，又写"Agent did not indicate task is done. Reached max number of steps"，且未给出可核对的动作序号与校验输出。
7. 每任务 1 次试验（`num_complete_trials` ∈ {0,1}），无重复运行，无法给出成功率置信区间。

---

## 三、android-world 本地复现：同一 Timer 任务 7 步通过，原版 10 步失败

### 3.1 设计

- 环境：纯 Python `MockAndroidDevice`，实现主页 Launcher 与 Clock 应用状态机（Tab 切换、Timer 数字键盘、Start/Pause/Reset、Stopwatch）。
- 感知输入：只有无障碍树文本（无截图、无视觉模型），元素以 `index` 定位。
- 模型：qwen3.8-flash（dashscope OpenAI 兼容接口），`temperature=0.1`，`response_format=json_object`。
- 约束：`max_steps=25`；连续 3 次非法动作或连续 3 次执行失败即终止。
- 任务：`Create a timer with 0 hours, 16 minutes, and 35 seconds. Do not start the timer.`（与 `t3a.md` 中 task 9 同题）。
- 产物：`last_run_trajectory.json`（含目标、成败、每步 observation / reason / action / result）。

### 3.2 实测数据

| 步骤 | 动作 | 执行结果 | 备注 |
|---|---|---|---|
| 1 | `open_app Clock` | 已打开 Clock | - |
| 2 | `click index=5` | 切换到 Timer Tab | - |
| 3 | `click index=3` | 输入 1，显示 `00h 00m 01s` | 中间态 |
| 4 | `click index=8` | 输入 6，显示 `00h 00m 16s` | 中间态 |
| 5 | `click index=5` | 输入 3，显示 `00h 01m 63s` | 中间态（原版在此判定"格式无效"） |
| 6 | `click index=7` | 输入 5，显示 `00h 16m 35s` | 达到目标值 |
| 7 | `status complete` | Agent 报告完成 | 未点击 Start，满足"Do not start" |

轨迹字段核对：`goal` 与任务一致；`success=true`；`steps` 长度 7；第 7 步动作为 `status`，无后续动作。轨迹中不含 `timer_running` 与数字序列字段，`run_demo.py` 只把这两项打印到终端，未写入轨迹也未做断言。

对照原版：`t3a.md` 中同任务在第 10 步被判定 `Reached max number of steps`，最终 `Task Failed`；`t3a_failed_analysis.md` 描述其过程为"输入 1、6、3 后看到 `00h 01m 63s`，判定为无效格式，用三次退格清零，再重复同样的错误输入"，直到超时。

### 3.3 结论

1. 同一任务、同一目标表述下，本地实现 7 步通过，原版 10 步失败（step 6-8 用三次退格清零，step 9-10 重复输入 1、6 后超时）；差异集中在第 5 步之后是否继续输入。
2. 本地实现的成功不依赖"发现错误再纠正"，而是依赖"接受中间态并继续输入"，第 5 步显示 `00h 01m 63s` 时未触发任何纠错动作。
3. Mock 的输入模型与真实 Clock 一致：数字右对齐填充 6 位，`1,6,3` 得到 `00h 01m 63s`，补第 4 位后进位为 `00h 16m 35s`；这一行为在原版日志中被同构复现。
4. 本地实现的"完成"只由 Agent 自报 `status=complete` 判定；`run_demo.py` 虽然打印 `timer_running` 与数字序列，但既不写入轨迹也不参与 `success` 计算，且不含原版的环境校验器（sqlite validator），因此两边的"成功"含义不同。

### 3.4 局限与问题

1. 样本量 n=1，只有一条轨迹，不能给出成功率，也不能替代 116 任务评测。
2. 变量不可分离：本地与原版同时改变了模型（qwen3.8-flash vs Claude 4 Sonnet）、感知模态（纯文本 vs 截图+文本）、验证器（Agent 自报 vs 环境校验）三项，任何差异都无法归因到单一因素。
3. Mock 的 Clock 输入逻辑由人工依据原版日志复刻，未在真机验证；例如真机在 `00h 01m 63s` 状态下继续输入是否必然进位，本项目没有独立证据。
4. 仅实现 Clock 一个应用，`open_app` 到其他应用会落到占位 UI，覆盖范围远小于原版 15 个应用。
5. 成功判定完全依赖 Agent 自报：`success` 来自 Agent 发出的 `status complete`，`run_demo.py` 没有状态断言（`timer_running` 与数字序列仅打印）。若 Agent 提前报告完成而目标未达成，本 Mock 不会像原版校验器那样发现，机制明显弱于环境校验。

---

## 四、elo-leaderboard 合成数据排行榜：两种方法排名相关 0.9971

### 4.1 设计

- 数据来源：不使用 Chatbot Arena 真实数据（该链路无产物），改为按预设 `true_ratings`（GPT-4o 1400 → Qwen2.5-7B 950，步长 50）用 Elo 期望胜率采样生成对战，`seed=7`，5000 条，平局概率固定 5%。
- 方法一：Bradley-Terry MLE + 100 轮 Bootstrap 95% 置信区间（Chatbot Arena 官方方法）。
- 方法二：Online Elo，`initial_rating=1000`，`k_factor=4`（官方值），顺序更新。
- 输出：`demo_leaderboard.png`、`demo_rating_dist.png`、`demo_win_rate_matrix.png`。
- 前置修复：`quickstart.py` 原先以模型名作为 `outcome` 传入，`update_ratings` 只识别 `model_a` / `model_b` / `tie`，导致全部对局退化为平局、所有 rating 恒为 1000；已改为标准 `outcome` 枚举。`visualization.py` 的 4 处 `plt.show()` 已移除并切换到 `Agg` 后端。

### 4.2 实测数据

| 指标 | 实测值 | 说明 |
|---|---|---|
| 合成对战样本量 | 5000 条 | 生成时固定 seed=7，可复现 |
| 平局比例 | 设定 5% | 人为参数，非实测分布 |
| BT vs Online Elo 排名相关系数 | 0.9971 | 两套 rating 逐模型对齐后计算 Pearson 相关 |
| BT 第 1 名 | GPT-4o，rating 1257.4，95% CI [1235.5, 1280.0] | 与预设最强一致；bootstrap 未固定重采样种子，每次复跑有约 ±3 分浮动 |
| BT 第 10 名 | 774.0 | 与预设最弱（950）排序一致 |
| 排名还原情况 | 10/10 顺序与预设一致 | 无错位 |
| 可视化产物 | 3 张 PNG 已生成（215.7 KB / 122.4 KB / 373.6 KB） | 图片不含可回读的数值表 |

### 4.3 结论

1. 在 5000 条、10 模型的规模下，顺序敏感的 Online Elo（K=4）与顺序无关的 Bradley-Terry MLE 给出几乎相同的排名（相关系数 0.9971），说明该规模下"匹配顺序"对最终排名影响可忽略。
2. 合成数据的预设能力梯度被完整恢复，10 个模型的排序与预设 10/10 一致，说明管线（数据装载 → 评分 → 排行榜 → 可视化）在流程上是通的。
3. Bootstrap 给出的 Top-1 置信区间宽度为 44.5 分（1235.5 至 1280.0），与其相邻模型 50 分的真实差距量级相当，即"第 1 与第 2 的差距接近置信区间宽度"，名次可分性处于边界。
4. `quickstart.py` 的 `outcome` 传参缺陷会让整套更新静默失效（rating 恒 1000、胜场恒 0），且不抛异常；这是无校验字段时的典型静默失败。

### 4.4 局限与问题

1. 无结果 JSON/CSV：全部数值仅存在于终端输出与 PNG，PNG 无法回读 rating 与 CI，本报告因此只能标注"中"级证据。
2. 结论建立在合成数据上：平局率 5% 与 rating 间距 50 均为人为设定，不能外推到真实 Chatbot Arena 的分布（真实平局率与模型密度未知）。
3. 真实数据链路完全未运行：README 所称"2GB 数据、处理 2-3 分钟、Numba 与多核加速 50-100 倍"在本目录内没有任何可核对产物，本报告不采用这些说法。
4. `quickstart.py` 的修复属于代码缺陷修复，不构成实验；但该缺陷此前未被任何测试捕获，说明 `test_elo.py` 未覆盖 `outcome` 传参路径。
5. Bootstrap 仅固定轮数（100），未记录重采样种子，CI 的逐次可复现性不成立。

---

## 五、跨实验结论

1. 三项实验都缺少统一的结构化结果文件：AndroidWorld 只有终端日志与 Markdown 汇总表，Elo 只有 PNG，本地复现只有单条轨迹；因此本报告的所有数字都必须从文本重新解析（88% → 35% 的纠错就是这样发现的）。
2. "完成率 ≠ 正确率"是两项评测型实验的共同陷阱：AndroidWorld 把 0.88 的终止率当作成功率，实际正确率 35%-40%；Elo 场景的"胜率"天然就是正确性指标，不存在该歧义，排行榜类评测比 GUI 任务更容易定义"成功"。
3. 三个实验的样本量呈断崖式分布（110 次运行 / 5000 条对战 / 1 次运行）：只有 Elo 的结论具备统计稳定性，GUI 侧的两个结论都是单点事实或单次观测。
4. 原版与本地复现对同一任务给出相反结论，但模型、感知模态、验证器三项同时变化，形成"不可归因的差异"；这说明复现实验若想定位原因，必须一次只改一个变量。
5. 三项实验都出现了"静默失败"：AndroidWorld 中 21 次 Agent 自报完成但校验不通过（假完成率 40.4%），Elo 中 outcome 传参错误导致更新静默失效，本地复现的成功判定含自报成分；三者共同指向"缺少运行时校验"这一结构性问题。

---

## 六、方法学与复现性问题处置清单

| 问题 | 涉及实验 | 处置 |
|---|---|---|
| 汇总表 `mean_success_rate` 均值被文档写成 `num_complete_trials` 均值（88% vs 40%） | AndroidWorld 基线 | 采用回读表格重算的 41/116 = 35.3%（全量）与 41/102 = 40.2%（仅正常终止），弃用文档的 88% |
| `num_fail_trials` 只统计 14 个未完成回合，与 61 个 `success=0` 不匹配 | AndroidWorld 基线 | 按 `success=0` 重新统计失败数 61，失败率 52.6% |
| `ClockTimerEntry` 行内 `success=0` 与 `num_fail_trials=0` 矛盾 | AndroidWorld 基线 | 以日志结果（超过最大步数、`Task Failed`）为准，标注该行字段不可用 |
| 4 个"声明不可行"任务：1 个日志判成功、3 个判失败，汇总表全部 `complete=1`、`fail=0` | AndroidWorld 基线 | 两套口径并列记录，不合并统计 |
| 日志缺 6 个任务、10 个运行片段无结果标记 | AndroidWorld 基线 | 分母同时给出 116（表）与 110（日志），不假设缺失片段的结果 |
| "28 个超时"只覆盖失败日志，全量为 33 | AndroidWorld 基线 | 采用 33（`t3a.md` 计数），28 标注为失败日志子集 |
| `SportsTrackerActivitiesCountForWeek` 同段出现"给出答案 2"与"未完成、超时" | AndroidWorld 基线 | 以结果标记（超时失败）为准，该任务的推理结论不作为证据 |
| 每任务仅 1 次试验，无方差 | AndroidWorld 基线 | 不给出置信区间，只报点估计 |
| n=1 轨迹，且模型/模态/验证器三变量同时改变 | android-world 本地复现 | 只作单点对照，不作成功率结论；不归因差异来源 |
| Mock 输入逻辑为人工复刻，未在真机验证 | android-world 本地复现 | 结论限定在 Mock 环境内，不外推到真机 |
| 指标仅存于终端输出，PNG 不可回读 | elo-leaderboard | 相关数值标"中"级证据，并列入待补测 P0 |
| `quickstart.py` outcome 传参导致更新静默失效 | elo-leaderboard | 记录为缺陷并修复，不作为实验结果 |
| Bootstrap 未固定重采样种子 | elo-leaderboard | CI 只作量级参考，不宣称逐次可复现 |

---

## 七、面向工程的实践结论

1. 评测表必须同时保留 `num_complete_trials` 与 `mean_success_rate` 两列并分别命名，且报告中不得互相代称；实测两者相差 0.88 与 0.40，直接把 61 个失败任务抹平。
2. 有状态 UI（如 Timer 的右对齐填充与进位）必须建模中间态：中间态 `00h 01m 63s` 在真实控件里是合法的过渡值，把它判为"无效格式"会触发"清零—重输"死循环，实测原版因此 10 步失败，本地版 7 步通过。
3. 评分/排行榜类实验必须落盘 CSV/JSON 并记录 seed 与 bootstrap 轮数；本期 Elo 的全部数值只能从终端读到，PNG 无法反查，导致结论只能给到"中"级证据。
4. `outcome` 这类枚举参数必须有测试覆盖：`quickstart.py` 传模型名时 Elo 更新退化为全平局且无异常，rating 恒为 1000、胜场恒为 0，属于典型的静默失效。
5. 失败归因要拆成"超时"与"校验不通过"：`t3a_failed.md` 的 52 次失败为 28 超时 + 3 声明不可行 + 21 校验失败，"假完成"占 40.4%，只盯超时会漏掉近一半问题。
6. GUI Agent 的成功判定不能只信 Agent 自报：原版 21 次自报完成后被数据库校验否掉；本地 Mock 目前没有状态断言（只打印 `timer_running` 与数字序列），应补足后才能与原版口径对齐。

---

## 八、待补测项

| 优先级 | 事项 | 目标 |
|---|---|---|
| P0 | 按 `success` 重算 AndroidWorld 116 任务的汇总指标并落盘 JSON | 消除"88% 成功率"误读，给出可复核的 35.3% 及其分母 |
| P0 | 为 elo-leaderboard 合成 demo 输出 results.json / CSV（含 seed、bootstrap 轮数、CI） | 让 0.9971 与 CI 可回读、可复算 |
| P0 | 补齐 `t3a.md` 缺失的 6 个任务与 10 个无结果片段 | 让日志分母与汇总表 116 对齐 |
| P1 | 本地复现扩到 ≥20 个任务（含 Calendar、Markor 文本编辑） | 从 n=1 提升到可给成功率的样本量 |
| P1 | 固定 bootstrap 重采样种子并重复 3 次 | 验证 CI 稳定性 |
| P1 | 用同一模型、同一感知模态重跑原版失败任务 | 把"模型/模态/验证器"三变量拆成单变量对照 |
| P2 | 运行 `main.py` 的真实 Chatbot Arena 数据链路 | 替换合成分布，检验真实平局率与模型密度下的排名 |
| P2 | Mock 设备扩展到 Contacts / ProExpense / SimpleCalendar | 复现更多原版失败类型（排除转录与数学类） |
| P2 | 在真机或模拟器上验证 Clock 输入进位行为 | 确认 Mock 复刻与真机一致 |

---

## 九、证据索引

| 实验 | 实测文档 | 结果文件 |
|---|---|---|
| AndroidWorld 基线评测 | `chapter6/android-world/t3a_summary.md`（116 行汇总表）<br>`chapter6/android-world/t3a_failed_analysis.md`（失败归因） | `chapter6/android-world/t3a.md`（110 次运行日志，含时间戳与逐步推理）<br>`chapter6/android-world/t3a_failed.md`（52 次失败日志） |
| android-world 本地复现 | `chapter6/android-world/run_demo.py`（运行入口） | `chapter6/android-world/last_run_trajectory.json`（7 步完整轨迹，含 goal/success/action/result） |
| elo-leaderboard 合成数据 | `chapter6/elo-leaderboard/demo_synthetic.py`（生成与评估脚本） | `chapter6/elo-leaderboard/demo_leaderboard.png`（215,697 B）<br>`chapter6/elo-leaderboard/demo_rating_dist.png`（122,367 B）<br>`chapter6/elo-leaderboard/demo_win_rate_matrix.png`（373,566 B）<br>无 JSON / CSV 结果文件 |

**数据取舍**：本报告以"结果文件 + 运行时间 + 原始输出"为准。据此，`t3a_summary.md` 中"88% 总体成功率""task 0-81 与 93-101 的 `mean_success_rate` 均为 1.00""12% 失败率"三处表述不采用，理由是同一文件表格的第三列逐行为 0/1 值、均值为 0.4，且 `num_fail_trials` 均值只覆盖 14 个未完成回合；上述三项均与表格数据直接冲突。`elo-leaderboard/README.md` 中"2GB 数据处理 2-3 分钟、Numba 与多核加速 50-100 倍"不采用，理由是目录内无对应运行产物。
