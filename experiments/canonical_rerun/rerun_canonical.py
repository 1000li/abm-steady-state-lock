#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rerun_canonical.py
==================
重跑"稳态锁定"ABM 的五个模型 (M1-M5)，全部使用**统一的正典初始条件**，
产出一张"新数 vs 论文旧数"对照表。

正典初始 (canonical initial)，所有模型/所有条件一致：
  - n 个 agent：30% 鸽(DOVE) / 30% 鹰(HAWK) / 40% 中立(NEUTRAL)
    (M2 例外：按 hawk_ratio 扫描，鸽/中立各填 (1-hawk_ratio)/2)
  - 每个 agent：health=100, resources=5
  - stance_score：鸽=-5, 鹰=+5, 中立=0      (无随机抖动)
  - 信任：同阵营=2, 异阵营=0                  (沿用 models.create_initial_state 约定)
  - GameState(resource_pool=3n, resource_regen=int(1.2n), consumption_rate=2)
  - mechanism_params = None  (即 resolve_turn 默认 = v0.8-Scheme E)
  - 跑 100 轮；每个条件 5 个种子 [42, 7, 123, 2024, 99]
  - 随机种子在每次 trial(一整个 100 轮的运行)开始前 random.seed(seed)

模型代码只读导入：
  archive/steady-state-lock/src/{models.py, fsm.py}

运行：
  python3 rerun_canonical.py            # 全跑 (~35-40 min)
  python3 rerun_canonical.py M4 M1      # 只跑指定模型
