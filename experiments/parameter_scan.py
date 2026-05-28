import sys
import os
import json
import time
import random
from datetime import datetime

sys.path.insert(0, '../src')
from fsm import resolve_turn
from models import Agent, GameState, Stance

def create_r3_state(n=1000):
    """创建R3基准状态"""
    state = GameState(
        resource_pool=300, 
        resource_regen=12 * n // 10,  # 每100只对应12
        consumption_rate=2
    )
    # 混合配置: 50鸽/30鹰/20中
    for i in range(n):
        if i < n * 0.5:
            stance, score = Stance.DOVE, -5
        elif i < n * 0.8:
            stance, score = Stance.HAWK, 5
        else:
            stance, score = Stance.NEUTRAL, 0
        agent = Agent(
            id=i, name=f'L{i}', 
            stance=stance, stance_score=score,
            health=100, resources=5
        )
        state.agents.append(agent)
    return state

def run_single(params, seed=None):
    """运行单次100轮模拟"""
    if seed is not None:
        random.seed(seed)
    state = create_r3_state(1000)
    faction_changes = 0
    
    for round_num in range(100):
        # 记录本轮初始立场分布
        pre_stances = {}
        for l in state.agents:
            pre_stances[l.id] = l.stance
        
        state, events = resolve_turn(state, [], mechanism_params=params)
        
        # 统计派系转换
        for l in state.agents:
            if l.id in pre_stances and l.stance != pre_stances[l.id]:
                faction_changes += 1
    
    alive = state.get_alive_agents()
    from collections import Counter
    stances = Counter([l.stance.value for l in alive])
    
    return {
        "survival_rate": len(alive) / 10.0,
        "alive_count": len(alive),
        "dove": stances.get("dove", 0),
        "hawk": stances.get("hawk", 0),
        "neutral": stances.get("neutral", 0),
        "faction_changes": faction_changes,
        "rounds": 100,
    }

def run_batch(prob_value, repeats=5):
    """批量运行，返回汇总统计"""
    results = []
    for i in range(repeats):
        seed = int(time.time() * 1000) % 100000 + i
        params = {"desperate_attack_prob": prob_value}
        result = run_single(params, seed=seed)
        result["run_id"] = i + 1
        result["seed"] = seed
        result["desperate_attack_prob"] = prob_value
        results.append(result)
    
    # 汇总
    survival_rates = [r["survival_rate"] for r in results]
    avg_survival = sum(survival_rates) / len(survival_rates)
    
    # 计算标准差
    if len(survival_rates) > 1:
        variance = sum((x - avg_survival) ** 2 for x in survival_rates) / (len(survival_rates) - 1)
        std = variance ** 0.5
    else:
        std = 0.0
    
    cv = (std / avg_survival * 100) if avg_survival > 0 else 0
    
    return {
        "desperate_attack_prob": prob_value,
        "repeats": repeats,
        "avg_survival_rate": avg_survival,
        "std": std,
        "cv_percent": cv,
        "min_survival": min(survival_rates),
        "max_survival": max(survival_rates),
        "raw_results": results,
    }

def main():
    # 扫描范围: 0.1, 0.2, ..., 0.9
    probs = [round(x * 0.1, 1) for x in range(1, 10)]
    
    print(f"开始饿急攻击概率扫描: {probs}")
    print(f"固定条件: 1000只, R3配置, 100回合, 每概率5重复")
    print("=" * 60)
    
    all_results = []
    for prob in probs:
        print(f"\n扫描概率 = {prob} ...")
        batch = run_batch(prob, repeats=5)
        all_results.append(batch)
        
        print(f"  平均存活率: {batch['avg_survival_rate']:.1f}% ± {batch['std']:.2f}% (CV={batch['cv_percent']:.1f}%)")
        print(f"  范围: {batch['min_survival']:.1f}% ~ {batch['max_survival']:.1f}%")
        
        # 打印各次详细结果
        for r in batch["raw_results"]:
            print(f"    Run#{r['run_id']}: {r['survival_rate']:.1f}% | 鸽{r['dove']} 鹰{r['hawk']} 中{r['neutral']} | 转换{r['faction_changes']}次")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"../../07-data/v0.8_robustness/sensitivity_desperate_attack"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/scan_desperate_attack_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "scan_type": "desperate_attack_probability",
            "scan_values": probs,
            "fixed_conditions": {
                "n": 1000,
                "resource_regen_per_100": 12,
                "consumption_rate": 2,
                "max_rounds": 100,
                "repeats_per_value": 5,
            },
            "results": all_results,
            "timestamp": timestamp,
        }, f, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"扫描完成！结果保存至: {output_file}")
    
    # 打印汇总表
    print(f"\n汇总表:")
    print(f"{'概率':>6} | {'存活率':>8} | {'CV':>6} | {'鸽派':>6} | {'鹰派':>6} | {'中立':>6}")
    print("-" * 50)
    for batch in all_results:
        r0 = batch["raw_results"][0]  # 取第一次的终态结构作为参考
        print(f"{batch['desperate_attack_prob']:>6.1f} | {batch['avg_survival_rate']:>7.1f}% | {batch['cv_percent']:>5.1f}% | {r0['dove']:>5} | {r0['hawk']:>5} | {r0['neutral']:>5}")

if __name__ == "__main__":
    main()
