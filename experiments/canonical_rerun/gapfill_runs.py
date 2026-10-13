#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gapfill_runs.py
===============
"稳态锁定"ABM 正典初始重跑的四个补充批次（对齐论文口径）：

  1. M4_resource_n1000      论文 §3.3.1 资源悖论表  n=1000, 30/30/40, regen ∈ {600,1200,2000,2400}
  2. M2_binary_scan_n1000   论文 §3.2.1 P1/Table 2   n=1000, 纯鸽鹰二元, hawk_ratio ∈ {0.0..1.0}
  3. M5_paper_interventions_n1000  论文 §3.3.3 Table 5  七个"弱扰动"干预 + 同批次 baseline
  4. C1_pure_dove_n1000     论文 §3.3.1 验证表 + §3.3.2 + Fig 6  纯鸽, regen ∈ {1200,2000,2400}

正典初始与 rerun_canonical.py 完全一致；archive/steady-state-lock 只读导入。

干预定义（论文 Table 2"弱扰动"版，round 从 1 计，"every k rounds" = 第 k, 2k, ... 轮开始时执行）：
  D1  每 10 轮随机移除 1 个活体
  I3  每 10 轮移除 resources + 0.2*health 最大的鹰派
  I4  每 20 轮 pool 注入 100
  I4b 每轮开始 pool 注入 5
  I5  每 10 轮 pool 注入 100
  I6  每 10 轮选最弱个体（health 最低，并列取 resources 低者）隔离 10 轮，下次重选替换
      （复用 fsm 内置"隔离"状态：免被攻击 + 自身不行动，与 rerun_canonical.py 的 I6 语义一致）
  I7  I3 与 I5 每 10 轮同时执行

运行：  python3 gapfill_runs.py            # 全跑
        python3 gapfill_runs.py M4 M2      # 只跑指定批次
