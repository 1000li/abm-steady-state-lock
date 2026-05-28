"""
model3_extinction.py - Faction extinction order (Fig.10)

Tracks the death sequence of factions over rounds to verify
the extinction-order law: Neutral → Hawk → Dove.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fsm import resolve_turn
from models import GameState, Agent, Stance
import json
from datetime import datetime
import random


def run_extinction_tracking(n=1000, seed=None, max_rounds=100):
    """Run single simulation and track faction extinction timeline."""
    if seed is not None:
        random.seed(seed)

    # R3-1000 baseline
    state = GameState(resource_pool=3000, resource_regen=1200, consumption_rate=2)
    for i in range(n):
        if i < n * 0.3:
            stance, score = Stance.DOVE, -5
        elif i < n * 0.6:
            stance, score = Stance.HAWK, 5
        else:
            stance, score = Stance.NEUTRAL, 0
        state.agents.append(Agent(
            id=i, name=f'L{i}', stance=stance, stance_score=score,
            health=100, resources=5
        ))

    # Track when each faction goes extinct
    extinction = {
        'neutral': None,
        'hawk': None,
        'dove': None,
    }
    initial_counts = {'neutral': int(n * 0.4), 'hawk': int(n * 0.3), 'dove': int(n * 0.3)}

    timeline = []
    for round_num in range(1, max_rounds + 1):
        state, events = resolve_turn(state, [])
        alive = state.get_alive_agents()
        factions = state.get_factions()

        counts = {
            'dove': len(factions['dove']),
            'hawk': len(factions['hawk']),
            'neutral': len(factions['neutral']),
        }

        # Record extinction round
        for faction in ['neutral', 'hawk', 'dove']:
            if extinction[faction] is None and counts[faction] == 0:
                extinction[faction] = round_num

        timeline.append({
            'round': round_num,
            'alive': len(alive),
            **counts,
        })

        if len(alive) == 0:
            break

    return {
        'seed': seed,
        'initial_counts': initial_counts,
        'extinction': extinction,
        'timeline': timeline,
        'final_alive': len(alive),
    }


def main():
    print("=" * 60)
    print("M3: Faction Extinction Order Tracking")
    print("=" * 60)

    results = []
    for seed in [42, 123, 456, 789, 2024]:
        result = run_extinction_tracking(n=1000, seed=seed)
        results.append(result)

        ext = result['extinction']
        print(f"\nSeed {seed}:")
        print(f"  Neutral extinct: Round {ext['neutral'] or 'N/A'}")
        print(f"  Hawk extinct:    Round {ext['hawk'] or 'N/A'}")
        print(f"  Dove extinct:    Round {ext['dove'] or 'N/A'} (never = survived)")
        print(f"  Final alive:     {result['final_alive']}/1000")

    # Verify extinction order across runs
    print(f"\n{'=' * 60}")
    print("Extinction Order Verification")
    print(f"{'=' * 60}")
    order_correct = 0
    for r in results:
        ext = r['extinction']
        # Expected: Neutral extinct first, then Hawk, Dove survives
        if (ext['neutral'] is not None and
            ext['hawk'] is not None and
            ext['neutral'] < ext['hawk'] and
            ext['dove'] is None):
            order_correct += 1
            print(f"  ✓ Seed {r['seed']}: N({ext['neutral']}) < H({ext['hawk']}) < D(survived)")
        else:
            print(f"  ✗ Seed {r['seed']}: Order violated or Dove extinct")

    print(f"\n  {order_correct}/{len(results)} runs confirm N → H → D order")

    # Save
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"extinction_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(filepath, 'w') as f:
        json.dump({
            'experiment': 'M3_Extinction_Order',
            'n': 1000,
            'runs': results,
            'verification': {
                'correct': order_correct,
                'total': len(results),
            },
        }, f, indent=2)
    print(f"\n  Saved to {filepath}")


if __name__ == "__main__":
    main()
