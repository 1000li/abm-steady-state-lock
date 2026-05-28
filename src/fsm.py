"""
fsm.py - 有限状态机逻辑 v0.4
新机制：概率资源获取 + 风险鹰派攻击
"""
import random
import math
from typing import List, Tuple, Dict
from models import Lobster, GameState, Stance

# ============ 机制参数（可配置）============
# 默认值 = 当前v0.8-Scheme E机制参数
# 参数扫描/消融实验可通过 mechanism_params 覆盖

DEFAULT_MECHANISM_PARAMS = {
    # --- 饿急攻击 (Desperate Attack) ---
    "desperate_attack_enabled": True,
    "desperate_attack_prob": 0.5,
    "desperate_attack_success_score": 5,
    "desperate_attack_fail_score": 2,

    # --- 连续绝望 (Consecutive Starvation) ---
    "consecutive_starvation_enabled": True,
    "starvation_to_hawk_prob": 0.9,
    "starvation_to_hawk_score": 3,
    "consecutive_starvation_threshold": 3,
    "consecutive_starvation_score": 5,

    # --- 相对剥夺 (Relative Deprivation) ---
    "relative_deprivation_enabled": True,
    "relative_deprivation_threshold": 8,
    "relative_deprivation_prob": 0.4,
    "relative_deprivation_score": 2,
    "relative_deprivation_self_resources": 3,

    # --- 被掠夺反应 (Being Attacked) ---
    "attacked_to_hawk_prob": 0.8,
    "attacked_to_hawk_score": 2,

    # --- 成功分享 (Successful Sharing) ---
    "sharing_reinforce_prob": 0.9,
    "sharing_reinforce_score": -2,

    # --- 成功掠夺 (Successful Raiding) ---
    "raiding_reinforce_prob": 0.85,
    "raiding_reinforce_score": 2,

    # --- 攻击失败 (Attack Failure) ---
    "attack_failure_reflect_prob": 0.6,
    "attack_failure_reflect_score": -1,

    # --- 见证死亡 (Witness Death) ---
    "death_witness_extreme_prob": 0.7,
    "death_witness_dove_score": -1,
    "death_witness_hawk_score": 1,

    # --- 攻击选择性 (Attack Selectivity) ---
    "hawk_target_non_hawk_first": True,
    "hawk_vs_hawk_penalty": 0.70,
}


def _get_param(params: dict, key: str, default):
    """安全获取参数，支持部分覆盖"""
    if params is None:
        return default
    return params.get(key, default)


# 游戏常量
CONSUMPTION_PER_TURN = 2      # 每回合消耗资源
HUNGER_DAMAGE = 20            # 饥饿扣血
HEAL_RATIO = 5                # 1资源 = 5生命值
VIOLENCE_DAMAGE = 10          # 暴力冲突伤害
RESOURCE_REGEN = 10           # 每回合资源池恢复


