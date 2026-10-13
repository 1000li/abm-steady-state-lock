# Data | 数据说明

本目录是论文 *Steady-State Lock and Emergent Order in Finite-Resource Competition* 的**策展数据**。

**2026-10-13 勘误**：论文 Fig 3–7 的数字以 `canonical_20261013/`（正典重跑批次）为唯一权威；历史批次子目录（`scale/`、`proportion_P1/` 等）对应论文 v1（2026-08 投稿版）数字，保留供溯源，不再对应正文数字。Fig 8–10 的对应实验未纳入正典重跑，仍以历史批次为源。

This directory holds the curated data behind the paper. **Revision 2026-10-13**: Figures 3–7 are authoritatively sourced from `canonical_20261013/` (canonical rerun batches); historical subdirectories correspond to paper v1 (2026-08 submission) and are kept for provenance. Figures 8–10 remain sourced from historical batches.

## 图 → 文件 对照 | Figure → file map（2026-10-13 勘误后）

| 图 | 权威源 | 关键数值 |
|:---|:---|:---|
| **Fig 3** 规模-存活率标度律 | `canonical_20261013/canonical_rerun_results.json`（M1） | n=50: 19.6%；n=100: 21.8%；n=200: 22.3%；n=1000: 21.6%（n≥100 饱和平台 ~22%，无规模惩罚） |
| **Fig 4** 初始配比-终态映射 | `canonical_20261013/gapfill_results.json`（M2 纯鸽鹰二元，11 条件 × 5 runs） | 非单调：hr=0.5 局部极大 44.3%，两侧递减，hr=1.0 崩溃至 0.24%；hr=0.7 处 5 种子双峰（双稳态） |
| **Fig 5** 资源水平-存活率响应 | `canonical_20261013/gapfill_results.json`（M4 @n=1000） | R2/R3/R4/R5 = 10.8/21.6/21.1/20.8%；regen 翻倍存活纹丝不动（resource paradox，总降幅 0.84pp） |
| **Fig 6** 鸽派纯度效应 | 基线 = `canonical_rerun_results.json`（21.64%）；F4 = `canonical_20261013/f4_rerun_results.json`（46.3%）；C1 = `gapfill_results.json`（60.42%） | 21.6% / 46.3% / 60.4%，纯度溢价 38.8pp |
| **Fig 7** 干预策略效果对比 | `canonical_20261013/gapfill_results.json`（M5，论文 Table 2 弱扰动定义 @n=1000） | 除 D1 随机剔除（−0.94pp）外全部在 ±0.15pp 噪声内；注入类在 pool 饱和时为严格 no-op |
| **Fig 8** 饿急攻击概率扫描 | `sensitivity/scan_desperate_attack_*`（历史批次，未重跑） | 鲁棒参数区 0.3–0.7 |
| **Fig 9** 消融实验对比 | `ablation/ablation_clean_*`, `ablation_conversion_*`（历史批次，未重跑） | ABL-0: 17.7%；FULL: 18.1% |
| **Fig 10** 派系灭绝顺序热图 | `scale/scale_1000_detailed_20260413_154204`（历史批次，未重跑） | 中立→鹰派→鸽派（正典 M3 复现：中立中位 19 轮→鹰 69 轮→鸽未灭绝） |

## 机制与配置 | Mechanism and configuration

- 机制版本：v0.8-Scheme E（`src/fsm.py` 的 `DEFAULT_MECHANISM_PARAMS`）
- 基准配置：R3-1000（n=1000, regen=1200, pool=3n=3000, 初始 30D/30H/40N）
- 正典初始完整规格（信任矩阵、种子协议等）见 `canonical_20261013/README.md`
- 每条件 5 次独立重复；规则侧为确定性过程（种子固定），重跑可复现

## 历史批次说明 | Historical batches (v1)

`scale/`、`proportion_P1/`、`resource_branch/`、`purity/`、`intervention/` 子目录是论文 v1 数字（基准 15.8%、n=100 尖峰 27.0%、40–70% 平台区等）的出处。2026-10 审计发现 Fig 3 混用了三套不同随机初始，故以统一正典初始重跑并全面替换；v1 数字与正典数字的差异归因于初始条件规格，机制结论（稳态锁定、鸽派主导、灭绝顺序、不可干预）在两个版本下均成立。

## 版本选择纪律 | Version selection

本目录不同时期只保留一个权威口径：2026-08 前以历史批次为准，2026-10-13 后以 `canonical_20261013/` 为准。多版本并存仅限正典目录内的逐 trial 明细与历史批次的溯源关系，避免混用。

## 许可 | License

数据与代码同为 MIT 协议。实验数据可由 `experiments/canonical_rerun/` 中的脚本复现（正典批次）或 `../outputs/` 复现（历史批次，不随仓库分发）。
