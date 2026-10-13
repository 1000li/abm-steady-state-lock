# 正典重跑批次 | Canonical rerun batches (2026-10-13)

本目录是 2026-10-13 论文勘误的**权威数据源**：在统一"正典初始"下重跑 Model 1–5 及全部对齐批次的逐 trial 记录。论文 Fig 3–7 的数字以本目录为准（见 `../README.md` 对照表）。

This directory holds the authoritative records of the 2026-10-13 paper revision: all experiments rerun under the unified canonical initialisation. Figures 3–7 of the paper are sourced from these files.

## 正典初始规格 | Canonical initialisation

所有批次统一（与论文 Methods 的 "Canonical initialisation" 段一致）：

| 项 | 取值 |
|:---|:---|
| 初始配比 | 30% 鸽 / 30% 鹰 / 40% 中立（批次指定的变体除外） |
| 个体属性 | health=100, resources=5 |
| stance_score | 鸽 −5 / 鹰 +5 / 中立 0（无随机抖动） |
| 信任矩阵 | 同阵营 2，异阵营 0 |
| 资源 | pool = 3n，regen = int(1.2n)（各批次另有指定处从指定），consumption = 2 |
| 机制 | v0.8-Scheme E 默认参数（`src/fsm.py`） |
| 轮数 | 100 |
| 种子 | [42, 7, 123, 2024, 99]，每个 trial 开始前 `random.seed(seed)` 一次 |
| 存活率 | 第 100 轮末存活数 / n |

## 文件 | Files

| 文件 | 批次 | 论文对应 | 关键新数 |
|:---|:---|:---|:---|
| `canonical_rerun_results.json` | M1 规模律（4 规模）、M2 三分配比扫描、M3 灭绝顺序、M4 资源响应 @n=100、M5 强干预 | Fig 3 主数据；§3.2.1 三分扫描；§3.4；M5 附录口径 | M1: 19.6/21.8/22.3/21.6%；M3: 中立 19 轮→鹰 69 轮→鸽未灭绝 |
| `gapfill_results.json` | M4 @n=1000、M2 纯鸽鹰二元扫描、M5 论文 Table 2 弱扰动干预、C1 纯鸽 R3/R4/R5 | Fig 4、Fig 5、Fig 7、Fig 6 的 C1 与基线 | M4: 10.76/21.64/21.08/20.80%；M2 二元: hr=0.5 局部极大 44.34%；M5: 除 D1（−0.94pp）全部 ±0.15pp 内；C1: 60.42/100/100% |
| `f4_rerun_results.json` | F4 高纯度（80D/10H/10N）@ R3 | Fig 6 蓝柱 | 46.3% ± 0.59 |

## 复跑 | Reproduction

```bash
cd experiments/canonical_rerun
python3 rerun_canonical.py    # M1–M5 主批次（约 38 分钟）
python3 gapfill_runs.py       # 四个对齐批次（约 62 分钟）
python3 f4_rerun.py           # F4（约 4 分钟）
```

脚本从仓库 `src/` 导入模型（只读），输出写入当前目录；`f4_rerun.py` 依赖同目录的 `gapfill_runs.py`。

## 与历史批次的关系 | Relation to historical batches

历史批次（`../scale/`、`../proportion_P1/`、`../resource_branch/`、`../purity/`、`../intervention/`、`../sensitivity/`、`../ablation/`）对应论文 v1（2026-08 投稿版）数字，因初始条件规格不完整且 Fig 3 混用了三套不同初始，已被本目录取代。其中 Fig 8（参数扫描）、Fig 9（消融）、Fig 10（灭绝热图明细轨迹）的对应实验**未纳入**正典重跑计划，仍以历史批次为源，论文相应文字未改动。