def resolve_turn(state: GameState, player_actions: List[dict], mechanism_params: dict = None) -> Tuple[GameState, List[str]]:
    """
    执行一个完整的回合
    mechanism_params: 可选的机制参数覆盖字典（用于参数扫描/消融实验）
    返回: (新状态, 事件列表)
    """
    events = []
    lobsters = state.get_alive_lobsters()

    # 将机制参数附加到state上，供子函数使用
    state._mechanism_params = mechanism_params

    # ===== 阶段1: 玩家干预 =====
    for action in player_actions:
        event = execute_player_action(state, action)
        if event:
            events.append(event)

    # ===== 阶段2: 资源池恢复 =====
    # 优先使用state中的配置，否则使用默认值
    regen = getattr(state, 'resource_regen', RESOURCE_REGEN)
    state.resource_pool += regen

    # ===== 阶段3: 资源消耗结算（每只龙虾必须消耗2单位） =====
    # 新机制：所有个体概率获取公共池资源，数值越好概率越高
    import random

    # 收集所有需要补充资源的个体
    needy_lobsters = []
    for lobster in list(lobsters):
        if not lobster.is_alive():
            continue

        needed = CONSUMPTION_PER_TURN

        # 1. 先用自身储备
        if lobster.resources >= needed:
            lobster.resources -= needed
            lobster.remove_status("饥饿")
            lobster.remove_status("濒死")
        else:
            # 自身不够，计算缺口
            shortfall = needed - lobster.resources
            lobster.resources = 0
            needy_lobsters.append((lobster, shortfall))

    # 2. 公共池资源概率分配（强者优先的概率获取）
    if needy_lobsters and state.resource_pool > 0:
        # 随机打乱顺序（去除顺序歧视）
        random.shuffle(needy_lobsters)

        # 计算每个个体的实力（资源+健康度）
        total_power = 0
        lobster_powers = []
        for lobster, shortfall in needy_lobsters:
            power = lobster.resources * 0.3 + lobster.health * 0.7
            power = max(0.1, power)  # 保底0.1避免除零
            lobster_powers.append((lobster, shortfall, power))
            total_power += power

        # 概率获取资源
        for lobster, shortfall, power in lobster_powers:
            if state.resource_pool <= 0:
                break

            # 成功概率 = 自身实力 / (总实力 + 资源池调节因子)
            # 资源池越充足，整体成功率越高
            pool_factor = min(1.0, state.resource_pool / (len(needy_lobsters) * 2))
            success_prob = (power / total_power) * pool_factor * len(needy_lobsters)
            success_prob = min(0.9, max(0.1, success_prob))  # 限制在10%-90%

            if random.random() < success_prob:
                # 成功获取：强者拿更多，但有上限
                base_amount = min(shortfall, state.resource_pool)
                bonus = int((power / total_power) * state.resource_pool * 0.5)  # 强者bonus
                acquire_amount = min(base_amount + bonus, shortfall * 2)  # 最多拿需求的两倍
                acquire_amount = min(acquire_amount, state.resource_pool)  # 不超过剩余

                state.resource_pool -= acquire_amount
                lobster.resources += acquire_amount

                if acquire_amount >= shortfall:
                    lobster.remove_status("饥饿")
                    if lobster.health > 30:
                        lobster.remove_status("濒死")

                events.append(f"{lobster.name}成功获取{acquire_amount}资源（成功率{success_prob:.0%}）")
            else:
                # 获取失败
                events.append(f"{lobster.name}争夺资源失败（成功率{success_prob:.0%}）")

    # 3. 还缺资源的个体扣生命值
    for lobster, shortfall in [(l, s) for l, s in needy_lobsters if l.resources < CONSUMPTION_PER_TURN]:
        needed = CONSUMPTION_PER_TURN - lobster.resources
        damage = needed * HUNGER_DAMAGE
        lobster.health -= damage
        lobster.add_status("饥饿")
        events.append(f"{lobster.name}缺乏资源，生命-{damage}")

        if lobster.health <= 30:
            lobster.add_status("濒死")

    # ===== 阶段4: 行为阶段（鹰派掠夺/鸽派分享） =====
    # 鹰派优先行动（按stance_score排序）
    sorted_lobsters = sorted(lobsters, key=lambda x: x.stance_score, reverse=True)

    # 记录鹰派成功掠夺用于立场更新
    hawk_success_events = []

    for lobster in sorted_lobsters:
        if not lobster.is_alive() or "隔离" in lobster.status:
            continue

        if lobster.stance == Stance.HAWK:
            event, success = hawk_action(lobster, lobsters, events, mechanism_params)
            if event:
                events.append(event)
                if success:
                    hawk_success_events.append(lobster.id)

    # 鸽派行动
    for lobster in sorted_lobsters:
        if not lobster.is_alive() or "隔离" in lobster.status:
            continue

        if lobster.stance == Stance.DOVE:
            event = dove_action(lobster, state, lobsters)
            if event:
                events.append(event)

    # 【方案E】饿急攻击：绝境鸽派尝试暴力
    if _get_param(mechanism_params, "desperate_attack_enabled", True):
        for lobster in sorted_lobsters:
            if not lobster.is_alive() or "隔离" in lobster.status:
                continue

            # 鸽派且资源=0且濒死 → 概率尝试攻击
            if (lobster.stance == Stance.DOVE and
                lobster.resources == 0 and
                "濒死" in lobster.status):

                desperate_prob = _get_param(mechanism_params, "desperate_attack_prob", 0.5)
                if random.random() < desperate_prob:
                    event, success = hawk_action(lobster, lobsters, events, mechanism_params)
                    if event:
                        events.append(event)
                        if success:
                            score = _get_param(mechanism_params, "desperate_attack_success_score", 5)
                            lobster.stance_score = min(10, lobster.stance_score + score)
                            events.append(f"💀 {lobster.name}饿急攻击成功，彻底觉醒为鹰派")
                        else:
                            score = _get_param(mechanism_params, "desperate_attack_fail_score", 2)
                            lobster.stance_score = min(10, lobster.stance_score + score)
                            events.append(f"⚠️ {lobster.name}饿急攻击失败，但记住了暴力")

    # ===== 阶段5: 生命值恢复（资源溢出转换） =====
    # 新机制：允许生命值超过100，上限150（溢出转换）
    MAX_HEALTH = 150  # 生命值上限从100提高到150

    for lobster in lobsters:
        if not lobster.is_alive():
            continue

        # 资源转换为生命值（允许溢出超过100）
        if lobster.resources > 0 and lobster.health < MAX_HEALTH:
            # 计算可转换量（更积极的转换）
            max_heal = (MAX_HEALTH - lobster.health) // HEAL_RATIO
            # 保留至少2单位资源，其余可用于治疗
            available = max(0, lobster.resources - 2)
            heal_amount = min(max_heal, available)

            if heal_amount > 0:
                lobster.resources -= heal_amount
                lobster.health = min(MAX_HEALTH, lobster.health + heal_amount * HEAL_RATIO)

                if lobster.health > 100:
                    events.append(f"{lobster.name}资源溢出转换，生命值突破上限达到{lobster.health}")
                else:
                    events.append(f"{lobster.name}消耗资源恢复了生命")

                if lobster.health > 30:
                    lobster.remove_status("濒死")

    # ===== 阶段6: 立场动态变化 =====
    # 【消融实验】支持完全跳过立场更新
    skip_stance = _get_param(mechanism_params, "skip_stance_update", False)
    if not skip_stance:
        for lobster in lobsters:
            if not lobster.is_alive():
                continue

            old_stance = lobster.stance
            update_stance(lobster, events, hawk_success_events, lobsters, mechanism_params)
            if lobster.stance != old_stance:
                events.append(f"{lobster.name}从{old_stance.value}变成了{lobster.stance.value}")

    # ===== 阶段7: 死亡检查 + 资源回收 =====
    for lobster in list(lobsters):
        if lobster.health <= 0 and lobster.is_alive():
            # 回收资源到公共池
            if lobster.resources > 0:
                state.resource_pool += lobster.resources
                events.append(f"💀 {lobster.name}死亡，其{lobster.resources}单位资源回归公共池")
                lobster.resources = 0
            else:
                events.append(f"💀 {lobster.name}死亡")
            lobster.health = 0

    # 记录历史
    state.events_history.append({
        "round": state.round,
        "events": events.copy(),
        "lobster_count": len(state.get_alive_lobsters()),
    })

    # 回合结束
    state.round += 1
    state.action_points = state.action_points_max

    return state, events


