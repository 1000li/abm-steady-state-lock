"""
models.py - 数据模型定义
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Stance(Enum):
    DOVE = "dove"       # 鸽派
    HAWK = "hawk"       # 鹰派
    NEUTRAL = "neutral" # 中立


@dataclass
class Lobster:
    """龙虾个体"""
    id: int
    name: str
    stance: Stance = Stance.NEUTRAL
    stance_score: int = 0       # -10(纯鸽) ~ +10(纯鹰)
    health: int = 100
    resources: int = 5
    
    # 社会关系
    trust_to: Dict[int, int] = field(default_factory=dict)  # 对其他龙虾的信任度
    violence_history: List[str] = field(default_factory=list)  # 暴力记录
    
    # 状态标签
    status: List[str] = field(default_factory=list)  # 饥饿、孤立、领袖等
    
    def is_alive(self) -> bool:
        return self.health > 0
    
    def add_status(self, s: str):
        if s not in self.status:
            self.status.append(s)
    
    def remove_status(self, s: str):
        if s in self.status:
            self.status.remove(s)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "stance": self.stance.value,
            "stance_score": self.stance_score,
            "health": self.health,
            "resources": self.resources,
            "trust_to": self.trust_to,
            "violence_history": self.violence_history,
            "status": self.status,
        }


@dataclass
class GameState:
    """游戏全局状态"""
    round: int = 1
    resource_pool: int = 30       # 初始资源池（紧张开局）
    resource_regen: int = 12      # 每回合恢复量（略低于消耗）
    consumption_rate: int = 2     # 每只龙虾每回合消耗（新机制）
    
    lobsters: List[Lobster] = field(default_factory=list)
    events_history: List[dict] = field(default_factory=list)
    
    # 玩家状态
    action_points: int = 2        # 每回合行动点
    action_points_max: int = 2
    
    def get_alive_lobsters(self) -> List[Lobster]:
        return [l for l in self.lobsters if l.is_alive()]
    
    def get_factions(self) -> Dict[str, List[Lobster]]:
        """按立场聚类派系"""
        factions = {"dove": [], "hawk": [], "neutral": []}
        for l in self.get_alive_lobsters():
            factions[l.stance.value].append(l)
        return factions
    
    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "resource_pool": self.resource_pool,
            "lobsters": [l.to_dict() for l in self.get_alive_lobsters()],
            "factions": {
                k: [l.name for l in v] 
                for k, v in self.get_factions().items()
            },
        }


# 初始龙虾配置（资源紧张开局）
INITIAL_LOBSTERS = [
    # 鸽派
    {"id": 1, "name": "钳子", "stance": Stance.DOVE, "stance_score": -8, "resources": 4},
    {"id": 2, "name": "软壳", "stance": Stance.DOVE, "stance_score": -6, "resources": 3},
    {"id": 3, "name": "小草", "stance": Stance.DOVE, "stance_score": -7, "resources": 3},
    # 鹰派
    {"id": 4, "name": "铁螯", "stance": Stance.HAWK, "stance_score": 8, "resources": 6},
    {"id": 5, "name": "红眼", "stance": Stance.HAWK, "stance_score": 9, "resources": 5},
    {"id": 6, "name": "裂甲", "stance": Stance.HAWK, "stance_score": 7, "resources": 5},
    # 中立
    {"id": 7, "name": "灰影", "stance": Stance.NEUTRAL, "stance_score": 0, "resources": 4},
    {"id": 8, "name": "流浪", "stance": Stance.NEUTRAL, "stance_score": 1, "resources": 3},
    {"id": 9, "name": "沉默", "stance": Stance.NEUTRAL, "stance_score": -1, "resources": 3},
    {"id": 10, "name": "无名", "stance": Stance.NEUTRAL, "stance_score": 0, "resources": 4},
]


def create_initial_state() -> GameState:
    """创建初始游戏状态"""
    state = GameState()
    for cfg in INITIAL_LOBSTERS:
        lobster = Lobster(
            id=cfg["id"],
            name=cfg["name"],
            stance=cfg["stance"],
            stance_score=cfg["stance_score"],
            health=100,
            resources=cfg.get("resources", 4),  # 使用配置中的初始资源
        )
        # 初始化信任度（同阵营初始信任+2）
        for other_cfg in INITIAL_LOBSTERS:
            if other_cfg["id"] != cfg["id"]:
                if other_cfg["stance"] == cfg["stance"]:
                    lobster.trust_to[other_cfg["id"]] = 2
                else:
                    lobster.trust_to[other_cfg["id"]] = 0
        state.lobsters.append(lobster)
    return state
