#!/usr/bin/env python3
"""
I3 针对性处决实验运行器
机制：v0.8-Scheme E | 每10回合处决最强鹰派
规模：1000只 | 配置：混合（300鸽/300鹰/400中立）
目的：测试精准打击鹰派能否改变稳态结构/提升存活率
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from fsm import resolve_turn
from models import GameState, Agent, Stance
import json
from datetime import datetime
import random

# ========== 实验参数 ==========
NUM_RUNS = 5
MAX_ROUNDS = 100
NUM_LOBSTERS = 1000
INITIAL_RESOURCES = 3000
RESOURCE_REGEN = 1000
CONSUMPTION_RATE = 2

# 干预参数
INTERVAL = 10       # 每10回合
COUNT = 1           # 每次处决1只

# 初始配置
NUM_DOVES = 300
NUM_HAWKS = 300
NUM_NEUTRAL = 400


def apply_targeted_hawk_death(state: GameState, round_num: int) -> list:
    """
    针对性处决：找到最强鹰派并杀死
    强度评估：resources + health/5 (资源为主，健康为辅)
    """
    events = []
    if round_num % INTERVAL == 0 and round_num > 0:
        alive = state.get_alive_agents()
        # 筛选鹰派
        hawks = [l for l in alive if l.stance == Stance.HAWK]
        if len(hawks) >= COUNT:
            # 按强度排序 (resources * 1.0 + health * 0.2)
            hawks.sort(key=lambda l: l.resources + l.health * 0.2, reverse=True)
            victims = hawks[:COUNT]
            for victim in victims:
                victim.health = 0
                strength = victim.resources + victim.health * 0.2
                events.append(f"💀🔪 针对性处决：{victim.name}(鹰派，强度{strength:.1f})被精准清除")
        elif len(hawks) > 0:
            # 鹰派不足，杀剩余的
            victims = hawks[:min(COUNT, len(hawks))]
            for victim in victims:
                victim.health = 0
                events.append(f"💀🔪 针对性处决：{victim.name}(鹰派，剩余少量)被清除")
    return events


def classify_events(events, intervention_events):
    """区分干预死亡 vs 自然死亡 vs 派系转换"""
    round_intervention = len([e for e in intervention_events if "处决" in e])
    round_natural = 0
    round_conversion = 0
    
    for e in events:
        if "💀" in e:
            if "处决" in e:
                continue
            elif "觉醒" in e or "绝望" in e:
                round_conversion += 1
            elif "死亡" in e:
                round_natural += 1
    
    return round_intervention, round_natural, round_conversion


def run_single_experiment(run_id: int) -> dict:
    print(f"\n{'='*70}")
    print(f"I3-针对性处决 实验运行 #{run_id + 1}/{NUM_RUNS}")
    print(f"{'='*70}")
    
    random.seed(5000 + run_id)
    
    state = GameState()
    state.resource_regen = RESOURCE_REGEN
    state.consumption_rate = CONSUMPTION_RATE
    state.resource_pool = INITIAL_RESOURCES
    
    # 初始化
    lid = 1
    for i in range(NUM_DOVES):
        l = Agent(id=lid, name=f"鸽{i+1}", stance=Stance.DOVE,
            stance_score=-5 - random.randint(0, 5), health=100,
            resources=random.randint(3, 6))
        state.agents.append(l); lid += 1
    for i in range(NUM_HAWKS):
        l = Agent(id=lid, name=f"鹰{i+1}", stance=Stance.HAWK,
            stance_score=5 + random.randint(0, 5), health=100,
            resources=random.randint(4, 7))
        state.agents.append(l); lid += 1
    for i in range(NUM_NEUTRAL):
        l = Agent(id=lid, name=f"中{i+1}", stance=Stance.NEUTRAL,
            stance_score=random.randint(-2, 2), health=100,
            resources=random.randint(3, 6))
        state.agents.append(l); lid += 1
    
    # 信任关系
    stance_map = {l.id: l.stance for l in state.agents}
    for l1 in state.agents:
        for l2 in state.agents:
            if l1.id != l2.id:
                l1.trust_to[l2.id] = 2 if stance_map[l1.id] == stance_map[l2.id] else 0
    
    print(f"规模: {NUM_LOBSTERS}只 | 资源: {INITIAL_RESOURCES}/{RESOURCE_REGEN}")
    print(f"初始: 鸽{NUM_DOVES} 鹰{NUM_HAWKS} 中{NUM_NEUTRAL}")
    print(f"干预: 每{INTERVAL}回合处决最强鹰派×{COUNT}")
    
    timeline = []
    death_log = []
    intervention_count = 0
    natural_death_count = 0
    stance_conversion_count = 0
    
    for round_num in range(1, MAX_ROUNDS + 1):
        # 阶段0: 干预
        int_events = apply_targeted_hawk_death(state, round_num)
        
        # 正常回合
        state, events = resolve_turn(state, [])
        
        all_events = int_events + events
        alive = state.get_alive_agents()
        factions = state.get_factions()
        
        round_int, round_nat, round_conv = classify_events(events, int_events)
        intervention_count += round_int
        natural_death_count += round_nat
        stance_conversion_count += round_conv
        
        for e in int_events:
            if "处决" in e:
                death_log.append({"round": round_num, "type": "intervention", "event": e})
        for e in events:
            if "💀" in e and "处决" not in e:
                if "觉醒" in e or "绝望" in e:
                    death_log.append({"round": round_num, "type": "conversion", "event": e})
                elif "死亡" in e:
                    death_log.append({"round": round_num, "type": "natural", "event": e})
        
        timeline.append({
            "round": round_num,
            "alive_count": len(alive),
            "dove_count": len(factions['dove']),
            "hawk_count": len(factions['hawk']),
            "neutral_count": len(factions['neutral']),
            "resource_pool": state.resource_pool,
            "intervention_this_round": round_int,
            "natural_death_this_round": round_nat,
            "stance_conversion_this_round": round_conv,
            "events_count": len(all_events)
        })
        
        if round_num % 10 == 0 or round_num == 1:
            hawk_alive = len(factions['hawk'])
            print(f"回合{round_num:3d}: 存活{len(alive):4d} | "
                  f"鸽{len(factions['dove']):3d} 鹰{hawk_alive:3d} 中{len(factions['neutral']):3d} | "
                  f"资源{state.resource_pool:5d} | "
                  f"处{round_int}死{round_nat}自/{round_conv}转")
        
        if len(alive) == 0:
            print(f"\n💀 第{round_num}回合：全部死亡")
            break
        
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
    print(f"统计: 处决{intervention_count} | 自然死(真){natural_death_count} | 转换{stance_conversion_count}")
    
    return {
        "run_id": run_id,
        "final_alive": len(final_alive),
        "survival_rate": len(final_alive) / NUM_LOBSTERS,
        "dove_count": len(final_factions['dove']),
        "hawk_count": len(final_factions['hawk']),
        "neutral_count": len(final_factions['neutral']),
        "intervention_deaths": intervention_count,
        "natural_deaths": natural_death_count,
        "stance_conversions": stance_conversion_count,
        "total_rounds": round_num,
        "timeline": timeline,
        "death_log": death_log
    }


def main():
    print("="*70)
    print("I3 针对性处决（v0.8-Scheme E）")
    print(f"配置: {NUM_LOBSTERS}只 | 鸽{NUM_DOVES}/鹰{NUM_HAWKS}/中{NUM_NEUTRAL}")
    print(f"干预: 每{INTERVAL}回合处决最强鹰派×{COUNT}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    for i in range(NUM_RUNS):
        result = run_single_experiment(i)
        results.append(result)
    
    survival_rates = [r["survival_rate"] for r in results]
    mean_rate = sum(survival_rates) / len(survival_rates)
    std_dev = (sum((x - mean_rate) ** 2 for x in survival_rates) / len(survival_rates)) ** 0.5
    cv = std_dev / mean_rate * 100 if mean_rate > 0 else 0
    
    int_counts = [r["intervention_deaths"] for r in results]
    nat_counts = [r["natural_deaths"] for r in results]
    conv_counts = [r["stance_conversions"] for r in results]
    
    print(f"\n{'='*70}")
    print("汇总统计")
    print(f"{'='*70}")
    for i, r in enumerate(results):
        print(f"  运行{i+1}: 存活{r['survival_rate']*100:.1f}% | "
              f"处决{r['intervention_deaths']} | 自然死(真){r['natural_deaths']} | "
              f"转换{r['stance_conversions']} | {r['total_rounds']}回合")
    
    print(f"\n  平均存活率: {mean_rate*100:.1f}% ± {std_dev*100:.2f}%")
    print(f"  CV: {cv:.1f}%")
    print(f"  处决均值: {sum(int_counts)/len(int_counts):.1f}")
    print(f"  自然死亡(真)均值: {sum(nat_counts)/len(nat_counts):.1f}")
    print(f"  派系转换均值: {sum(conv_counts)/len(conv_counts):.1f}")
    
    baseline = 27.0
    diff = (mean_rate * 100) - baseline
    print(f"\n  vs R3基准(27.0%): {'+' if diff > 0 else ''}{diff:.1f}%")
    
    d1_baseline = 20.7
    d1_diff = (mean_rate * 100) - d1_baseline
    print(f"  vs D1直接死亡(20.7%): {'+' if d1_diff > 0 else ''}{d1_diff:.1f}%")
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '07-data', 'v0.8_schemeE_intervention', 'I3_targeted_hawk')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"I3_targeted_hawk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w') as f:
        json.dump({
            "experiment": "I3-TargetedHawkDeath",
            "version": "v0.8-E",
            "num_agents": NUM_LOBSTERS,
            "initial_config": {"dove": NUM_DOVES, "hawk": NUM_HAWKS, "neutral": NUM_NEUTRAL},
            "intervention": {"type": "targeted_hawk_death", "interval": INTERVAL, "count": COUNT},
            "mean_survival_rate": mean_rate,
            "std": std_dev,
            "cv_percent": cv,
            "runs": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存: {output_file}")

if __name__ == "__main__":
    main()