def execute_player_action(state: GameState, action: dict) -> str:
    """执行玩家干预，返回事件描述"""
    action_type = action.get("type")
    target_id = action.get("target_id")

    if action_type == "execute":
        target = find_lobster_by_id(state, target_id)
        if target and target.is_alive():
            target.health = 0
            return f"🔪 玩家处决了{target.name}"

    elif action_type == "feed":
        amount = action.get("amount", 15)
        state.resource_pool += amount
        return f"🍖 玩家投喂，资源池+{amount}"

    elif action_type == "isolate":
        target = find_lobster_by_id(state, target_id)
        if target and target.is_alive():
            target.add_status("隔离")
            return f"🔒 玩家隔离了{target.name}"

    return ""


def hawk_action(lobster: Lobster, all_lobsters: List[Lobster], events: List[str], mechanism_params: dict = None) -> Tuple[str, bool]:
    """
    鹰派行为：抢夺资源
    mechanism_params: 可选的机制参数覆盖字典
    返回: (事件描述, 是否成功掠夺)
    """
    # 找目标（存活、非隔离、非自己）
    targets = [l for l in all_lobsters
               if l.id != lobster.id and l.is_alive() and "隔离" not in l.status]
    
    if not targets:
        return "", False
    
    # 分离目标为两组：非鹰派（鸽/中立）和鹰派
    non_hawk_targets = [t for t in targets if t.stance != Stance.HAWK]
    hawk_targets = [t for t in targets if t.stance == Stance.HAWK]
    
    candidates = []
    
    # 先评估非鹰派目标
    for target in non_hawk_targets:
        success_prob, expected_gain, max_steal, counter_damage = _calc_attack_metrics(
            lobster, target, False, mechanism_params
        )
        candidates.append((target, success_prob, expected_gain, max_steal, counter_damage, "non_hawk"))
    
    # 鹰派优先攻击非鹰派（可配置）
    target_non_hawk_first = _get_param(mechanism_params, "hawk_target_non_hawk_first", True)
    best_non_hawk_gain = max([c[2] for c in candidates], default=-999)
    
    if (not target_non_hawk_first) or (best_non_hawk_gain < 0.3 and hawk_targets):
        for target in hawk_targets:
            success_prob, expected_gain, max_steal, counter_damage = _calc_attack_metrics(
                lobster, target, True, mechanism_params
            )
            candidates.append((target, success_prob, expected_gain, max_steal, counter_damage, "hawk"))
    
    if not candidates:
        return "", False
    
    # 选择预期收益最高的目标
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    # 如果预期收益太低，放弃攻击
    if candidates[0][2] < -0.5 and random.random() < 0.6:
        return f"⚠️ {lobster.name}评估风险后放弃攻击", False

    target, success_prob, _, max_steal, counter_damage, target_type = candidates[0]

    # 执行攻击判定
    if random.random() < success_prob:
        # ===== 攻击成功 =====
        power_diff = success_prob - 0.5
        steal = min(max_steal, target.resources)

        target.resources -= steal
        lobster.resources += steal

        # 伤害（5-18）
        damage = 8 + int(power_diff * 20)
        damage = max(5, min(18, damage))
        target.health -= damage

        # 关系变化
        target.trust_to[lobster.id] = target.trust_to.get(lobster.id, 0) - 6
        lobster.trust_to[target.id] = lobster.trust_to.get(target.id, 0) - 3

        # 记录暴力
        lobster.violence_history.append(f"掠夺了{target.name}")
        target.violence_history.append(f"被{lobster.name}掠夺")

        target_type_str = "非鹰派" if target_type == "non_hawk" else "同类"

        # 触发事件用于立场更新
        events.append(f"__HAWK_SUCCESS__:{lobster.id}:{target.id}")

        return f"⚔️ {lobster.name}掠夺{target.name}({target_type_str})，抢夺{steal}资源，造成{damage}伤害", True
    else:
        # ===== 攻击失败 =====
        actual_counter = int(counter_damage * (0.8 + random.random() * 0.4))
        actual_counter = min(actual_counter, 10)
        lobster.health -= actual_counter

        cost = min(1, lobster.resources)
        lobster.resources -= cost

        target.trust_to[lobster.id] = target.trust_to.get(lobster.id, 0) - 4
        lobster.trust_to[target.id] = lobster.trust_to.get(target.id, 0) - 2

        return f"🛡️ {lobster.name}攻击{target.name}失败，遭反击-{actual_counter}生命，消耗{cost}资源", False


