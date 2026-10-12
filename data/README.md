# Data | 数据说明

本目录是论文 *Steady-State Lock and Emergent Order in Finite-Resource Competition* 的**策展数据**：图 3–10 背后的权威运行记录，从项目历史批次的完整数据中挑出，一图一源。生成脚本见 `../experiments/`，运行结果写入 `../outputs/`（不随仓库分发），故本目录是论文数字的唯一权威版本。

This directory holds the **curated data** behind the paper: the authoritative runs for Figures 3–10, one source per figure, selected from the project's historical batches. Experiment scripts live in `../experiments/` and write new runs to `../outputs/` (not distributed), so this directory is the single authoritative record of the paper's numbers.

## 图 → 文件 对照 | Figure → file map

| 图 | 文件 | 关键数值 |
|:---|:---|:---|
| **Fig 3** 规模-存活率标度律 | `scale/scale_10_*`, `scale_30_*`, `scale_50_proportional_20260521_160354`, `resource_R2R5_*`（n=100 R3）, `scale_200_proportional_*`, `1000_proportional_R2R3_*`（n=1000 R3） | n=50: 25.2%；n=100: 27.0%（峰值）；n=1000: 15.8% |
| **Fig 4** 初始配比-终态映射 | `proportion_P1/P1_batch1..3_*`（11 条件 × 5 runs） | 40–70% 鹰派平台区 |
| **Fig 5** 资源水平-存活率响应 | `scale/resource_R2R5_*`（n=100）, `scale/1000_proportional_R2R3_*`（n=1000 R2/R3）, `resource_branch/branch_resource_scale_*`（n=1000 R4/R5） | R3→R4 的 resource paradox（0.5pp，未达显著） |
| **Fig 6** 鸽派纯度效应 | `purity/F4_r3_rerun`（80D/10H/10N）, `purity/C1_resource_cross_*`（C1-R3 条目）, 基线取 Fig 3 的 n=1000 R3 | 15.8% / 47.4±0.6% / 60.3% |
| **Fig 7** 干预策略效果对比 | `intervention/intervention_R3-100_*`, `intervention_R3-1000_*` | 7 种干预，最佳增益 +1.9pp（I7 vs D1） |
| **Fig 8** 饿急攻击概率扫描 | `sensitivity/scan_desperate_attack_*` | 鲁棒参数区 0.3–0.7 |
| **Fig 9** 消融实验对比 | `ablation/ablation_clean_*`, `ablation_conversion_*` | ABL-0: 17.7%；FULL: 18.1% |
| **Fig 10** 派系灭绝顺序热图 | `scale/scale_1000_detailed_20260413_154204` | 中立→鹰派→鸽派 |

## 机制与配置 | Mechanism and configuration

- 机制版本：v0.8-Scheme E（`src/fsm.py` 的 `DEFAULT_MECHANISM_PARAMS`）
- 基准配置：R3-1000（n=1000, regen=1200, pool=3000, 初始 30D/30H/40N）
- 每条件 5 次独立重复；规则侧为确定性过程（种子固定），重跑可复现
- Fig 6 的三档纯度：混合基线 15.8%、高纯度 F4 47.4%、纯鸽 C1 60.3%

## 关于版本选择 | On version selection

同一实验在项目历史上跑过多个批次（如 C1 早期 ER 基线为 regen=1000 的 50.3%，Fig 6 现采用 regen=1200 的 R3 值 60.3%）。本目录只保留与论文数字一致的权威批次，避免多版本混用——这一纪律来自项目 2026-05 的数据审计教训。

## 许可 | License

数据与代码同为 MIT 协议。实验数据由 `experiments/` 中的脚本生成，可用 `../outputs/` 复现。