输出：  gapfill_results.json / gapfill_report.md（同目录）
"""
import sys, os, json, time, random, statistics
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(BASE, "..", "..", "src"))
sys.path.insert(0, SRC)

from fsm import resolve_turn              # noqa: E402
from models import GameState, Agent, Stance  # noqa: E402

MAX_ROUNDS = 100
SEEDS = [42, 7, 123, 2024, 99]
CONSUMPTION = 2


def make_state(n, dove_f=0.3, hawk_f=0.3, regen=None):
    """正典初始状态生成器（与 rerun_canonical.py 一致；regen 可覆盖）。"""
    nd = int(round(n * dove_f))
    nh = int(round(n * hawk_f))
    nn = n - nd - nh
    st = GameState(resource_pool=3 * n,
                   resource_regen=int(1.2 * n) if regen is None else regen,
                   consumption_rate=CONSUMPTION)
    aid = 0
    for _ in range(nd):
        st.agents.append(Agent(id=aid, name=f"A{aid}", stance=Stance.DOVE,
                               stance_score=-5, health=100, resources=5)); aid += 1
    for _ in range(nh):
        st.agents.append(Agent(id=aid, name=f"A{aid}", stance=Stance.HAWK,
                               stance_score=5, health=100, resources=5)); aid += 1
    for _ in range(nn):
        st.agents.append(Agent(id=aid, name=f"A{aid}", stance=Stance.NEUTRAL,
                               stance_score=0, health=100, resources=5)); aid += 1
    smap = {a.id: a.stance for a in st.agents}
    for a in st.agents:
        for b in st.agents:
            if a.id != b.id:
                a.trust_to[b.id] = 2 if smap[a.id] == smap[b.id] else 0
    return st


# ----------------------------------------------------------------------------
# 论文 Table 2 "弱扰动" 干预（与 rerun_canonical.Intervention 分立的实现）
# ----------------------------------------------------------------------------
class PaperIntervention:
    """每回合开始前对 state 施加一次干预；kind ∈ {D1,I3,I4,I4b,I5,I6,I7}。"""

    def __init__(self, kind):
        self.kind = kind
        self.isolated = None          # I6 当前隔离目标

    def _remove_top_hawk(self, st):
        hawks = [a for a in st.get_alive_agents() if a.stance == Stance.HAWK]
        if hawks:
            target = max(hawks, key=lambda a: a.resources + 0.2 * a.health)
            target.health = 0

    def before_round(self, st, r):
        k = self.kind
        if k == "D1":
            if r % 10 == 0:
                alive = st.get_alive_agents()
                if alive:
                    random.choice(alive).health = 0
        elif k == "I3":
            if r % 10 == 0:
                self._remove_top_hawk(st)
        elif k == "I4":
            if r % 20 == 0:
                st.resource_pool += 100
        elif k == "I4b":
            st.resource_pool += 5
        elif k == "I5":
            if r % 10 == 0:
                st.resource_pool += 100
        elif k == "I6":
            if r % 10 == 0:
                if self.isolated is not None:
                    self.isolated.remove_status("隔离")
                    self.isolated = None
                alive = st.get_alive_agents()
                if alive:
                    target = min(alive, key=lambda a: (a.health, a.resources))
                    target.add_status("隔离")
                    self.isolated = target
        elif k == "I7":
            if r % 10 == 0:
                self._remove_top_hawk(st)
                st.resource_pool += 100


# ----------------------------------------------------------------------------
# 运行循环：逐 trial 记录，返回聚合 + 明细
# ----------------------------------------------------------------------------
def run_trials(batch, label, n, state_factory, intervention_kind=None):
    trials = []
    for seed in SEEDS:
        random.seed(seed)
        st = state_factory()
        inter = PaperIntervention(intervention_kind) if intervention_kind else None
        last_round = MAX_ROUNDS
        for r in range(1, MAX_ROUNDS + 1):
            if inter is not None:
                inter.before_round(st, r)
            st, _ = resolve_turn(st, [])
            if len(st.get_alive_agents()) == 0:
                last_round = r
                break
        alive = len(st.get_alive_agents())
        fac = st.get_factions()
        trials.append({
            "batch": batch, "condition": label, "seed": seed,
            "intervention": intervention_kind or "none",
            "alive_end": alive,
            "survival_rate": alive / n,
            "dove_end": len(fac["dove"]), "hawk_end": len(fac["hawk"]),
            "neutral_end": len(fac["neutral"]),
            "dove_share_survivors": (len(fac["dove"]) / alive) if alive else 0.0,
            "last_round": last_round,
        })
    sr = [t["survival_rate"] for t in trials]
    ds = [t["dove_share_survivors"] for t in trials]
    agg = {
        "label": label, "n": n,
        "intervention": intervention_kind or "none",
        "survival_mean": statistics.mean(sr),
        "survival_std": statistics.pstdev(sr) if len(sr) > 1 else 0.0,
        "survival_runs": sr,
        "alive_mean": statistics.mean([t["alive_end"] for t in trials]),
        "dove_share_mean": statistics.mean(ds),
        "dove_share_std": statistics.pstdev(ds) if len(ds) > 1 else 0.0,
        "trials": trials,
    }
    return agg


# ----------------------------------------------------------------------------
# 批次 1：M4_resource_n1000（论文 §3.3.1 资源悖论表）
# ----------------------------------------------------------------------------
def batch_m4():
    print("\n" + "=" * 74)
    print("批次1 M4_resource_n1000：n=1000, 30/30/40, regen ∈ {600,1200,2000,2400}")
    print("=" * 74)
    n = 1000
    out = {}
    for regen in (600, 1200, 2000, 2400):
        t0 = time.time()
        r = run_trials("M4_resource_n1000", f"regen={regen}", n,
                       lambda regen=regen: make_state(n, regen=regen))
        out[f"regen={regen}"] = r
        print(f"  regen={regen:<5} 存活率 {r['survival_mean']*100:6.2f}% ± {r['survival_std']*100:.2f}%"
              f"   [{time.time()-t0:.0f}s]")
    return out


# ----------------------------------------------------------------------------
# 批次 2：M2_binary_scan_n1000（论文 §3.2.1 P1/Table 2，纯鸽鹰二元）
# ----------------------------------------------------------------------------
def batch_m2_binary():
    print("\n" + "=" * 74)
    print("批次2 M2_binary_scan_n1000：n=1000, regen=1200, hawk_ratio 0.0→1.0, 无中立")
    print("=" * 74)
    n = 1000
    out = {}
    for i in range(11):
        hr = round(i * 0.1, 1)
        df = 1.0 - hr
        t0 = time.time()
        r = run_trials("M2_binary_scan_n1000", f"hawk_ratio={hr:.1f}", n,
                       lambda df=df, hr=hr: make_state(n, dove_f=df, hawk_f=hr, regen=1200))
        out[f"hawk_ratio={hr:.1f}"] = r
        print(f"  鹰占比{hr:.1f} 鸽{df:.1f}  存活率 {r['survival_mean']*100:6.2f}% ± "
              f"{r['survival_std']*100:.2f}%  存活者中鸽 {r['dove_share_mean']*100:5.1f}%"
              f"   [{time.time()-t0:.0f}s]")
    return out


# ----------------------------------------------------------------------------
# 批次 3：M5_paper_interventions_n1000（论文 §3.3.3 Table 5，弱扰动版）
# ----------------------------------------------------------------------------
def batch_m5_paper():
    print("\n" + "=" * 74)
    print("批次3 M5_paper_interventions_n1000：n=1000, 30/30/40, regen=1200, Table2 弱扰动")
    print("=" * 74)
    n = 1000
    out = {}
    t0 = time.time()
    base = run_trials("M5_paper_interventions_n1000", "baseline", n,
                      lambda: make_state(n, regen=1200))
    out["baseline"] = base
    print(f"  baseline                 存活率 {base['survival_mean']*100:6.2f}% ± "
          f"{base['survival_std']*100:.2f}%   [{time.time()-t0:.0f}s]")
    b = base["survival_mean"]
    for kind in ("D1", "I3", "I4", "I4b", "I5", "I6", "I7"):
        t0 = time.time()
        r = run_trials("M5_paper_interventions_n1000", kind, n,
                       lambda: make_state(n, regen=1200), intervention_kind=kind)
        r["delta_vs_baseline_pp"] = (r["survival_mean"] - b) * 100
        out[kind] = r
        print(f"  {kind:<4} 存活率 {r['survival_mean']*100:6.2f}% ± {r['survival_std']*100:.2f}%  "
              f"Δ {r['delta_vs_baseline_pp']:+5.2f}pp  存活者中鸽 {r['dove_share_mean']*100:5.1f}%"
              f"   [{time.time()-t0:.0f}s]")
    return out


# ----------------------------------------------------------------------------
# 批次 4：C1_pure_dove_n1000（论文 §3.3.1 验证表 + §3.3.2 + Fig 6）
# ----------------------------------------------------------------------------
def batch_c1():
    print("\n" + "=" * 74)
    print("批次4 C1_pure_dove_n1000：n=1000, 纯鸽, regen ∈ {1200,2000,2400}")
    print("=" * 74)
    n = 1000
    out = {}
    for regen in (1200, 2000, 2400):
        t0 = time.time()
        r = run_trials("C1_pure_dove_n1000", f"regen={regen}", n,
                       lambda regen=regen: make_state(n, dove_f=1.0, hawk_f=0.0, regen=regen))
        out[f"regen={regen}"] = r
        print(f"  regen={regen:<5} 存活率 {r['survival_mean']*100:6.2f}% ± {r['survival_std']*100:.2f}%"
              f"  终端存活均值 {r['alive_mean']:.1f}   [{time.time()-t0:.0f}s]")
    return out


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    which = sys.argv[1:] or ["M4", "M2B", "M5P", "C1"]
    which = [w.upper() for w in which]
    t0 = time.time()
    results = {"meta": {
        "script": "gapfill_runs.py",
        "ran_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_src": SRC,
        "canonical_init": "30/30/40（或批次指定配比）; health=100; resources=5; "
                          "score -5/+5/0; pool=3n; cons=2; mech=默认(v0.8-Scheme E)",
        "rounds": MAX_ROUNDS, "seeds": SEEDS,
        "survival_def": "第100轮末存活数 / n（提前全灭则为0）",
    }}
    fns = {"M4": batch_m4, "M2B": batch_m2_binary,
           "M5P": batch_m5_paper, "C1": batch_c1}
    for w in which:
        if w in fns:
            results[w] = fns[w]()
    results["meta"]["elapsed_sec"] = round(time.time() - t0, 1)

    # 自检：trial 计数
    expect = {"M4": 20, "M2B": 55, "M5P": 40, "C1": 15}   # M5P = 7干预×5 + baseline×5
    counts = {}
    for w, agg in ((k, v) for k, v in results.items() if k in fns):
        counts[w] = sum(len(v["trials"]) for v in agg.values())
    ok = all(counts.get(w) == e for w, e in expect.items())
    print(f"\ntrial 计数: {counts}  期望 {expect}  ->  {'OK' if ok else 'MISMATCH'}")
    results["meta"]["trial_counts"] = counts
    results["meta"]["trial_counts_ok"] = ok

    outp = os.path.join(BASE, "gapfill_results.json")
    with open(outp, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    json.load(open(outp))   # 可解析性自检
    print(f"已保存: {outp}")
    print(f"总耗时: {results['meta']['elapsed_sec']}s")


if __name__ == "__main__":
    main()