def _calc_attack_metrics(lobster: Lobster, target: Lobster, is_hawk_target: bool, mechanism_params: dict = None) -> Tuple[float, float, int, int]:
    """计算攻击指标，返回: (成功率, 预期收益, 最大掠夺量, 反击伤害)
    mechanism_params: 可选的机制参数覆盖字典
    """
    # 计算攻击实力
    atk_power = lobster.resources * 0.3 + lobster.health * 0.5 + lobster.stance_score * 0.3
    def_power = target.resources * 0.3 + target.health * 0.5

    # 鹰派战斗经验加成
    if lobster.stance == Stance.HAWK:
        atk_power *= 1.15

    # 受伤惩罚
    if target.health < 30:
        def_power *= 0.85

    # 成功概率
    power_diff = atk_power - def_power
    success_prob = 1 / (1 + math.exp(-power_diff / 30))
    success_prob = max(0.30, min(0.95, success_prob))

    # 【关键】攻击鹰派时成功率降低（可配置）
    if is_hawk_target:
        penalty = _get_param(mechanism_params, "hawk_vs_hawk_penalty", 0.70)
        success_prob *= penalty
        success_prob = max(0.20, success_prob)  # 保底20%

    # 预期掠夺量
    expected_steal = min(2 + int((success_prob - 0.5) * 3), target.resources)

    # 反击伤害
    counter_damage = int((target.resources + target.health * 0.1) * 0.15)
    counter_damage = min(counter_damage, 8)

    # 预期收益
    expected_gain = success_prob * expected_steal - (1 - success_prob) * (1 + counter_damage * 0.1)

    return success_prob, expected_gain, expected_steal, counter_damage