"""
import sys, os, json, time, random, statistics
from datetime import datetime

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "src")
SRC = os.path.normpath(SRC)
sys.path.insert(0, SRC)

from fsm import resolve_turn          # noqa: E402
from models import GameState, Agent, Stance  # noqa: E402

# ----------------------------------------------------------------------------
# 配置
# ----------------------------------------------------------------------------
MAX_ROUNDS = 100
SEEDS = [42, 7, 123, 2024, 99]
CONSUMPTION = 2

def make_state(n, dove_f=0.3, hawk_f=0.3):
    """正典初始状态生成器 (复用)."""
    nd = int(round(n * dove_f))
    nh = int(round(n * hawk_f))
    nn = n - nd - nh
    st = GameState(resource_pool=3 * n,
                   resource_regen=int(1.2 * n),
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


def run_once(state, n, seeds=SEEDS, intervention=None, record_factions=False):
    """对给定 state_factory 跑 5 个种子，返回聚合统计。
    state 参数是一个 callable(seed)->GameState，保证每个 trial 独立重建。
    """
    survivals, dove_shares, extinction, timeline = [], [], [], None
    fac_order = {"dove": [], "hawk": [], "neutral": []}
    for seed in seeds:
        random.seed(seed)
        st = state()                       # 每次 trial 重建干净状态
        inter = intervention(st) if intervention else None
        first_hit = {"dove": None, "hawk": None, "neutral": None}
        thr = max(1, int(0.01 * n))
        tl = []
        for r in range(1, MAX_ROUNDS + 1):
            if inter is not None:
                inter.before_round(st, r)
            st, _ = resolve_turn(st, [])
            fac = st.get_factions()
            tl.append((r, len(st.get_alive_agents()),
                       len(fac["dove"]), len(fac["hawk"]), len(fac["neutral"])))
            for k in first_hit:
                if first_hit[k] is None and len(fac[k]) <= thr:
                    first_hit[k] = r
            if len(st.get_alive_agents()) == 0:
                break
        alive = len(st.get_alive_agents())
        fac = st.get_factions()
        survivals.append(alive / n)
        dove_shares.append(len(fac["dove"]) / alive if alive else 0.0)
        for k in first_hit:
            fac_order[k].append(first_hit[k])
        if record_factions:
            extinction.append(first_hit)
            if timeline is None:
                timeline = tl
    return {
        "survival_mean": statistics.mean(survivals),
        "survival_std": statistics.pstdev(survivals) if len(survivals) > 1 else 0.0,
        "survival_runs": survivals,
        "dove_share_mean": statistics.mean(dove_shares),
        "dove_share_std": statistics.pstdev(dove_shares) if len(dove_shares) > 1 else 0.0,
        "faction_first_hit": {k: fac_order[k] for k in fac_order},
        "extinction_detail": extinction,
    }


def med(xs):
    xs2 = [x for x in xs if x is not None]
    return statistics.median(xs2) if xs2 else None


# ----------------------------------------------------------------------------
# M1 规模律
# ----------------------------------------------------------------------------
def model_m1():
    print("\n" + "=" * 74)
    print("M1 规模律：n ∈ {50,100,200,1000}，终态存活率")
    print("=" * 74)
    out = {}
    for n in (50, 100, 200, 1000):
        t0 = time.time()
        r = run_once(lambda n=n: make_state(n), n)
        out[str(n)] = r
        print(f"  n={n:<5} 存活率 {r['survival_mean']*100:6.2f}% ± {r['survival_std']*100:.2f}%"
              f"   [{time.time()-t0:.0f}s]")
    return out


# ----------------------------------------------------------------------------
# M2 初始配比
# ----------------------------------------------------------------------------
def model_m2():
    print("\n" + "=" * 74)
    print("M2 初始配比：n=1000，hawk_ratio 0.0→1.0 (步长0.1)，鸽/中立各填一半")
    print("=" * 74)
    out = {}
    n = 1000
    for i in range(11):
        hr = round(i * 0.1, 1)
        df = (1.0 - hr) / 2.0
        t0 = time.time()
        r = run_once(lambda n=n, df=df, hr=hr: make_state(n, dove_f=df, hawk_f=hr), n)
        out[f"{hr:.1f}"] = {"hawk_ratio": hr, "dove_f": df, **r}
        print(f"  鹰占比{hr:.1f} (鸽{df:.2f}/中{df:.2f})  "
              f"存活率 {r['survival_mean']*100:6.2f}% ± {r['survival_std']*100:.2f}%   "
              f"存活者中鸽占比 {r['dove_share_mean']*100:5.1f}% ± {r['dove_share_std']*100:.1f}%"
              f"   [{time.time()-t0:.0f}s]")
    return out


# ----------------------------------------------------------------------------
# M3 灭绝顺序
# ----------------------------------------------------------------------------
def model_m3():
    print("\n" + "=" * 74)
    print("M3 灭绝顺序：n=1000，记录中立/鹰/鸽数量降到 ≤1% (=≤10) 的轮次")
    print("=" * 74)
    n = 1000
    r = run_once(lambda n=n: make_state(n), n, record_factions=True)
    order = sorted(["dove", "hawk", "neutral"],
                   key=lambda k: (med(r["faction_first_hit"][k]) is None,
                                  med(r["faction_first_hit"][k]) or 999))
    for k in ("neutral", "hawk", "dove"):
        hits = r["faction_first_hit"][k]
        hs = ", ".join("—" if h is None else str(h) for h in hits)
        m = med(hits)
        print(f"  {k:<8} 首次≤1%轮次: {hs}   中位={m if m is not None else 'never'}")
    print(f"  → 实际顺序 (按中位): {'→'.join(order)}")
    r["order_by_median"] = order
    return r


# ----------------------------------------------------------------------------
# M4 资源响应
# ----------------------------------------------------------------------------
def model_m4():
    print("\n" + "=" * 74)
    print("M4 资源响应：n=100，regen ∈ {0.6n,1.2n,2.0n,2.4n} = {60,120,200,240}")
    print("=" * 74)
    out = {}
    n = 100
    labels = ["R2(0.6n)", "R3(1.2n)", "R4(2.0n)", "R5(2.4n)"]
    for lab, regen in zip(labels, (60, 120, 200, 240)):
        def mk(n=n, regen=regen):
            st = make_state(n)
            st.resource_regen = regen        # 覆盖正典 regen
            return st
        r = run_once(mk, n)
        out[lab] = {"regen": regen, **r}
        print(f"  {lab:<9} regen={regen:<4} 存活率 {r['survival_mean']*100:6.2f}% ± {r['survival_std']*100:.2f}%")
    return out


# ----------------------------------------------------------------------------
# M5 干预
# ----------------------------------------------------------------------------
class Intervention:
    """在每回合开始前对 state 施加一次干预。"""
    def __init__(self, kind, n):
        self.kind = kind
        self.n = n
        self.done = False
        self.isolated = []

    def before_round(self, st, r):
        k = self.kind
        if k == "I1_random_cull" and r == 1 and not self.done:
            alive = st.get_alive_agents()
            k_num = max(1, int(0.05 * len(alive)))
            for a in random.sample(alive, k_num):
                a.health = 0
            self.done = True
        elif k == "I2_hawk_remove" and r == 1 and not self.done:
            hawks = sorted([a for a in st.get_alive_agents() if a.stance == Stance.HAWK],
                           key=lambda a: a.stance_score, reverse=True)
            for a in hawks[:max(1, int(0.05 * len(hawks)))]:
                a.health = 0
            self.done = True
        elif k == "I3_inject_start" and r == 1:
            st.resource_pool += 2 * self.n
        elif k == "I4_inject_mid" and r == 50:
            st.resource_pool += 2 * self.n
        elif k == "I5_grant_all" and r == 1 and not self.done:
            for a in st.get_alive_agents():
                a.resources += 2
            self.done = True
        elif k == "I6_isolate_hawks":
            if r == 1:
                hawks = sorted([a for a in st.get_alive_agents() if a.stance == Stance.HAWK],
                               key=lambda a: a.stance_score, reverse=True)
                self.isolated = hawks[:max(1, int(0.05 * len(hawks)))]
                for a in self.isolated:
                    a.add_status("隔离")
            elif r == 20:
                for a in self.isolated:
                    a.remove_status("隔离")
        elif k == "I7_execute_top_hawks" and r == 1 and not self.done:
            hawks = sorted([a for a in st.get_alive_agents() if a.stance == Stance.HAWK],
                           key=lambda a: a.stance_score, reverse=True)
            for a in hawks[:max(1, int(0.01 * len(hawks)))]:
                a.health = 0
            self.done = True


def model_m5():
    print("\n" + "=" * 74)
    print("M5 干预：n=1000，baseline + 7 类干预各一次，比较存活率增益")
    print("=" * 74)
    n = 1000
    base = run_once(lambda n=n: make_state(n), n)
    b = base["survival_mean"]
    print(f"  baseline (无干预)        存活率 {b*100:6.2f}% ± {base['survival_std']*100:.2f}%")
    out = {"baseline": {"gain_pp": 0.0, **base}}
    kinds = ["I1_random_cull", "I2_hawk_remove", "I3_inject_start", "I4_inject_mid",
             "I5_grant_all", "I6_isolate_hawks", "I7_execute_top_hawks"]
    desc = {
        "I1_random_cull": "随机剔除5%个体 (R1)",
        "I2_hawk_remove": "定向移除 stance_score 前5%鹰派 (R1)",
        "I3_inject_start": "开局资源注入 +2n (R1)",
        "I4_inject_mid": "中期资源注入 +2n (R50)",
        "I5_grant_all": "全民发放 +2 资源 (R1)",
        "I6_isolate_hawks": "隔离前5%高威胁鹰派 20轮 (R1-R19)",
        "I7_execute_top_hawks": "处决前1%顶级鹰派 (R1)",
    }
    for k in kinds:
        r = run_once(lambda n=n: make_state(n), n, intervention=lambda st, k=k: Intervention(k, n))
        gain = (r["survival_mean"] - b) * 100
        out[k] = {"desc": desc[k], "gain_pp": gain, **r}
        print(f"  {k:<22} {desc[k]:<34} {r['survival_mean']*100:6.2f}%  "
              f"增益 {gain:+5.2f}pp")
    best = max((v for k, v in out.items() if k != "baseline"), key=lambda v: v["gain_pp"])
    print(f"  → 最佳干预增益: {best['gain_pp']:+.2f}pp")
    out["best_gain_pp"] = best["gain_pp"]
    return out


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    which = sys.argv[1:] or ["M1", "M2", "M3", "M4", "M5"]
    which = [w.upper() for w in which]
    t0 = time.time()
    results = {"meta": {
        "script": "rerun_canonical.py",
        "ran_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model_src": SRC,
        "canonical_init": "30% dove / 30% hawk / 40% neutral; health=100; resources=5; "
                          "score -5/+5/0; pool=3n; regen=int(1.2n); cons=2; mech=默认(v0.8-Scheme E)",
        "rounds": MAX_ROUNDS, "seeds": SEEDS,
    }}
    fns = {"M1": model_m1, "M2": model_m2, "M3": model_m3, "M4": model_m4, "M5": model_m5}
    for w in which:
        if w in fns:
            results[w] = fns[w]()
    results["meta"]["elapsed_sec"] = round(time.time() - t0, 1)

    outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "canonical_rerun_results.json")
    with open(outp, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n已保存: {outp}")
    print(f"总耗时: {results['meta']['elapsed_sec']}s")


if __name__ == "__main__":
    main()
