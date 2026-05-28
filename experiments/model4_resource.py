#!/usr/bin/env python3
"""
C1 资源交叉验证实验
纯鸽派(1000只)在不同资源丰度下的存活率测试
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from fsm import resolve_turn
from models import GameState, Agent, Stance
import json
from datetime import datetime
import random

NUM_RUNS = 5
MAX_ROUNDS = 100
NUM_LOBSTERS = 1000
CONSUMPTION_RATE = 2

# 资源水平配置 (对应100只R2-R5的等比放大)
# 100只基准: regen=120/160/200/240, 净资源=-80/-40/0/+40
# 1000只等比: regen=1200/1600/2000/2400, 净资源=-800/-400/0/+400
# 但C1已有基准使用的是regen=1200, 净资源=-800, 对应100只R3(-40)??
# 修正: 100只R3是regen=160,净资源=-40; 对应1000只regen=1600,净资源=-400
# 但C1修正版报告说regen=1200是"R3基准赤字"... 让我用报告中的实际参数
RESOURCE_CONFIGS = [
    ("C1-R2", 800, 3000),    # 重度赤字 (净-1200)
    ("C1-R3", 1200, 3000),   # 基准 (净-800, 已有数据60.6%)
    ("C1-R4", 2000, 3000),   # 零平衡 (净0)
    ("C1-R5", 2400, 3000),   # 盈余 (净+400)
]

def classify_events(events):
    natural_death = 0
    stance_conversion = 0
    for e in events:
        if "💀" in e:
            if "直接死亡" in e:
                continue
            elif "觉醒" in e or "绝望" in e:
                stance_conversion += 1
            elif "死亡" in e:
                natural_death += 1
    return natural_death, stance_conversion

def run_single_experiment(run_id: int, exp_label: str, regen: int, initial_pool: int) -> dict:
    print(f"\n{'='*70}")
    print(f"{exp_label} #{run_id + 1}/{NUM_RUNS} | regen={regen} | pool={initial_pool}")
    print(f"{'='*70}")
    
    state = GameState()
    state.resource_regen = regen
    state.consumption_rate = CONSUMPTION_RATE
    state.resource_pool = initial_pool
    
    # 初始化1000只纯鸽派
    for i in range(NUM_LOBSTERS):
        agent = Agent(
            id=i+1, name=f"鸽{i+1}", stance=Stance.DOVE,
            stance_score=-5 - random.randint(0, 5), health=100,
            resources=random.randint(3, 6)
        )
        state.agents.append(agent)
    
    # 初始化信任（全部是鸽派，互相信任）
    for l1 in state.agents:
        for l2 in state.agents:
            if l1.id != l2.id:
                l1.trust_to[l2.id] = 2
    
    net_resource = regen - CONSUMPTION_RATE * NUM_LOBSTERS
    print(f"规模: {NUM_LOBSTERS}只 | 初始资源池: {initial_pool} | 再生: {regen}/轮")
    print(f"净资源: {net_resource}/轮 | 单只净资源: {net_resource/NUM_LOBSTERS:.2f}/轮")
    print(f"初始: 鸽{NUM_LOBSTERS} 鹰0 中0")
    
    timeline = []
    natural_death_count = 0
    stance_conversion_count = 0
    
    for round_num in range(1, MAX_ROUNDS + 1):
        state, events = resolve_turn(state, [])
        
        alive = state.get_alive_agents()
        factions = state.get_factions()
        
        round_natural_death, round_stance_conversion = classify_events(events)
        natural_death_count += round_natural_death
        stance_conversion_count += round_stance_conversion
        
        timeline.append({
            "round": round_num,
            "alive_count": len(alive),
            "dove_count": len(factions['dove']),
            "hawk_count": len(factions['hawk']),
            "neutral_count": len(factions['neutral']),
            "resource_pool": state.resource_pool,
        })
        
        if round_num % 10 == 0 or round_num == 1:
            print(f"回合{round_num:3d}: 存活{len(alive):4d} | "
                  f"鸽{len(factions['dove']):3d} 鹰{len(factions['hawk']):3d} 中{len(factions['neutral']):3d} | "
                  f"资源{state.resource_pool:5d}")
        
        if len(alive) == 0:
            print(f"\n💀 第{round_num}回合：全部死亡")
            break
        
        # 稳态检测
        if round_num > 30 and len(timeline) >= 20:
            recent = timeline[-20:]
            alive_changes = sum(1 for i in range(1, len(recent))
                               if recent[i]["alive_count"] != recent[i-1]["alive_count"])
            if alive_changes <= 2:
                print(f"\n✓ 第{round_num}回合：达到稳态")
                break
    
    final_alive = state.get_alive_agents()
    final_factions = state.get_factions()
    
    print(f"\n结果: 存活{len(final_alive)}/{NUM_LOBSTERS} ({len(final_alive)/NUM_LOBSTERS*100:.1f}%)")
    print(f"派系: 鸽{len(final_factions['dove'])} 鹰{len(final_factions['hawk'])} 中{len(final_factions['neutral'])}")
    print(f"统计: 自然死{natural_death_count} | 转换{stance_conversion_count}")
    
    return {
        "run_id": run_id,
        "final_alive": len(final_alive),
        "survival_rate": len(final_alive) / NUM_LOBSTERS,
        "dove_count": len(final_factions['dove']),
        "hawk_count": len(final_factions['hawk']),
        "neutral_count": len(final_factions['neutral']),
        "natural_deaths": natural_death_count,
        "stance_conversions": stance_conversion_count,
        "total_rounds": round_num,
        "timeline": timeline,
    }

def run_resource_level(exp_label: str, regen: int, initial_pool: int):
    print("="*70)
    print(f"【{exp_label}】资源交叉验证")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    for i in range(NUM_RUNS):
        result = run_single_experiment(i, exp_label, regen, initial_pool)
        results.append(result)
    
    survival_rates = [r["survival_rate"] for r in results]
    mean_rate = sum(survival_rates) / len(survival_rates)
    std_dev = (sum((x - mean_rate) ** 2 for x in survival_rates) / len(survival_rates)) ** 0.5
    cv = std_dev / mean_rate * 100 if mean_rate > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"{exp_label} 汇总统计")
    print(f"{'='*70}")
    for i, r in enumerate(results):
        print(f"  运行{i+1}: 存活{r['survival_rate']*100:.1f}% | "
              f"自然死{r['natural_deaths']} | 转换{r['stance_conversions']} | "
              f"{r['total_rounds']}回合")
    
    print(f"\n  平均存活率: {mean_rate*100:.1f}% ± {std_dev*100:.2f}%")
    print(f"  CV: {cv:.1f}%")
    
    return {
        "experiment": exp_label,
        "regen": regen,
        "initial_pool": initial_pool,
        "net_resource": regen - CONSUMPTION_RATE * NUM_LOBSTERS,
        "mean_survival_rate": mean_rate,
        "std": std_dev,
        "cv_percent": cv,
        "runs": results,
    }

def main():
    print("="*70)
    print("C1 纯鸽派资源交叉验证 (v0.8-Scheme E)")
    print("="*70)
    
    all_results = []
    for label, regen, pool in RESOURCE_CONFIGS:
        result = run_resource_level(label, regen, pool)
        all_results.append(result)
    
    # 汇总对比
    print("\n" + "="*70)
    print("【跨资源水平对比】")
    print("="*70)
    print(f"{'实验':<10} {'再生':<8} {'净资源':<10} {'存活率':<12} {'CV':<8} {'vs基准':<10}")
    print("-"*70)
    
    baseline = None
    for r in all_results:
        if r["experiment"] == "C1-R3":
            baseline = r["mean_survival_rate"]
            break
    
    for r in all_results:
        diff = ""
        if baseline and r["experiment"] != "C1-R3":
            d = (r["mean_survival_rate"] - baseline) * 100
            diff = f"{d:+.1f}%"
        elif r["experiment"] == "C1-R3":
            diff = "(基准)"
        
        print(f"{r['experiment']:<10} {r['regen']:<8} {r['net_resource']:<+10} "
              f"{r['mean_survival_rate']*100:.1f}%       {r['cv_percent']:.1f}%   {diff}")
    
    # 保存
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '07-data', 'v0.8_C1_resource_cross')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"C1_resource_cross_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w') as f:
        json.dump({
            "experiment_series": "C1-Resource-Cross-Validation",
            "version": "v0.8-Scheme E",
            "num_agents": NUM_LOBSTERS,
            "initial_config": {"dove": NUM_LOBSTERS, "hawk": 0, "neutral": 0},
            "results": all_results,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存: {output_file}")

if __name__ == "__main__":
    main()