def dove_action(lobster: Lobster, state: GameState, all_lobsters: List[Lobster]) -> str:
    """鸽派行为：分享资源给需要帮助的同类（加入随机性）"""
    # 找需要帮助的鸽派同伴
    candidates = []
    for other in all_lobsters:
        if other.id == lobster.id or not other.is_alive() or "隔离" in other.status:
            continue
        # 只帮鸽派或中立偏鸽的，不帮鹰派
        if other.stance == Stance.HAWK:
            continue
        # 需要帮助：濒死或资源低于消耗需求
        if "濒死" in other.status or other.health < 30 or other.resources < CONSUMPTION_PER_TURN:
            trust = lobster.trust_to.get(other.id, 0)
            candidates.append((other, trust))

    if not candidates:
        return ""

    # 80%概率按信任度排序，20%概率随机选择（打破确定性）
    if random.random() < 0.8:
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected = candidates[0]
    else:
        selected = random.choice(candidates)

    other, trust = selected
    share_amount = 2  # 分享2单位

    # 优先从公共池取
    from_pool = min(share_amount, state.resource_pool)
    from_private = share_amount - from_pool

    # 如果公共池不够，检查自己是否愿意动用私人储备
    # 只有对信任度>=0的同伴才会动用自己的资源
    if from_private > 0 and trust < 0:
        return ""  # 不信任，只从公共池拿，不够就不帮

    if from_private > 0 and lobster.resources < from_private + 2:  # 至少留2单位自保
        return ""  # 自己储备不够，不帮

    # 执行分享
    state.resource_pool -= from_pool
    lobster.resources -= from_private
    other.resources += share_amount
    other.health = min(100, other.health + 3)  # 分享带来一点安慰

    # 增进关系（被帮助的一方更感激）
    other.trust_to[lobster.id] = other.trust_to.get(lobster.id, 0) + 4
    lobster.trust_to[other.id] = lobster.trust_to.get(other.id, 0) + 2

    source = ""
    if from_pool > 0 and from_private > 0:
        source = f"（公共池{from_pool}+自己{from_private}）"
    elif from_pool > 0:
        source = "（公共池）"
    else:
        source = "（私人储备）"

    return f"💚 {lobster.name}分享了资源给{other.name}{source}"


