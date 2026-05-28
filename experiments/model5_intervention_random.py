#!/usr/bin/env python3
"""
直接死亡机制实验运行器 - D1 (修正版)
机制：每10回合随机选择1只存活龙虾直接死亡（模拟外部死亡压力）
规模：1000只 | 配置：混合（300鸽/300鹰/400中立）
记录：全量记录（每回合存活/派系/死亡/资源/死亡原因）
修正：区分真正死亡 vs 派系转换事件
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
NUM_RUNS = 5              # 5次重复
MAX_ROUNDS = 100          # 最大100回合
NUM_LOBSTERS = 1000      # 1000只规模
INITIAL_RESOURCES = 3000  # 初始资源
RESOURCE_REGEN = 1000    # 每回合恢复
CONSUMPTION_RATE = 2      # 每回合消耗

# 直接死亡干预参数
DEATH_INTERVAL = 10       # 每10回合
DEATH_COUNT = 1           # 每次杀死1只

# 初始派系比例（混合配置 = R3基准）
NUM_DOVES = 300
NUM_HAWKS = 300
NUM_NEUTRAL = 400


def apply_direct_death(state: GameState, round_num: int) -> list:
    """
    应用直接死亡干预
    每DEATH_INTERVAL回合，随机选择DEATH_COUNT只存活龙虾直接死亡
    返回死亡事件列表
    """
    events = []
    if round_num % DEATH_INTERVAL == 0 and round_num > 0:
        alive = state.get_alive_agents()
        if len(alive) >= DEATH_COUNT:
            victims = random.sample(alive, DEATH_COUNT)
            for victim in victims:
                victim.health = 0
                events.append(f"💀☠️ 直接死亡：{victim.name}({victim.stance.value})被随机选中死亡")
    return events


def classify_events(events, dd_events):
    """
    修正：区分真正死亡 vs 派系转换
    返回：(round_dd, round_natural_death, round_stance_conversion)
    """
    round_dd = len([e for e in dd_events if "直接死亡" in e])
    round_natural_death = 0
    round_stance_conversion = 0
    
    for e in events:
        if "💀" in e:
            if "直接死亡" in e:
                continue
            elif "觉醒" in e or "绝望" in e:
                round_stance_conversion += 1
            elif "死亡" in e:
                round_natural_death += 1
    
    return round_dd, round_natural_death, round_stance_conversion


def run_single_experiment(run_id: int) -> dict:
    print(f"\n{'='*70}")
    print(f"D1-直接死亡 实验运行 #{run_id + 1}/{NUM_RUNS}")
    print(f"{'='*70}")
    
    state = GameState()
    state.resource_regen = RESOURCE_REGEN
    state.consumption_rate = CONSUMPTION_RATE
    state.resource_pool = INITIAL_RESOURCES
    
    # 初始化1000只龙虾（混合配置）
    agent_id = 1
    for i in range(NUM_DOVES):
        agent = Agent(
            id=agent_id, name=f"鸽{i+1}", stance=Stance.DOVE,
            stance_score=-5 - random.randint(0, 5), health=100,
            resources=random.randint(3, 6)
        )
        state.agents.append(agent)
        agent_id += 1
    
    for i in range(NUM_HAWKS):
        agent = Agent(
            id=agent_id, name=f"鹰{i+1}", stance=Stance.HAWK,
            stance_score=5 + random.randint(0, 5), health=100,
            resources=random.randint(4, 7)
        )
        state.agents.append(agent)
        agent_id += 1
    
    for i in range(NUM_NEUTRAL):
        agent = Agent(
            id=agent_id, name=f"中{i+1}", stance=Stance.NEUTRAL,
            stance_score=random.randint(-2, 2), health=100,
            resources=random.randint(3, 6)
        )
        state.agents.append(agent)
        agent_id += 1
    
    # 初始化信任关系
    stance_map = {l.id: l.stance for l in state.agents}
    for l1 in state.agents:
        for l2 in state.agents:
            if l1.id != l2.id:
                l1.trust_to[l2.id] = 2 if stance_map[l1.id] == stance_map[l2.id] else 0
    
    print(f"规模: {NUM_LOBSTERS}只 | 资源: {INITIAL_RESOURCES}/{RESOURCE_REGEN}")
    print(f"初始: 鸽{NUM_DOVES} 鹰{NUM_HAWKS} 中{NUM_NEUTRAL}")
    print(f"干预: 每{DEATH_INTERVAL}回合直接死亡{DEATH_COUNT}只")
    
    # ========== 全量记录结构 ==========
    timeline = []
    death_log = []
    direct_death_count = 0
    natural_death_count = 0
    stance_conversion_count = 0
    
    for round_num in range(1, MAX_ROUNDS + 1):
        # 阶段0: 直接死亡干预（在资源恢复前执行）
        dd_events = apply_direct_death(state, round_num)
        
        # 执行正常回合
        state, events = resolve_turn(state, [])
        
        # 合并事件
        all_events = dd_events + events
        
        alive = state.get_alive_agents()
        factions = state.get_factions()
        
        # 修正：分类事件
        round_dd, round_natural_death, round_stance_conversion = classify_events(events, dd_events)
        direct_death_count += round_dd
        natural_death_count += round_natural_death
        stance_conversion_count += round_stance_conversion
        
        # 记录死亡详情
        for e in dd_events:
            if "直接死亡" in e:
                death_log.append({"round": round_num, "type": "direct", "event": e})
        for e in events:
            if "💀" in e and "直接死亡" not in e:
                if "觉醒" in e or "绝望" in e:
                    death_log.append({"round": round_num, "type": "conversion", "event": e})
                elif "死亡" in e:
                    death_log.append({"round": round_num, "type": "natural", "event": e})
        
        # 全量记录
        timeline.append({
            "round": round_num,
            "alive_count": len(alive),
            "dove_count": len(factions['dove']),
            "hawk_count": len(factions['hawk']),
            "neutral_count": len(factions['neutral']),
            "resource_pool": state.resource_pool,
            "direct_death_this_round": round_dd,
            "natural_death_this_round": round_natural_death,
            "stance_conversion_this_round": round_stance_conversion,
            "events_count": len(all_events)
        })
        
        # 打印（每10回合 + 第1回合 + 有死亡时）
        if round_num % 10 == 0 or round_num == 1 or round_dd > 0:
            print(f"回合{round_num:3d}: 存活{len(alive):4d} | "
                  f"鸽{len(factions['dove']):3d} 鹰{len(factions['hawk']):3d} 中{len(factions['neutral']):3d} | "
                  f"资源{state.resource_pool:4d} | "
                  f"死{round_dd}直/{round_natural_death}自/{round_stance_conversion}转")
        
        # 终止条件
        if len(alive) == 0:
            print(f"\n💀 第{round_num}回合：全部死亡")
            break
        
        # 稳态检测（连续20回合存活数变化≤2）
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
    print(f"死亡统计: 直接{direct_death_count} | 自然(真){natural_death_count} | 转换{stance_conversion_count}")
    
    return {
        "run_id": run_id,
        "final_alive": len(final_alive),
        "survival_rate": len(final_alive) / NUM_LOBSTERS,
        "dove_count": len(final_factions['dove']),
        "hawk_count": len(final_factions['hawk']),
        "neutral_count": len(final_factions['neutral']),
        "direct_deaths": direct_death_count,
        "natural_deaths": natural_death_count,
        "stance_conversions": stance_conversion_count,
        "total_rounds": round_num,
        "timeline": timeline,
        "death_log": death_log
    }


def main():
    print("="*70)
    print(f"D1-直接死亡机制实验 (修正版)")
    print(f"配置: {NUM_LOBSTERS}只 | 混合(鸽{NUM_DOVES}/鹰{NUM_HAWKS}/中{NUM_NEUTRAL})")
    print(f"干预: 每{DEATH_INTERVAL}回合随机{DEATH_COUNT}只直接死亡")
    print(f"记录: 全量（每回合存活/派系/资源/死亡/转换）")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    for i in range(NUM_RUNS):
        result = run_single_experiment(i)
        results.append(result)
    
    # 汇总统计
    survival_rates = [r["survival_rate"] for r in results]
    mean_rate = sum(survival_rates) / len(survival_rates)
    std_dev = (sum((x - mean_rate) ** 2 for x in survival_rates) / len(survival_rates)) ** 0.5
    cv = std_dev / mean_rate * 100 if mean_rate > 0 else 0
    
    dd_counts = [r["direct_deaths"] for r in results]
    nat_counts = [r["natural_deaths"] for r in results]
    conv_counts = [r["stance_conversions"] for r in results]
    
    print(f"\n{'='*70}")
    print("汇总统计")
    print(f"{'='*70}")
    for i, r in enumerate(results):
        print(f"  运行{i+1}: 存活{r['survival_rate']*100:.1f}% | "
              f"直接死{r['direct_deaths']} | 自然死(真){r['natural_deaths']} | 转换{r['stance_conversions']} | "
              f"{r['total_rounds']}回合")
    
    print(f"\n  平均存活率: {mean_rate*100:.1f}% ± {std_dev*100:.2f}%")
    print(f"  CV: {cv:.1f}%")
    print(f"  直接死亡均值: {sum(dd_counts)/len(dd_counts):.1f}")
    print(f"  自然死亡(真)均值: {sum(nat_counts)/len(nat_counts):.1f}")
    print(f"  派系转换均值: {sum(conv_counts)/len(conv_counts):.1f}")
    
    # 与基准对比
    baseline = 27.0
    diff = (mean_rate * 100) - baseline
    print(f"\n  vs R3基准(27.0%): {'+' if diff > 0 else ''}{diff:.1f}%")
    
    # 保存数据
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '07-data',
                              'v0.8_schemeE_intervention', 'D1_direct_death')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"D1_direct_death_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w') as f:
        json.dump({
            "experiment": "D1-DirectDeath-v2",
            "num_agents": NUM_LOBSTERS,
            "initial_config": {"dove": NUM_DOVES, "hawk": NUM_HAWKS, "neutral": NUM_NEUTRAL},
            "intervention": {"type": "direct_death", "interval": DEATH_INTERVAL, "count": DEATH_COUNT},
            "mean_survival_rate": mean_rate,
            "std": std_dev,
            "cv_percent": cv,
            "runs": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存: {output_file}")


if __name__ == "__main__":
    main()
