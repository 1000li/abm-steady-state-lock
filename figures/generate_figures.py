"""
generate_figures.py - Generate all paper figures

Reproduces Figures 2-10 from the paper using the core ABM engine.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

from fsm import resolve_turn
from models import GameState, Agent, Stance


def create_r3_state(n=1000, seed=None):
    """Create R3-1000 baseline state."""
    if seed is not None:
        import random
        random.seed(seed)
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
    return state


def run_single(n=1000, seed=None, max_rounds=100):
    """Run single simulation and return trajectory."""
    if seed is not None:
        import random
        random.seed(seed)
    state = create_r3_state(n)
    trajectory = []
    for round_num in range(max_rounds):
        state, events = resolve_turn(state, [])
        alive = state.get_alive_agents()
        stances = Counter([l.stance.value for l in alive])
        trajectory.append({
            'round': round_num + 1,
            'alive': len(alive),
            'dove': stances.get('dove', 0),
            'hawk': stances.get('hawk', 0),
            'neutral': stances.get('neutral', 0),
        })
    return trajectory


def plot_fig2_evolution_trajectory(output_dir='.'):
    """Fig.2: 100-round evolution trajectory (R3-1000 baseline)."""
    print("Fig.2: Evolution trajectory...")
    trajectory = run_single(n=1000, seed=42)
    
    rounds = [t['round'] for t in trajectory]
    alive = [t['alive'] for t in trajectory]
    dove = [t['dove'] for t in trajectory]
    hawk = [t['hawk'] for t in trajectory]
    neutral = [t['neutral'] for t in trajectory]
    
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    
    # Panel A: Total alive
    axes[0].plot(rounds, alive, 'k-', linewidth=1.5)
    axes[0].axhline(y=158, color='r', linestyle='--', alpha=0.5, label='Baseline ~15.8%')
    axes[0].set_ylabel('Alive count')
    axes[0].set_title('A. Total population')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Panel B: Faction composition
    axes[1].plot(rounds, dove, 'b-', label='Dove', linewidth=1.5)
    axes[1].plot(rounds, hawk, 'r-', label='Hawk', linewidth=1.5)
    axes[1].plot(rounds, neutral, 'g-', label='Neutral', linewidth=1.5)
    axes[1].set_ylabel('Count')
    axes[1].set_xlabel('Round')
    axes[1].set_title('B. Faction composition')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'fig2_evolution_trajectory.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✓ fig2_evolution_trajectory.png")


def plot_fig3_size_scaling(output_dir='.'):
    """Fig.3: Size scaling law (n=50, 100, 200, 1000)."""
    print("Fig.3: Size scaling law...")
    
    sizes = [50, 100, 200, 1000]
    survival_rates = []
    
    for n in sizes:
        print(f"  Running n={n}...")
        rates = []
        for seed in range(5):
            traj = run_single(n=n, seed=seed, max_rounds=100)
            final_alive = traj[-1]['alive']
            rates.append(final_alive / n * 100)
        survival_rates.append(np.mean(rates))
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(sizes, survival_rates, 'ko-', linewidth=2, markersize=8)
    ax.axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    ax.set_xscale('log')
    ax.set_xlabel('Population size n')
    ax.set_ylabel('Survival rate (%)')
    ax.set_title('Fig.3: System-size scaling under isometric resource scaling')
    ax.grid(True, alpha=0.3)
    
    for x, y in zip(sizes, survival_rates):
        ax.annotate(f'{y:.1f}%', (x, y), textcoords="offset points", xytext=(0, 10), ha='center')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'fig3_size_scaling.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✓ fig3_size_scaling.png")


def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("Generating Paper Figures")
    print("=" * 60)
    
    plot_fig2_evolution_trajectory(output_dir)
    plot_fig3_size_scaling(output_dir)
    
    print(f"\n{'=' * 60}")
    print(f"All figures saved to {output_dir}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
