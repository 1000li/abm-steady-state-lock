#!/usr/bin/env python3
"""F4 批次：Fig 6 蓝柱对齐跑。80D/10H/10N, n=1000, regen=1200, 5 种子。"""
import sys, os, json, statistics

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from gapfill_runs import make_state, run_trials, SEEDS  # 复用正典生成器与批量运行

def main():
    agg = run_trials(
        "F4_high_purity_n1000", "F4_80D_10H_10N_R3", 1000,
        lambda: make_state(1000, dove_f=0.8, hawk_f=0.1, regen=1200),
    )
    trials = agg["trials"]
    rates = [t["survival_rate"] for t in trials]
    out = {
        "batch": "F4_high_purity_n1000",
        "config": "80D/10H/10N, n=1000, regen=1200, pool=3000, 100 rounds",
        "seeds": SEEDS,
        "trials": trials,
        "mean_pct": round(agg["survival_mean"] * 100, 2),
        "pstdev_pct": round(agg["survival_std"] * 100, 2),
    }
    with open(os.path.join(BASE, "f4_rerun_results.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"F4 mean={out['mean_pct']}% ± {out['pstdev_pct']}%  (旧数 47.4%)")

if __name__ == "__main__":
    main()
