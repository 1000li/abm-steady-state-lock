#!/usr/bin/env python3
"""
方案E规模测试运行器 - 1000只（验证超大规模稳定性）
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from fsm import resolve_turn
from models import GameState, Agent, Stance
import json
from datetime import datetime
import random

NUM_RUNS = 3  # 3次重复验证稳定性
MAX_ROUNDS = 100
NUM_LOBSTERS = 1000
INITIAL_RESOURCES = 3000  # 按比例：100只=300，1000只=3000
RESOURCE_REGEN = 1000     # 按比例：100只=100，1000只=1000

def run_single_experiment(run_id: int) -> dict:
    print(f"\n{'='*60}")
    print(f"E-Scale-1000 实验运行 #{run_id + 1}/{NUM_RUNS}")
    print(f"{'='*60}")
    
    state = GameState()
    state.resource_regen = RESOURCE_REGEN
    state.consumption_rate = 2
    state.resource_pool = INITIAL_RESOURCES
    
    # 1000只龙虾
    num_doves, num_hawks, num_neutral = 300, 300, 400
    agent_id = 1
    
    print(f"初始化 {NUM_LOBSTERS} 只龙虾...")
    
    for i in range(num_doves):
        agent = Agent(id=agent_id, name=f"鸽{i+1}", stance=Stance.DOVE,
                         stance_score=-5 - random.randint(0, 5), health=100, resources=random.randint(3, 6))
        state.agents.append(agent)
        agent_id += 1
    
    for i in range(num_hawks):
        agent = Agent(id=agent_id, name=f"鹰{i+1}", stance=Stance.HAWK,
                         stance_score=5 + random.randint(0, 5), health=100, resources=random.randint(4, 7))
        state.agents.append(agent)
        agent_id += 1
    
    for i in range(num_neutral):
        agent = Agent(id=agent_id, name=f"中{i+1}", stance=Stance.NEUTRAL,
                         stance_score=random.randint(-2, 2), health=100, resources=random.randint(3, 6))
        state.agents.append(agent)
        agent_id += 1
    
    # 初始化信任关系（简化：相同派系=信任2，不同=0）
    print("初始化信任关系...")
    stance_map = {l.id: l.stance for l in state.agents}
    for l1 in state.agents:
        for l2 in state.agents:
            if l1.id != l2.id:
                l1.trust_to[l2.id] = 2 if stance_map[l1.id] == stance_map[l2.id] else 0
    
    print(f"规模: {NUM_LOBSTERS}只 | 资源: {INITIAL_RESOURCES}/{RESOURCE_REGEN}")
    print(f"初始: 鸽{num_doves} 鹰{num_hawks} 中{num_neutral}")
    
    timeline = []
    for round_num in range(1, MAX_ROUNDS + 1):
        state, events = resolve_turn(state, [])
        alive = state.get_alive_agents()
        factions = state.get_factions()
        
        if round_num % 10 == 0 or round_num == 1:
            print(f"回合{round_num:3d}: 存活{len(alive):4d} | 鸽{len(factions['dove']):3d} 鹰{len(factions['hawk']):3d} 中{len(factions['neutral']):3d}")
        
        timeline.append({"round": round_num, "alive_count": len(alive), 
                        "dove_count": len(factions['dove']), "hawk_count": len(factions['hawk'])})
        
        if len(alive) == 0:
            print(f"\n💀 第{round_num}回合：全部死亡")
            break
        
        if round_num > 30 and len(timeline) >= 20:
            recent = timeline[-20:]
            if sum(1 for i in range(1, len(recent)) if recent[i]["alive_count"] != recent[i-1]["alive_count"]) <= 2:
                print(f"\n✓ 第{round_num}回合：达到稳态")
                break
    
    final_alive = state.get_alive_agents()
    final_factions = state.get_factions()
    
    print(f"\n结果: 存活{len(final_alive)}/{NUM_LOBSTERS} ({len(final_alive)/NUM_LOBSTERS*100:.1f}%)")
    print(f"派系: 鸽{len(final_factions['dove'])} 鹰{len(final_factions['hawk'])} 中{len(final_factions['neutral'])}")
    
    return {"run_id": run_id, "final_alive": len(final_alive), 
            "survival_rate": len(final_alive) / NUM_LOBSTERS,
            "dove_count": len(final_factions['dove']), "hawk_count": len(final_factions['hawk'])}

def main():
    print("="*60)
    print(f"方案E超大规模测试: {NUM_LOBSTERS}只龙虾")
    print(f"配置: 初始{INITIAL_RESOURCES} + 恢复{RESOURCE_REGEN}/轮")
    print(f"目的: 验证变异系数(CV)随规模变化趋势")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    for i in range(NUM_RUNS):
        result = run_single_experiment(i)
        results.append(result)
    
    survival_rates = [r["survival_rate"] for r in results]
    mean_rate = sum(survival_rates) / len(survival_rates)
    std_dev = (sum((x - mean_rate) ** 2 for x in survival_rates) / len(survival_rates)) ** 0.5
    cv = std_dev / mean_rate * 100 if mean_rate > 0 else 0
    
    print(f"\n{'='*60}")
    print("汇总统计")
    print(f"{'='*60}")
    for i, r in enumerate(results):
        print(f"  运行{i+1}: {r['survival_rate']*100:.1f}%")
    print(f"  平均: {mean_rate*100:.1f}% ± {std_dev*100:.2f}%")
    print(f"  CV: {cv:.1f}%")
    
    # CV趋势对比
    print(f"\n{'='*60}")
    print("CV规模趋势对比")
    print(f"{'='*60}")
    print(f"  50只:   CV = 29.9%")
    print(f"  100只:  CV = 8.2%")
    print(f"  200只:  CV = 2.9%")
    print(f"  1000只: CV = {cv:.1f}%  ← 当前")
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '07-data', 'v0.8_schemeE_scale')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, f"scale_{NUM_LOBSTERS}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"), 'w') as f:
        json.dump({"experiment": f"E-Scale-{NUM_LOBSTERS}", "num_agents": NUM_LOBSTERS,
                   "mean_survival_rate": mean_rate, "std": std_dev, "cv_percent": cv, "runs": results}, f, indent=2)

if __name__ == "__main__":
    main()
