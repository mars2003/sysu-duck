"""
gacha.py - 鸭鸭抽卡系统
纯 Python 实现，32种人格组合 + SSR/SR/R/N 稀有度 + 保底贯通
"""
import random
import json
import os

RARITY_WEIGHTS = {'N': 16, 'R': 12, 'SR': 2, 'SSR': 2}
MBTI_LIST = ['E', 'I']
THINKING_LIST = ['S', 'N']  # sensing vs intuition
DECISION_LIST = ['T', 'F']  # thinking vs feeling

def load_json(name: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), 'prompts', f'{name}.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def load_personality_labels():
    return load_json('personality_labels')

def load_self_intros():
    return load_json('self_intro')

def load_rare_titles():
    raw = load_json('rare_titles')
    # 构建 key -> title 映射: "呆萌-E-N-T" -> "反差萌达人"
    return {t['key']: t['title'] for t in raw.get('titles', [])}

def rarity_rank(r: str) -> int:
    return {'N': 1, 'R': 2, 'SR': 3, 'SSR': 4}.get(r, 0)

def _draw_once(pity_counter: int, ssr_pity_counter: int):
    """内部单抽逻辑，返回 (rarity, is_pity)"""
    if ssr_pity_counter >= 100:
        return 'SSR', True
    if pity_counter >= 10:
        return 'SR', True
    pool = []
    for r, w in RARITY_WEIGHTS.items():
        pool.extend([r] * w)
    rarity = random.choice(pool)
    return rarity, False

def update_pity(rarity: str, pity_counter: int, ssr_pity_counter: int):
    """根据抽卡结果更新保底计数器，返回 (new_pity, new_ssr_pity)"""
    if rarity == 'SSR':
        return 0, 0
    elif rarity == 'SR':
        return 0, ssr_pity_counter + 1
    else:
        return pity_counter + 1, ssr_pity_counter + 1

def make_mbti():
    social = random.choice(MBTI_LIST)
    thinking = random.choice(THINKING_LIST)
    decision = random.choice(DECISION_LIST)
    return social, thinking, decision

def perform_draw(pity_counter: int, ssr_pity_counter: int,
                 fixed_attribute: str = None, fixed_campus: str = None) -> dict:
    """
    执行一次完整抽卡（读保底 → 抽卡 → 更新保底 → 返回结果）
    与 TS performDraw 完全对齐
    返回: {rarity, title, attribute, social, thinking, decision, campus, mbti_key,
           personality_label, is_pity, new_pity_counter, new_ssr_pity_counter}
    """
    # 1. 根据保底决定稀有度
    rarity, is_pity = _draw_once(pity_counter, ssr_pity_counter)

    # 2. 决定属性（4选1，或用固定的）
    attributes = ['呆萌', '叛逆', '睿智', '魅力']
    attribute = fixed_attribute or random.choice(attributes)

    # 3. 决定人格维度
    social, thinking, decision = make_mbti()
    mbti_key = f'{social}-{thinking}-{decision}'

    # 4. 查人格标签
    labels = load_personality_labels()
    personality_label = labels.get(f'{attribute}-{mbti_key}', mbti_key)

    # 5. 查稀有称号（TS calculateTitle 逻辑：取 rarity 与组合rarity 的更高者）
    titles = load_rare_titles()
    title = titles.get(f'{attribute}-{mbti_key}', f'{attribute}鸭')

    # 6. 称号本身的稀有度
    title_rarity = {'N': 1, 'R': 2, 'SR': 3, 'SSR': 4}.get(rarity, 1)
    combo_rarity = 1  # N=1, R=2, SR=3, SSR=4

    # 7. 更新保底
    new_pity, new_ssr = update_pity(rarity, pity_counter, ssr_pity_counter)

    # 8. 校区
    if fixed_campus:
        campus = fixed_campus
    else:
        campuses = ['南校', '北校', '东校', '珠海', '深圳', '全校']
        campus = random.choice(campuses)

    return {
        'rarity': rarity,
        'title': title,
        'attribute': attribute,
        'social': social,
        'thinking': thinking,
        'decision': decision,
        'campus': campus,
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
    return f"{emoji} {rarity_name} — 【{d['attribute']}】{d['personality_label']}\n🏷️ 称号：{d['title']}\n📍 校区：{d['campus']}"
