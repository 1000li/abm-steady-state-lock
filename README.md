# Steady-State Lock ABM
# 稳态锁定多主体模型

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Agent-based model for**: *Steady-State Lock and Emergent Order in Finite-Resource Competition* (submitted to JASSS)
> 
> **论文**: 《有限资源竞争中的稳态锁定与涌现秩序》（投稿 JASSS 中）

## Overview | 项目概述

This repository contains the core agent-based model (ABM) and experimental scripts used in our study of steady-state lock in finite-resource competition systems.

本仓库包含我们研究有限资源竞争系统中稳态锁定现象的核心多主体模型（ABM）和实验脚本。

The model features three agent types—**Doves** (cooperators), **Hawks** (predators), and **Neutrals**—interacting in a shared resource pool over discrete rounds.

模型包含三类主体——**鸽派**（合作者）、**鹰派**（掠夺者）和**中立派**——在离散回合中共享资源池进行互动。

### Key Finding: Steady-State Lock | 核心发现：稳态锁定

Under structural resource deficit, the system spontaneously converges to a **single Dove-dominated attractor** (~98% Dove) that is robust against:

在结构性资源赤字条件下，系统自发收敛到**单一鸽派主导吸引子**（~98% 鸽派），且对以下扰动保持稳健：

- External interventions (random culling, targeted removal, resource injection)
- 外部干预（随机剔除、定向移除、资源注入）
- Parameter variations (population size, resource levels)
- 参数变化（种群规模、资源水平）
- Mechanism ablations (removing individual behavioral rules)
- 机制消融（移除单个行为规则）

## Repository Structure | 仓库结构

```
steady-state-lock/
├── src/                          # Core ABM engine | 核心ABM引擎
│   ├── __init__.py
│   ├── models.py                 # Data models | 数据模型
│   └── fsm.py                    # Finite state machine | 有限状态机
│
├── experiments/                  # Paper experiments (10 scripts) | 论文实验（10个脚本）
│   ├── model1_scaling.py         # Fig.3: Size scaling law | 规模标度律
│   ├── model2_proportion.py    # Fig.4: Initial proportion mapping | 初始配比映射
│   ├── model3_extinction.py    # Fig.10: Faction extinction order | 派系灭绝顺序
│   ├── model4_resource.py      # Fig.5: Resource response | 资源响应
│   ├── model5_intervention_random.py    # Fig.7: D1 random culling | D1 随机剔除
│   ├── model5_intervention_targeted.py  # Fig.7: I3 targeted removal | I3 定向移除
│   ├── model5_intervention_injection.py # Fig.7: I4 resource injection | I4 资源注入
│   ├── model5_intervention_combined.py  # Fig.7: I7 combined strategy | I7 组合策略
│   ├── ablation.py             # Fig.9: Ablation study | 消融实验
│   └── parameter_scan.py       # Fig.8: Desperate attack probability scan | 饿急攻击概率扫描
│
├── figures/                        # Figure generation | 图表生成
│   └── generate_figures.py
│
├── data/                          # Output directory | 输出目录
├── README.md                      # This file | 本文件
├── LICENSE                        # MIT License | MIT 协议
└── requirements.txt               # Dependencies | 依赖
```

## Quick Start | 快速开始

### Installation | 安装

```bash
pip install -r requirements.txt
```

### Run a Single Simulation | 运行单次模拟

```python
from src.models import GameState, Lobster, Stance
from src.fsm import resolve_turn

# R3-1000 baseline: 30% Dove / 30% Hawk / 40% Neutral, R=1200
# R3-1000 基准：30% 鸽派 / 30% 鹰派 / 40% 中立，R=1200

state = GameState(resource_pool=3000, resource_regen=1200, consumption_rate=2)
for i in range(1000):
    if i < 300:
        stance, score = Stance.DOVE, -5
    elif i < 600:
        stance, score = Stance.HAWK, 5
    else:
        stance, score = Stance.NEUTRAL, 0
    state.lobsters.append(Lobster(
        id=i, name=f'A{i}', stance=stance, stance_score=score,
        health=100, resources=5
    ))

# Run 100 rounds | 运行100回合
for r in range(100):
    state, events = resolve_turn(state, [])
    
final_alive = state.get_alive_lobsters()
print(f"Survival: {len(final_alive)}/1000 ({len(final_alive)/10:.1f}%)")
# 存活率：{len(final_alive)}/1000 ({len(final_alive)/10:.1f}%)
```

### Run Experiments | 运行实验

```bash
cd experiments
python model1_scaling.py          # Size scaling (n=50 to 1000) | 规模标度律
python model2_proportion.py       # Initial proportion scan | 初始配比扫描
python model5_intervention_random.py  # Intervention strategies | 干预策略
```

## The Five Models | 五个模型

Our paper presents five complementary models as different resolution slices of an emergence path:

论文提出五个互补模型，作为涌现路径的不同分辨率切片：

