"""
gacha.py - 鸭鸭抽卡系统
纯 Python 实现，32种人格组合 + SSR/SR/R/N 稀有度
与 TS src/lib/gacha.ts 完全对齐
"""
import random
import json
import os

RARITY_WEIGHTS = {'N': 70, 'R': 25, 'SR': 4.5, 'SSR': 0.5}
MBTI_LIST = ['E', 'I']
THINKING_LIST = ['S', 'N']  # sensing vs intuition
DECISION_LIST = ['T', 'F']  # thinking vs feeling


def load_json(name: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), 'prompts', f'{name}.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_personality_labels() -> dict:
    return load_json('personality_labels')


def load_self_intros() -> dict:
    return load_json('self_intro')


def load_rare_titles() -> dict:
    """加载稀有称号列表，返回 key->{title, rarity} 映射"""
    raw = load_json('rare_titles')
    return {t['key']: {'title': t['title'], 'rarity': t.get('rarity', 'N')}
            for t in raw.get('titles', [])}


def weighted_choice(items: list, weights: list) -> str:
    """加权随机选择（对齐 TS weightedChoice）"""
    total = sum(weights)
    r = random.random() * total
    cumulative = 0
    for item, weight in zip(items, weights):
        cumulative += weight
        if r < cumulative:
            return item
    return items[-1]


def rarity_rank(r: str) -> int:
    return {'N': 1, 'R': 2, 'SR': 3, 'SSR': 4}.get(r, 0)


def merge_draw_and_title_rarity(draw_rarity: str, title_rarity: str) -> str:
    """
    抽卡稀有度与组合称号配置的稀有度取较高者（对齐 TS performDraw）。
    """
    if rarity_rank(title_rarity) > rarity_rank(draw_rarity):
        return title_rarity
    return draw_rarity


def _draw_once(pity_counter: int, ssr_pity_counter: int) -> tuple[str, bool]:
    """
    内部单抽逻辑（对齐 TS drawRarity）
    - SSR >= 100 → SR（保底触发，降级为SR）
    - SR >= 10 → R/SR/SSR 随机（保底触发）
    - 普通抽 → N/R/SR/SSR 随机
    """
    if ssr_pity_counter >= 100:
        # SSR保底触发 → SR（降级，对齐TS）
        return 'SR', True
    if pity_counter >= 10:
        # SR保底触发 → R/SR/SSR 70/25/5
        rarity = weighted_choice(['R', 'SR', 'SSR'], [70, 25, 5])
        return rarity, True
    # 普通抽卡
    rarity = weighted_choice(['N', 'R', 'SR', 'SSR'], [70, 25, 4.5, 0.5])
    return rarity, False


def update_pity(rarity: str, pity_counter: int, ssr_pity_counter: int) -> tuple[int, int]:
    """
    根据抽卡结果更新保底计数器（对齐 TS updatePity）
    - SSR: 全部归零
    - SR: pity归零，ssr_pity +1
    - N/R: pity +1，ssr_pity +1
    """
    if rarity == 'SSR':
        return 0, 0
    elif rarity == 'SR':
        return 0, ssr_pity_counter + 1
    else:
        return pity_counter + 1, ssr_pity_counter + 1


def make_mbti() -> tuple[str, str, str]:
    social = random.choice(MBTI_LIST)
    thinking = random.choice(THINKING_LIST)
    decision = random.choice(DECISION_LIST)
    return social, thinking, decision


def calculate_title(attribute: str, social: str, thinking: str, decision: str) -> tuple[str, str]:
    """
    计算称号和稀有度（对齐 TS calculateTitle）
    级联匹配：4维 → 3维 → 2维 → 1维
    返回 (title, rarity)
    """
    titles = load_rare_titles()
    full_key = f'{attribute}-{social}-{thinking}-{decision}'
    dim3_key = f'{attribute}-{social}-{thinking}'
    dim2_key = f'{attribute}-{social}'
    dim1_key = attribute

    for key in [full_key, dim3_key, dim2_key, dim1_key]:
        if key in titles:
            info = titles[key]
            return info['title'], info.get('rarity', 'N')

    # 默认称号
    defaults = {'呆萌': '小太阳', '叛逆': '独行侠', '睿智': '智多星', '魅力': '万人迷'}
    return defaults.get(attribute, '鸭鸭'), 'N'


def perform_draw(pity_counter: int, ssr_pity_counter: int,
                 fixed_attribute: str = None) -> dict:
    """
    执行一次完整抽卡（对齐 TS performDraw）
    返回: {rarity, title, attribute, social, thinking, decision,
           mbti_key, personality_label, is_pity,
           new_pity_counter, new_ssr_pity_counter}
    """
    # 1. 根据保底决定稀有度
    rarity, is_pity = _draw_once(pity_counter, ssr_pity_counter)

    # 2. 决定属性
    attributes = ['呆萌', '叛逆', '睿智', '魅力']
    attribute = fixed_attribute or random.choice(attributes)

    # 3. 决定人格维度
    social, thinking, decision = make_mbti()
    mbti_key = f'{social}-{thinking}-{decision}'

    # 4. 查人格标签
    labels = load_personality_labels()
    personality_label = labels.get(f'{attribute}-{mbti_key}', mbti_key)

    # 5. 查稀有称号（TS calculateTitle 逻辑：取 rarity 与组合rarity 的更高者）
    title, title_rarity = calculate_title(attribute, social, thinking, decision)

    # 6. 抽卡稀有度与称号稀有度合并为最终展示稀有度
    final_rarity = merge_draw_and_title_rarity(rarity, title_rarity)
    final_title = title

    # 7. 更新保底
    new_pity, new_ssr = update_pity(rarity, pity_counter, ssr_pity_counter)

    return {
        'rarity': final_rarity,
        'title': final_title,
        'attribute': attribute,
        'social': social,
        'thinking': thinking,
        'decision': decision,
        'mbti_key': mbti_key,
        'personality_label': personality_label,
        'is_pity': is_pity,
        'new_pity_counter': new_pity,
        'new_ssr_pity_counter': new_ssr,
    }


def get_rarity_emoji(rarity: str) -> str:
    return {'N': '🦆', 'R': '🦆', 'SR': '🦢', 'SSR': '🦚'}.get(rarity, '🦆')


def format_draw_result(d: dict) -> str:
    emoji = get_rarity_emoji(d['rarity'])
    rarity_name = {'N': '普通', 'R': '稀有', 'SR': '超稀有', 'SSR': '极稀有'}.get(d['rarity'], '')
    personality = d.get('personality_label', d.get('mbti_key', ''))
    campus = d.get('campus', '')
    return (f"{emoji} {rarity_name} — 【{d['attribute']}】{personality}\n"
            f"🏷️ 称号：{d['title']}\n"
            f"📍 校区：{campus}")
