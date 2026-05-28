#!/usr/bin/env python3
"""
P1 相变探测实验运行器（Layer 3）
机制：v0.8-Scheme E | 改变初始鹰派比例 0%-100%
规模：1000只 | 中立固定100只
目的：探测相变/临界点，绘制存活率 vs 初始鹰派比例曲线
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from fsm import resolve_turn
from models import GameState, Lobster, Stance
import json
from datetime import datetime
import random

# ========== 实验参数 ==========
NUM_RUNS = 5
MAX_ROUNDS = 100
NUM_LOBSTERS = 1000
NUM_NEUTRAL = 100  # 中立固定100只
INITIAL_RESOURCES = 3000
RESOURCE_REGEN = 1000
CONSUMPTION_RATE = 2

# 鹰派比例扫描点
HAWK_RATIOS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def run_single_condition(hawk_ratio: float, run_id: int) -> dict:
    """运行单一条件下的单次实验"""
    random.seed(20000 + int(hawk_ratio * 100) * 10 + run_id)
    
    # 计算数量
    neutral = NUM_NEUTRAL
    remaining = NUM_LOBSTERS - neutral
    hawks = int(remaining * hawk_ratio)
    doves = remaining - hawks
    
    state = GameState()
    state.resource_regen = RESOURCE_REGEN
    state.consumption_rate = CONSUMPTION_RATE
    state.resource_pool = INITIAL_RESOURCES
    
    lid = 1
    for i in range(doves):
        l = Lobster(id=lid, name=f"鸽{i+1}", stance=Stance.DOVE,
            stance_score=-5 - random.randint(0, 5), health=100,
            resources=random.randint(3, 6))
        state.lobsters.append(l); lid += 1
    for i in range(hawks):
        l = Lobster(id=lid, name=f"鹰{i+1}", stance=Stance.HAWK,
            stance_score=5 + random.randint(0, 5), health=100,
            resources=random.randint(4, 7))
        state.lobsters.append(l); lid += 1
    for i in range(neutral):
        l = Lobster(id=lid, name=f"中{i+1}", stance=Stance.NEUTRAL,
            stance_score=random.randint(-2, 2), health=100,
            resources=random.randint(3, 6))
        state.lobsters.append(l); lid += 1
    
    stance_map = {l.id: l.stance for l in state.lobsters}
    for l1 in state.lobsters:
        for l2 in state.lobsters:
            if l1.id != l2.id:
                l1.trust_to[l2.id] = 2 if stance_map[l1.id] == stance_map[l2.id] else 0
    
    timeline = []
    death_log = []
    stance_conversion_count = 0
    
    for round_num in range(1, MAX_ROUNDS + 1):
        state, events = resolve_turn(state, [])
        
        alive = state.get_alive_lobsters()
        factions = state.get_factions()
        
        round_conv = 0
        for e in events:
            if "💀" in e:
                if "觉醒" in e or "绝望" in e:
                    round_conv += 1
                    death_log.append({"round": round_num, "type": "conversion", "event": e})
                elif "死亡" in e:
                    death_log.append({"round": round_num, "type": "natural", "event": e})
        
        stance_conversion_count += round_conv
        
        timeline.append({
            "round": round_num,
            "alive_count": len(alive),
            "dove_count": len(factions['dove']),
            "hawk_count": len(factions['hawk']),
            "neutral_count": len(factions['neutral']),
            "resource_pool": state.resource_pool,
            "events_count": len(events)
        })
        
        if len(alive) == 0:
            break
        
        if round_num > 30 and len(timeline) >= 20:
            recent = timeline[-20:]
            alive_changes = sum(1 for i in range(1, len(recent))
                               if recent[i]["alive_count"] != recent[i-1]["alive_count"])
            if alive_changes <= 2:
                break
    
    final_alive = state.get_alive_lobsters()
    final_factions = state.get_factions()
    
    return {
        "run_id": run_id,
        "hawk_ratio": hawk_ratio,
        "initial_doves": doves,
        "initial_hawks": hawks,
        "initial_neutral": neutral,
        "final_alive": len(final_alive),
        "survival_rate": len(final_alive) / NUM_LOBSTERS,
        "dove_count": len(final_factions['dove']),
        "hawk_count": len(final_factions['hawk']),
        "neutral_count": len(final_factions['neutral']),
        "stance_conversions": stance_conversion_count,
        "total_rounds": round_num,
        "timeline": timeline,
        "death_log": death_log
    }


def run_condition_batch(hawk_ratio: float) -> dict:
    """运行单一条件下的多次重复"""
    print(f"\n{'='*70}")
    print(f"P1-相变探测 | 初始鹰派比例: {hawk_ratio*100:.0f}%")
    print(f"{'='*70}")
    
    neutral = NUM_NEUTRAL
    remaining = NUM_LOBSTERS - neutral
    hawks = int(remaining * hawk_ratio)
    doves = remaining - hawks
    print(f"配置: 鸽{doves} / 鹰{hawks} / 中立{neutral} (共{NUM_LOBSTERS})")
    
    results = []
    for i in range(NUM_RUNS):
        r = run_single_condition(hawk_ratio, i)
        results.append(r)
        print(f"  运行{i+1}: 存活{r['survival_rate']*100:.1f}% | "
              f"鸽{r['dove_count']} 鹰{r['hawk_count']} 中{r['neutral_count']} | "
              f"转换{r['stance_conversions']} | {r['total_rounds']}回合")
    
    survival_rates = [r["survival_rate"] for r in results]
    mean_rate = sum(survival_rates) / len(survival_rates)
    std_dev = (sum((x - mean_rate) ** 2 for x in survival_rates) / len(survival_rates)) ** 0.5
    cv = std_dev / mean_rate * 100 if mean_rate > 0 else 0
    
    # 终态平均值
    mean_dove = sum(r["dove_count"] for r in results) / len(results)
    mean_hawk = sum(r["hawk_count"] for r in results) / len(results)
    mean_neutral = sum(r["neutral_count"] for r in results) / len(results)
    mean_rounds = sum(r["total_rounds"] for r in results) / len(results)
    mean_conv = sum(r["stance_conversions"] for r in results) / len(results)
    
    print(f"  ─────────────────────────────────────────")
    print(f"  平均存活率: {mean_rate*100:.1f}% ± {std_dev*100:.2f}% | CV: {cv:.1f}%")
    print(f"  终态: 鸽{mean_dove:.0f} 鹰{mean_hawk:.0f} 中{mean_neutral:.0f}")
    print(f"  达到稳态: {mean_rounds:.0f}回合 | 转换均值: {mean_conv:.1f}")
    
    return {
        "hawk_ratio": hawk_ratio,
        "initial_doves": doves,
        "initial_hawks": hawks,
        "initial_neutral": neutral,
        "mean_survival_rate": mean_rate,
        "std": std_dev,
        "cv_percent": cv,
        "mean_dove_count": mean_dove,
        "mean_hawk_count": mean_hawk,
        "mean_neutral_count": mean_neutral,
        "mean_rounds": mean_rounds,
        "mean_conversions": mean_conv,
        "runs": results
    }


def main():
    print("="*70)
    print("P1 相变探测实验（Layer 3）")
    print(f"机制: v0.8-Scheme E | 规模: {NUM_LOBSTERS}只")
    print(f"扫描点: 初始鹰派比例 {'/'.join([f'{r*100:.0f}%' for r in HAWK_RATIOS])}")
    print(f"中立固定: {NUM_NEUTRAL}只 | 每组重复: {NUM_RUNS}次")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    all_conditions = []
    for hawk_ratio in HAWK_RATIOS:
        condition_result = run_condition_batch(hawk_ratio)
        all_conditions.append(condition_result)
    
    # 打印汇总表格
    print(f"\n{'='*70}")
    print("相变探测汇总")
    print(f"{'='*70}")
    print(f"{'初始鹰%':>8} | {'存活率':>8} | {'±':>6} | {'CV%':>5} | {'终态鸽':>6} | {'终态鹰':>6} | {'终态中':>6} | {'回合':>5}")
    print("-" * 70)
    for c in all_conditions:
        print(f"{c['hawk_ratio']*100:>7.0f}% | {c['mean_survival_rate']*100:>7.1f}% | "
              f"{c['std']*100:>5.2f}% | {c['cv_percent']:>4.1f} | "
              f"{c['mean_dove_count']:>6.0f} | {c['mean_hawk_count']:>6.0f} | "
              f"{c['mean_neutral_count']:>6.0f} | {c['mean_rounds']:>5.0f}")
    
    # 保存数据
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '07-data', 'v0.8_schemeE_layer3', 'P1_phase_transition')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"P1_phase_transition_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w') as f:
        json.dump({
            "experiment": "P1-PhaseTransition",
            "version": "v0.8-E",
            "num_lobsters": NUM_LOBSTERS,
            "num_neutral": NUM_NEUTRAL,
            "hawk_ratios": HAWK_RATIOS,
            "num_runs": NUM_RUNS,
            "conditions": all_conditions
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存: {output_file}")

if __name__ == "__main__":
    main()
