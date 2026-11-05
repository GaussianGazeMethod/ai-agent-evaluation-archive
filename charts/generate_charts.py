"""根据 docs/data 下的 CSV 生成六章关键数据图。

运行方式：python3 generate_charts.py
依赖：matplotlib（不依赖 numpy/pandas 以外的额外包）
所有数值均来自 data/ 目录，图表不引入任何未在报告中出现的数据。
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib import rcParams

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(BASE, "..", "data"))

# 统一视觉风格
rcParams["font.family"] = ["Arial Unicode MS"]
rcParams["axes.unicode_minus"] = False
rcParams["font.size"] = 10
rcParams["axes.titlesize"] = 11
rcParams["axes.titleweight"] = "bold"
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False
rcParams["figure.dpi"] = 200
rcParams["savefig.dpi"] = 200
rcParams["figure.facecolor"] = "white"

BLUE = "#2F6BFF"
TEAL = "#12A594"
RED = "#E5484D"
AMBER = "#F2A93B"
GRAY = "#9AA0A6"
INK = "#202124"


def read_csv(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    path = os.path.join(BASE, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("已生成", name)


def annotate_bars(ax, bars, fmt, offset=0.02, horizontal=True):
    """在柱状图外侧标注数值。"""
    for bar in bars:
        if horizontal:
            value = bar.get_width()
            ax.text(
                value + offset, bar.get_y() + bar.get_height() / 2,
                fmt.format(value), va="center", ha="left", fontsize=9, color=INK,
            )
        else:
            value = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2, value + offset,
                fmt.format(value), ha="center", va="bottom", fontsize=9, color=INK,
            )


# ---------------------------------------------------------------- 第 1 章

def chart_ch1_context():
    rows = read_csv("ch1-context-ablation.csv")
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.3]}
    )

    # 左：三套运行合计的两种判定口径（15 组）
    labels = ["协议判定\nProtocol-level", "内容校验\nContent-level"]
    passed = [13, 8]
    failed = [2, 7]
    y = range(len(labels))
    ax1.barh(y, passed, color=TEAL, height=0.5, label="判定通过")
    ax1.barh(y, failed, left=passed, color=RED, height=0.5, label="未通过")
    for i, (p, f) in enumerate(zip(passed, failed)):
        ax1.text(p / 2, i, str(p), ha="center", va="center", color="white", fontsize=11)
        ax1.text(p + f / 2, i, str(f), ha="center", va="center", color="white", fontsize=11)
        ax1.text(15.4, i, "{:.1f}%".format(p / 15 * 100), va="center", fontsize=10, color=INK)
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(labels)
    ax1.set_xlim(0, 17)
    ax1.set_xlabel("15 组运行 / 15 runs")
    ax1.set_title("同一批结果，两种判定差 33.4 个百分点")
    ax1.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.3),
               ncol=2, fontsize=9)

    # 右：PDF V2 单例耗时，颜色表示内容校验是否通过
    modes = [r["mode"] for r in rows][::-1]
    elapsed = [float(r["elapsed_s"]) for r in rows][::-1]
    real = [int(r["content_verdict_pass"]) for r in rows][::-1]
    colors = [TEAL if p else RED for p in real]
    ax2.barh(modes, elapsed, color=colors, height=0.5)
    for bar, r in zip(ax2.patches, rows[::-1]):
        ax2.text(float(r["elapsed_s"]) + 0.8, bar.get_y() + bar.get_height() / 2,
                 "{:.1f}s / {} 次迭代".format(float(r["elapsed_s"]), r["iterations"]),
                 va="center", fontsize=9, color=INK)
    ax2.set_xlim(0, 48)
    ax2.set_xlabel("单例耗时（秒）/ elapsed seconds")
    ax2.set_title("PDF V2 各模式耗时（颜色 = 内容校验结果）")
    ax2.legend(handles=[Patch(color=TEAL, label="内容校验通过"),
                        Patch(color=RED, label="内容校验未通过")],
               frameon=False, fontsize=9, loc="lower right")

    fig.text(0.01, -0.02,
             "来源：docs/data/ch1-context-ablation.csv。原始判定仅检查是否输出 FINAL ANSWER。",
             fontsize=8, color=GRAY)
    save(fig, "ch1-context-judgement.png")


def chart_ch1_llm_vs_rl():
    rows = {r["metric"]: r for r in read_csv("ch1-llm-vs-rl.csv")}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2))

    # 左：胜率对比（百分比）
    groups = ["训练阶段\nTraining", "评估阶段\nEvaluation"]
    ql = [float(rows["training_win_rate"]["q_learning"]) * 100,
          float(rows["eval_win_rate"]["q_learning"]) * 100]
    glm = [float(rows["training_win_rate"]["glm5"]) * 100,
           float(rows["eval_win_rate"]["glm5"]) * 100]
    x = range(len(groups))
    w = 0.35
    b1 = ax1.bar([i - w / 2 for i in x], ql, w, color=GRAY, label="Q-Learning")
    b2 = ax1.bar([i + w / 2 for i in x], glm, w, color=BLUE, label="GLM-5 上下文学习")
    annotate_bars(ax1, b1, "{:.2f}%", offset=1.5, horizontal=False)
    annotate_bars(ax1, b2, "{:.1f}%", offset=1.5, horizontal=False)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(groups)
    ax1.set_ylim(0, 115)
    ax1.set_ylabel("胜率（%）/ win rate")
    ax1.set_title("训练 100% 不代表评估可用")
    ax1.legend(frameon=False, fontsize=9)

    # 右：平均奖励对比
    groups2 = ["训练平均奖励", "评估平均奖励"]
    ql2 = [float(rows["training_avg_reward"]["q_learning"]),
           float(rows["eval_avg_reward"]["q_learning"])]
    glm2 = [float(rows["training_avg_reward"]["glm5"]),
            float(rows["eval_avg_reward"]["glm5"])]
    b3 = ax2.bar([i - w / 2 for i in x], ql2, w, color=GRAY)
    b4 = ax2.bar([i + w / 2 for i in x], glm2, w, color=BLUE)
    annotate_bars(ax2, b3, "{:.1f}", offset=6, horizontal=False)
    annotate_bars(ax2, b4, "{:.1f}", offset=6, horizontal=False)
    ax2.axhline(0, color="#DADCE0", linewidth=0.8)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(groups2)
    ax2.set_ylim(-80, 290)
    ax2.set_ylabel("平均奖励 / average reward")
    ax2.set_title("平均奖励：LLM 训练与评估均高于 RL")

    fig.text(0.01, -0.02,
             "样本量：Q-Learning 训练 5000 局 / 评估 100 局；GLM-5 训练 20 局 / 评估 10 局。"
             "训练耗时 2.39s 对 6960.32s。",
             fontsize=8, color=GRAY)
    save(fig, "ch1-llm-vs-rl.png")


# ---------------------------------------------------------------- 第 2 章

def chart_ch2_kv_cache():
    rows = read_csv("ch2-kv-cache.csv")
    rows = sorted(rows, key=lambda r: int(r["cached_tokens"]))
    modes = [r["mode"] for r in rows]
    tokens = [int(r["cached_tokens"]) for r in rows]
    delta = [float(r["delta_wall_time_pct"]) for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))

    # 左：缓存 token 总量（对数轴）
    bars = ax1.barh(modes, tokens,
                    color=[RED if m == "sliding_window" else BLUE for m in modes],
                    height=0.55)
    bars[[m for m in modes].index("sliding_window")].set_hatch("//")
    bars[[m for m in modes].index("sliding_window")].set_edgecolor("white")
    ax1.set_xscale("log")
    ax1.set_xlim(1000, 1200000)
    for bar, value in zip(ax1.patches, tokens):
        ax1.text(value * 1.12, bar.get_y() + bar.get_height() / 2,
                 "{:,}".format(value), va="center", fontsize=9, color=INK)
    ax1.set_xlabel("缓存 token 总量（对数轴）/ cached tokens (log)")
    ax1.set_title("稳定前缀缓存 40 万，动态元数据只剩 5 千")

    # 右：总耗时变化
    colors = [TEAL if d <= 0 else AMBER if d < 50 else RED for d in delta]
    ax2.barh(modes, delta, color=colors, height=0.55)
    for bar, d in zip(ax2.patches, delta):
        x = d + 3 if d >= 0 else d - 3
        ax2.text(x, bar.get_y() + bar.get_height() / 2,
                 "{:+.1f}%".format(d), va="center",
                 ha="left" if d >= 0 else "right", fontsize=9, color=INK)
    ax2.axvline(0, color="#DADCE0", linewidth=0.8)
    ax2.set_xlim(-115, 115)
    ax2.set_xlabel("相对 correct 的总耗时变化 / wall-time delta")
    ax2.set_title("缓存丢失的代价体现在 wall time")
    ax2.text(0.98, 0.98, "sliding_window 的 -89.8% 是任务未完成的假象",
             transform=ax2.transAxes, ha="right", va="top", fontsize=8, color=RED)

    fig.text(0.01, -0.02,
             "来源：docs/data/ch2-kv-cache.csv。模型 Kimi K3，同一任务，仅改变上下文构造方式。",
             fontsize=8, color=GRAY)
    save(fig, "ch2-kv-cache.png")


def chart_ch2_compression():
    rows = read_csv("ch2-context-compression.csv")
    names = [r["strategy"].replace("_", " ") for r in rows]
    ok = [r["outcome"].startswith("succeeded") for r in rows]
    colors = [TEAL if o else RED for o in ok]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4))
    fig.subplots_adjust(wspace=0.3)

    tokens = [int(r["total_tokens"]) for r in rows]
    ax1.barh(names, tokens, color=colors, height=0.55)
    for bar, value in zip(ax1.patches, tokens):
        ax1.text(value + 4000, bar.get_y() + bar.get_height() / 2,
                 "{:,}".format(value), va="center", fontsize=9, color=INK)
    ax1.set_xlim(0, 235000)
    ax1.set_xlabel("累计 token / total tokens")
    ax1.set_title("查询聚焦压缩把 token 压到 11 万")

    wall = [float(r["wall_time_s"]) for r in rows]
    ax2.barh(names, wall, color=colors, height=0.55)
    ax2.set_yticks([])
    for bar, r in zip(ax2.patches, rows):
        ax2.text(float(r["wall_time_s"]) + 60, bar.get_y() + bar.get_height() / 2,
                 "{:.0f}s / 溢出 {} 次".format(float(r["wall_time_s"]), r["overflow_count"]),
                 va="center", fontsize=9, color=INK)
    ax2.set_xlim(0, 7600)
    ax2.set_xlabel("总耗时（秒）/ wall time")
    ax2.set_title("零溢出策略未必最快")

    ax1.legend(handles=[Patch(color=TEAL, label="任务完成"),
                        Patch(color=RED, label="任务失败")],
               frameon=False, fontsize=9, loc="lower center",
               bbox_to_anchor=(0.5, -0.32), ncol=2)

    fig.text(0.01, -0.02,
             "任务：查清 11 位 OpenAI 联合创始人当前任职；窗口 128K，最多 20 轮，Kimi K3。",
             fontsize=8, color=GRAY)
    save(fig, "ch2-context-compression.png")


# ---------------------------------------------------------------- 第 3 章

def chart_ch3_difficulty():
    rows = read_csv("ch3-memory-60cases.csv")
    labels = ["L1 无检索", "L1 有检索", "L2", "L3"]
    passed = [int(r["passed"]) for r in rows]
    scored = [int(r["scored"]) for r in rows]
    total = [int(r["total"]) for r in rows]
    reward = [float(r["avg_reward_scored"]) for r in rows]
    minutes = [float(r["total_minutes"]) for r in rows]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    colors = [GRAY, BLUE, AMBER, RED]

    ax = axes[0]
    rates = [p / t * 100 for p, t in zip(passed, total)]
    bars = ax.bar(labels, rates, color=colors, width=0.55)
    annotate_bars(ax, bars, "{:.0f}%", offset=2, horizontal=False)
    ax.set_ylim(0, 118)
    ax.set_ylabel("通过率（%）/ pass rate")
    ax.set_title("通过率随层级下降")

    ax = axes[1]
    bars = ax.bar(labels, reward, color=colors, width=0.55)
    annotate_bars(ax, bars, "{:.3f}", offset=0.02, horizontal=False)
    ax.set_ylim(0.4, 1.08)
    ax.set_ylabel("已评分样本平均 reward")
    ax.set_title("平均 reward 同步下降")

    ax = axes[2]
    bars = ax.bar(labels, minutes, color=colors, width=0.55)
    annotate_bars(ax, bars, "{:.1f} min", offset=0.8, horizontal=False)
    ax.set_ylim(0, 52)
    ax.set_ylabel("总耗时（分钟）/ minutes")
    ax.set_title("难度换来的时间成本")

    fig.suptitle("60 例双层记忆评测的难度梯度 / Difficulty gradient across 60 memory cases",
                 fontsize=12, fontweight="bold", y=1.03)
    fig.text(0.01, -0.06,
             "来源：docs/data/ch3-memory-60cases.csv。L1 两组为同一层的基线（无检索）与真检索对照；"
             "L3 有 4 例未评分，按有效样本为 9/16（56.3%）。",
             fontsize=8, color=GRAY)
    save(fig, "ch3-difficulty-gradient.png")


# ---------------------------------------------------------------- 第 4 章

def chart_ch4_tool_inventory():
    rows = read_csv("ch4-tool-inventory.csv")
    servers = [r for r in rows if r["server"] != "total"]
    names = [r["server"] for r in servers]
    discovered = [int(r["tools"]) for r in servers]

    # README 旧口径 18 + 6 + 18 = 42
    documented = [18, 6, 18]

    fig, ax = plt.subplots(figsize=(9.5, 4))
    y = [1, 0]
    left_d = 0
    left_n = 0
    colors = [AMBER, TEAL, BLUE]
    for i, name in enumerate(names):
        ax.barh(y[0], documented[i], left=left_d, color=colors[i], height=0.5,
                edgecolor="white")
        ax.text(left_d + documented[i] / 2, y[0], str(documented[i]),
                ha="center", va="center", color="white", fontsize=10)
        left_d += documented[i]

        ax.barh(y[1], discovered[i], left=left_n, color=colors[i], height=0.5,
                edgecolor="white")
        ax.text(left_n + discovered[i] / 2, y[1], str(discovered[i]),
                ha="center", va="center", color="white", fontsize=10)
        left_n += discovered[i]

    ax.text(left_d + 1.5, y[0], "总计 {} = 18 + 6 + 18".format(left_d),
            va="center", fontsize=10, color=INK)
    ax.text(left_n + 1.5, y[1], "总计 {} = 37 + 6 + 50".format(left_n),
            va="center", fontsize=11, color=INK, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(["README 文档口径\n(documented)", "MCP 实测发现\n(discovered)"])
    ax.set_xlim(0, 150)
    ax.set_xlabel("工具数量 / number of tools")
    ax.set_title("同一套服务，文档写 42，实测发现 93")
    ax.legend(handles=[Patch(color=colors[i], label=names[i]) for i in range(len(names))],
              frameon=False, fontsize=9, loc="upper right")

    fig.text(0.01, -0.02,
             "来源：docs/data/ch4-tool-inventory.csv。工具数由 Agent 启动时 list_tools() 的实际返回统计；"
             "差距来自协作服务器 18→37、感知服务器 18→50。",
             fontsize=8, color=GRAY)
    save(fig, "ch4-tool-inventory.png")


# ---------------------------------------------------------------- 第 5 章

def chart_ch5_pytest():
    rows = {r["metric"]: int(r["count"]) for r in read_csv("ch5-pytest.csv")}
    fail_rows = read_csv("ch5-pytest-failures.csv")

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [1, 1.3]}
    )

    passed, failed = rows["passed"], rows["failed"]
    total = rows["collected"]
    ax1.barh([0], [passed], color=TEAL, height=0.45, label="通过")
    ax1.barh([0], [failed], left=[passed], color=RED, height=0.45, label="失败")
    ax1.text(passed / 2, 0, str(passed), ha="center", va="center", color="white", fontsize=12)
    ax1.text(passed + failed / 2, 0, str(failed), ha="center", va="center",
             color="white", fontsize=10)
    ax1.text(total + 9, 0, "{}/{} = {:.1f}%".format(passed, total, passed / total * 100),
             va="center", fontsize=10, color=INK)
    ax1.set_yticks([])
    ax1.set_ylim(-1, 1)
    ax1.set_xlim(0, 165)
    ax1.set_xlabel("pytest 用例数 / test cases")
    ax1.set_title("123 个用例，117 通过")
    ax1.legend(frameon=False, fontsize=9, loc="lower center",
               bbox_to_anchor=(0.5, -0.34), ncol=2)

    # 右：6 个失败用例的归因分布
    groups = {
        "后台输出时序": 2,
        "错误消息措辞": 1,
        "超时输出捕获": 1,
        "Grep 无效正则": 1,
        "集成元数据": 1,
        "二进制检测": 1,
    }
    names = list(groups.keys())[::-1]
    counts = list(groups.values())[::-1]
    ax2.barh(names, counts, color=GRAY, height=0.55)
    for bar, c in zip(ax2.patches, counts):
        ax2.text(c + 0.05, bar.get_y() + bar.get_height() / 2, str(c),
                 va="center", fontsize=10, color=INK)
    ax2.set_xlim(0, 2.6)
    ax2.set_xlabel("用例数 / cases")
    ax2.set_title("6 个失败均为边缘断言与时序问题")

    fig.text(0.01, -0.02,
             "说明：失败项未涉及 Write/Edit/Read/Bash 同步执行/Grep 常规路径等核心工具链。",
             fontsize=8, color=GRAY)
    save(fig, "ch5-pytest.png")


# ---------------------------------------------------------------- 第 6 章

def chart_ch6_androidworld():
    rows = {r["outcome"]: r for r in read_csv("ch6-androidworld-outcomes.csv")}
    fail_rows = read_csv("ch6-androidworld-failures.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    # 左：116 个任务的构成
    success = int(rows["success"]["count"])
    failure = int(rows["failure"]["count"])
    missing = int(rows["not_completed_nan"]["count"])
    ax1.barh([0], [success], color=TEAL, height=0.45, label="成功")
    ax1.barh([0], [failure], left=[success], color=RED, height=0.45, label="失败")
    ax1.barh([0], [missing], left=[success + failure], color=GRAY, height=0.45,
             label="无结果(NaN)")
    ax1.text(success / 2, 0, str(success), ha="center", va="center",
             color="white", fontsize=12)
    ax1.text(success + failure / 2, 0, str(failure), ha="center", va="center",
             color="white", fontsize=12)
    ax1.text(success + failure + missing / 2, 0, str(missing), ha="center",
             va="center", color="white", fontsize=9)
    ax1.set_yticks([])
    ax1.set_xlim(0, 130)
    ax1.set_xlabel("116 个任务 / tasks")
    ax1.set_title("116 个任务：41 成功 / 61 失败 / 14 无结果")
    ax1.legend(frameon=False, fontsize=9, loc="lower center",
               bbox_to_anchor=(0.5, -0.34), ncol=3)

    # 右：文档口径与实测口径对比
    labels = ["文档声称\nreported", "实测(全量 116)", "实测(正常终止 102)"]
    values = [88.0, 35.3, 40.2]
    colors = [RED, BLUE, TEAL]
    bars = ax2.bar(labels, values, color=colors, width=0.5)
    annotate_bars(ax2, bars, "{:.1f}%", offset=2, horizontal=False)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("成功率（%）/ success rate")
    ax2.set_title("88% 是终止率，不是成功率")
    ax2.text(0.5, 92, "高估 53 个百分点", ha="center", fontsize=9, color=RED)

    fig.text(0.01, -0.02,
             "失败日志 52 次 = 28 次步数耗尽 + 21 次数据库校验不通过 + 3 次声明不可行；"
             "全量日志记录 33 次步数耗尽。",
             fontsize=8, color=GRAY)
    save(fig, "ch6-androidworld.png")


def chart_ch6_elo():
    rows = read_csv("ch6-elo.csv")
    labels = ["Top-1  GPT-4o", "Top-10  Qwen2.5-7B"]
    ratings = [float(r["bt_rating"]) for r in rows]
    lows = [r["ci_low"] for r in rows]
    highs = [r["ci_high"] for r in rows]

    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    bars = ax.bar(labels, ratings, color=[BLUE, GRAY], width=0.45)
    for i, r in enumerate(rows):
        if lows[i] and highs[i]:
            low, high = float(lows[i]), float(highs[i])
            ax.errorbar(i, ratings[i], yerr=[[ratings[i] - low], [high - ratings[i]]],
                        fmt="none", ecolor=INK, capsize=8, linewidth=1.2)
            ax.text(i, high + 14, "{:.1f}".format(ratings[i]),
                    ha="center", va="bottom", fontsize=10, color=INK)
            ax.text(i + 0.3, ratings[i],
                    "95% CI [{:.1f}, {:.1f}]".format(low, high),
                    va="center", fontsize=9, color=INK)
        else:
            ax.text(i, ratings[i] + 14, "{:.1f}".format(ratings[i]),
                    ha="center", va="bottom", fontsize=10, color=INK)
            ax.text(i + 0.3, ratings[i], "无置信区间记录", va="center",
                    fontsize=9, color=GRAY)
    ax.set_ylim(650, 1400)
    ax.set_ylabel("Bradley-Terry rating")
    ax.set_title("5000 条合成对战：两法排名相关 0.9971")

    fig.text(0.01, -0.02,
             "10/10 模型排序与预设一致；BT 与 Online Elo（K=4）方法对比。"
             "数据为按预设 rating 采样的合成对战，seed=7，平局率设定 5%。",
             fontsize=8, color=GRAY)
    save(fig, "ch6-elo.png")


if __name__ == "__main__":
    chart_ch1_context()
    chart_ch1_llm_vs_rl()
    chart_ch2_kv_cache()
    chart_ch2_compression()
    chart_ch3_difficulty()
    chart_ch4_tool_inventory()
    chart_ch5_pytest()
    chart_ch6_androidworld()
    chart_ch6_elo()
