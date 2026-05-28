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
    """R3-1000 基准状态创建器 (30鸽/30鹰/40中, pool=3000, regen=1200)"""
    state = GameState(
        resource_pool=300,
        resource_regen=12 * n // 10,
        consumption_rate=2
    )
    for i in range(n):
        if i < n * 0.3:
            stance, score = Stance.DOVE, -5
        elif i < n * 0.6:
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
    
    # 记录初始立场分布
    initial = {}
    for l in state.agents:
        initial[l.id] = l.stance.value
    
    for round_num in range(100):
        state, events = resolve_turn(state, [], mechanism_params=params)
    
    alive = state.get_alive_agents()
    from collections import Counter
    stances = Counter([l.stance.value for l in alive])
    
    # 检查立场是否变化
    stance_changed = 0
    for l in alive:
        if l.id in initial and l.stance.value != initial[l.id]:
            stance_changed += 1
    
    return {
        "survival_rate": len(alive) / 10.0,
        "alive_count": len(alive),
        "dove": stances.get("dove", 0),
        "hawk": stances.get("hawk", 0),
        "neutral": stances.get("neutral", 0),
        "stance_changed": stance_changed,
        "rounds": 100,
    }

def run_batch(condition_name, params, repeats=5):
    """批量运行"""
    print(f"\n  条件: {condition_name} ...")
    results = []
    for i in range(repeats):
        seed = int(time.time() * 1000) % 100000 + i
        result = run_single(params, seed=seed)
        result["run_id"] = i + 1
        result["seed"] = seed
        result["condition"] = condition_name
        results.append(result)
        print(f"    Run#{i+1}: {result['survival_rate']:.1f}% | 鸽{result['dove']} 鹰{result['hawk']} 中{result['neutral']} | 立场变化{result['stance_changed']}只")
    
    survival_rates = [r["survival_rate"] for r in results]
    avg_survival = sum(survival_rates) / len(survival_rates)
    
    if len(survival_rates) > 1:
        variance = sum((x - avg_survival) ** 2 for x in survival_rates) / (len(survival_rates) - 1)
        std = variance ** 0.5
    else:
        std = 0.0
    
    cv = (std / avg_survival * 100) if avg_survival > 0 else 0
    
    return {
        "condition": condition_name,
        "repeats": repeats,
        "avg_survival_rate": avg_survival,
        "std": std,
        "cv_percent": cv,
        "min_survival": min(survival_rates),
        "max_survival": max(survival_rates),
        "raw_results": results,
    }

def main():
    conditions = [
        # ABL-0-clean: 完全禁用立场更新
        ("ABL-0-clean_无立场更新", {
            "skip_stance_update": True,
        }),
        # ABL-FULL: 完整机制（对照组）
        ("ABL-FULL_完整机制", {}),
    ]
    
    print("=" * 60)
    print("消融实验: 立场更新的必要性验证（干净版）")
    print("=" * 60)
    print("固定条件: 1000只, R3配置, 100回合, 每条件5重复")
    print("\n预期:")
    print("  ABL-0-clean(无立场更新): 立场不变，初始50/30/20")
    print("  ABL-FULL(完整机制): 基准 = 鸽派主导")
    
    all_results = []
    for name, params in conditions:
        batch = run_batch(name, params, repeats=5)
        all_results.append(batch)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"../../07-data/v0.8_robustness/ablation_clean"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = f"{output_dir}/ablation_clean_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "experiment_type": "ablation_study_clean",
            "target": "stance_update_necessity",
            "conditions": [c[0] for c in conditions],
            "fixed_conditions": {
                "n": 1000,
                "resource_regen_per_100": 12,
                "consumption_rate": 2,
                "max_rounds": 100,
                "repeats_per_condition": 5,
            },
            "results": all_results,
            "timestamp": timestamp,
        }, f, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"干净消融实验完成！结果保存至: {output_file}")
    
    # 汇总表
    print(f"\n{'=' * 60}")
    print("汇总表:")
    print(f"{'条件':<25} | {'存活率':>8} | {'CV':>6} | {'鸽派':>6} | {'鹰派':>6} | {'中立':>6} | {'立场变化':>8}")
    print("-" * 70)
    for batch in all_results:
        r0 = batch["raw_results"][0]
        print(f"{batch['condition']:<25} | {batch['avg_survival_rate']:>7.1f}% | {batch['cv_percent']:>5.1f}% | {r0['dove']:>5} | {r0['hawk']:>5} | {r0['neutral']:>5} | {r0['stance_changed']:>7}")
    
    print(f"\n{'=' * 60}")
    print("结论判断:")
    for batch in all_results:
        r0 = batch["raw_results"][0]
        if r0['stance_changed'] == 0:
            status = "✅ 立场完全不变（无更新生效）"
        elif r0['stance_changed'] < 10:
            status = f"⚠️ 微量立场变化 ({r0['stance_changed']}只)"
        else:
            status = f"❌ 大量立场变化 ({r0['stance_changed']}只)"
        print(f"  {batch['condition']}: {status}")

if __name__ == "__main__":
    main()