def update_stance(lobster: Lobster, events: List[str], hawk_success_ids: List[int], all_lobsters: List[Lobster], mechanism_params: dict = None):
    """
    根据经历更新立场（方案E：有效机制组合）
    mechanism_params: 可选的机制参数覆盖字典
    hawk_success_ids: 本回合成功掠夺的鹰派ID列表
    all_lobsters: 所有龙虾列表（用于计算鹰派平均资源）
    """
    # 【方案E】初始化连续濒死计数器
    if not hasattr(lobster, '_consecutive_starving'):
        lobster._consecutive_starving = 0

    # 濒死经历 → 变鹰（生存本能）
    starvation_prob = _get_param(mechanism_params, "starvation_to_hawk_prob", 0.9)
    if any(f"{lobster.name}缺乏资源" in e for e in events):
        lobster._consecutive_starving += 1
        if random.random() < starvation_prob:
            score = _get_param(mechanism_params, "starvation_to_hawk_score", 3)
            lobster.stance_score = min(10, lobster.stance_score + score)
    else:
        lobster._consecutive_starving = 0  # 重置计数器

    # 【方案E】连续濒死 → 彻底黑化
    if _get_param(mechanism_params, "consecutive_starvation_enabled", True):
        threshold = _get_param(mechanism_params, "consecutive_starvation_threshold", 3)
        if lobster._consecutive_starving >= threshold:
            score = _get_param(mechanism_params, "consecutive_starvation_score", 5)
            lobster.stance_score = min(10, lobster.stance_score + score)
            events.append(f"💀 {lobster.name}因长期饥饿而彻底绝望")
            lobster._consecutive_starving = 0  # 重置避免重复触发

    # 【方案E】相对剥夺感：鸽派看到鹰派大口吃肉 → 嫉妒变鹰
    if _get_param(mechanism_params, "relative_deprivation_enabled", True):
        if lobster.stance == Stance.DOVE:
            hawks = [l for l in all_lobsters if l.stance == Stance.HAWK and l.is_alive()]
            if hawks and lobster.resources < _get_param(mechanism_params, "relative_deprivation_self_resources", 3):
                avg_hawk_resources = sum(h.resources for h in hawks) / len(hawks)
                dep_threshold = _get_param(mechanism_params, "relative_deprivation_threshold", 8)
                if avg_hawk_resources > dep_threshold:
                    dep_prob = _get_param(mechanism_params, "relative_deprivation_prob", 0.4)
                    if random.random() < dep_prob:
                        score = _get_param(mechanism_params, "relative_deprivation_score", 2)
                        lobster.stance_score = min(10, lobster.stance_score + score)
                        events.append(f"{lobster.name}眼红鹰派的资源，心生嫉妒")

    # 被掠夺 → 变鹰（仇恨/防备）
    attacked_prob = _get_param(mechanism_params, "attacked_to_hawk_prob", 0.8)
    if any(f"被{lobster.name}掠夺" in e for e in events):
        if random.random() < attacked_prob:
            score = _get_param(mechanism_params, "attacked_to_hawk_score", 2)
            lobster.stance_score = min(10, lobster.stance_score + score)

    # 成功分享救助 → 巩固鸽派
    sharing_prob = _get_param(mechanism_params, "sharing_reinforce_prob", 0.9)
    if any(f"{lobster.name}分享了" in e for e in events):
        if random.random() < sharing_prob:
            score = _get_param(mechanism_params, "sharing_reinforce_score", -2)
            lobster.stance_score = max(-10, lobster.stance_score + score)

    # 成功掠夺 → 巩固鹰派
    raiding_prob = _get_param(mechanism_params, "raiding_reinforce_prob", 0.85)
    if lobster.id in hawk_success_ids:
        if random.random() < raiding_prob:
            score = _get_param(mechanism_params, "raiding_reinforce_score", 2)
            lobster.stance_score = min(10, lobster.stance_score + score)
            events.append(f"{lobster.name}因成功掠夺而更加坚信力量")

    # 攻击失败 → 反思
    failure_prob = _get_param(mechanism_params, "attack_failure_reflect_prob", 0.6)
    if any(f"{lobster.name}攻击" in e and "失败" in e for e in events):
        if random.random() < failure_prob:
            score = _get_param(mechanism_params, "attack_failure_reflect_score", -1)
            lobster.stance_score = max(-10, lobster.stance_score + score)
            events.append(f"{lobster.name}因攻击受挫而略有收敛")

    # 见证死亡 → 立场极端化
    witness_prob = _get_param(mechanism_params, "death_witness_extreme_prob", 0.7)
    if any("死亡" in e for e in events):
        if random.random() < witness_prob:
            if lobster.stance == Stance.DOVE:
                score = _get_param(mechanism_params, "death_witness_dove_score", -1)
                lobster.stance_score = max(-10, lobster.stance_score + score)
            elif lobster.stance == Stance.HAWK:
                score = _get_param(mechanism_params, "death_witness_hawk_score", 1)
                lobster.stance_score = min(10, lobster.stance_score + score)

    # 根据score更新stance分类
    if lobster.stance_score <= -3:
        lobster.stance = Stance.DOVE
    elif lobster.stance_score >= 3:
        lobster.stance = Stance.HAWK
    else:
        lobster.stance = Stance.NEUTRAL


def find_lobster_by_id(state: GameState, lobster_id: int) -> Lobster:
    """通过ID查找龙虾"""
    for l in state.lobsters:
        if l.id == lobster_id:
            return l
    return None


def get_recent_events(state: GameState, n: int = 5) -> List[dict]:
    """获取最近n回合的历史"""
    return state.events_history[-n:] if state.events_history else []