| Model | Scale | Focus | Key Finding |
|:-----:|:-----:|:------|:------------|
| **M1** | Macro | Size scaling | Three regimes: chaotic→metastable→size penalty |
| **M1** | 宏观 | 规模标度律 | 三阶段：混沌→亚稳态→规模惩罚 |
| **M2** | Meso | Initial proportion | 40-70% Hawk plateau → terminal structure |
| **M2** | 中观 | 初始配比 | 40-70% 鹰派平台区 → 终态结构 |
| **M3** | Micro | Extinction order | Neutral→Hawk→Dove death sequence |
| **M3** | 微观 | 灭绝顺序 | 中立→鹰派→鸽派 死亡序列 |
| **M4** | Env. | Resource response | Pure-Dove carrying capacity formula |
| **M4** | 环境 | 资源响应 | 纯鸽派承载力公式 |
| **M5** | Resilience | Intervention | Unintervenability theorem |
| **M5** | 韧性 | 干预策略 | 不可干预定理 |

## Mechanism Parameters | 机制参数

All behavioral rules are configurable via `mechanism_params` dict passed to `resolve_turn()`:

所有行为规则可通过传递给 `resolve_turn()` 的 `mechanism_params` 字典进行配置：

| Parameter | Default | Description | 说明 |
|:----------|:-------:|:------------|:-----|
| `desperate_attack_prob` | 0.50 | Dove→Hawk when resource=0 | 资源为0时鸽派→鹰派概率 |
| `consecutive_starvation_threshold` | 3 | Rounds of deficit before conversion | 连续赤字回合数阈值 |
| `relative_deprivation_prob` | 0.40 | Dove→Hawk on observing Hawk advantage | 观察到鹰派优势时的转换概率 |
| `attacked_to_hawk_prob` | 0.80 | Any→Hawk when attacked | 被攻击时任意→鹰派概率 |
| `sharing_reinforce_prob` | 0.90 | Dove reinforcement on successful share | 成功分享后鸽派强化概率 |
| `raiding_reinforce_prob` | 0.85 | Hawk reinforcement on successful raid | 成功掠夺后鹰派强化概率 |
| `attack_failure_reflect_prob` | 0.60 | Hawk→Dove on failed attack | 攻击失败后鹰派→鸽派概率 |

## Data Availability | 数据可用性

### Generated Data | 生成数据

All experimental data is generated by running the scripts in `experiments/`. Output files are saved to `data/` in JSON format.

所有实验数据通过运行 `experiments/` 中的脚本生成。输出文件以 JSON 格式保存到 `data/` 目录。

**Data structure per experiment:**

```json
{
  "experiment": "M1_Scaling",
  "n": 1000,
  "mean_survival_rate": 0.158,
  "std": 0.012,
  "runs": [
    {
      "run_id": 0,
      "final_alive": 158,
      "survival_rate": 0.158,
      "dove_count": 153,
      "hawk_count": 4,
      "neutral_count": 1
    }
  ]
}
```

### Raw Paper Data | 论文原始数据

The complete raw data used in the JASSS paper (including all replicate runs, parameter scans, and ablation conditions) is archived at:

JASSS 论文使用的完整原始数据（包括所有重复运行、参数扫描和消融实验条件）存档于：

- **Zenodo DOI**: [pending submission | 待提交]
- **GitHub**: Available upon paper acceptance | 论文接受后公开

### Data License | 数据许可

Generated data follows the same MIT License as the code. You are free to use, modify, and redistribute the data with attribution.

生成数据遵循与代码相同的 MIT 协议。您可以自由使用、修改和再分发数据，只需保留署名。

## Reproducing Paper Results | 复现论文结果

### Expected Runtime | 预期运行时间

| Experiment | Population | Runs | Approx. Time |
|:---|:---:|:---:|:---|
| M1 Scaling | 50–1000 | 5 each | ~5 min |
| M2 Proportion | 1000 | 11 conditions | ~3 min |
| M3 Extinction | 1000 | 5 seeds | ~5 min |
| M4 Resource | 1000 | 4 R levels | ~2 min |
| M5 Intervention | 1000 | 4 strategies | ~3 min |
| Ablation | 1000 | 4 conditions | ~3 min |
| Parameter Scan | 1000 | 11 probabilities | ~4 min |

*On a modern CPU (e.g., Apple M3 / Intel i7). Times are approximate and vary with random seed.*

*在现代 CPU 上（如 Apple M3 / Intel i7）。时间为近似值，随随机种子变化。*

### Modifying Parameters | 修改参数

```python
from src.fsm import resolve_turn

# Run with modified desperate attack probability
# 使用修改后的饿急攻击概率运行
params = {"desperate_attack_prob": 0.30}
state, events = resolve_turn(state, [], mechanism_params=params)
```

See `src/fsm.py` line 15–60 for the full parameter list and defaults.

完整参数列表和默认值见 `src/fsm.py` 第15-60行。

## Citation | 引用

If you use this code, please cite:

如果使用本代码，请引用：

```bibtex
@article{steadystatelock2026,
  title={Steady-State Lock and Emergent Order in Finite-Resource Competition},
  author={[Authors]},
  journal={Journal of Artificial Societies and Social Simulation},
  year={2026}
}
```

## License | 许可

[MIT License](LICENSE)

## Contact | 联系方式

For questions about the model or paper, please open an issue.

如有关于模型或论文的问题，请提交 issue。

---

*Developed by 闲闲Shian and Kimi Claw | 由 闲闲Shian 和 Kimi Claw 开发*
