"""
gacha.py - 鸭鸭抽卡系统
纯 Python 实现，32种人格组合 + SSR/SR/R/N 稀有度
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
    return load_json('rare_titles')

def draw_once(total_draws: int, pity_counter: int, ssr_pity_counter: int):
    """单抽，返回 (rarity, is_pity)"""
    # SSR 保底：100抽必出
    if ssr_pity_counter >= 100:
        return 'SSR', True
    # SR 保底：10抽必出
    if pity_counter >= 10:
        return 'SR', True
    
    # 根据权重随机
    pool = []
    for r, w in RARITY_WEIGHTS.items():
        pool.extend([r] * w)
    rarity = random.choice(pool)
    return rarity, False

def update_pity(rarity: str, pity_counter: int, ssr_pity_counter: int):
    """更新保底计数器"""
    if rarity == 'SSR':
        return 0, 0
    elif rarity == 'SR':
        return 0, ssr_pity_counter + 1
    else:
        return pity_counter + 1, ssr_pity_counter + 1

def make_mbti():
    social = random.choice(MBTI_LIST)        # E or I
    thinking = random.choice(THINKING_LIST)   # S or N
    decision = random.choice(DECISION_LIST)   # T or F
    return social, thinking, decision

def draw_rarity() -> dict:
    """
    执行一次抽卡，返回完整档案
    返回: {
        rarity, title, attribute, social, thinking, decision, campus, mbti_key, personality_label
    }
    """
    # 先决定稀有度
    rarity, _ = draw_once(0, 0, 0)
    
    # 决定属性（4选1）
    attributes = ['呆萌', '叛逆', '睿智', '魅力']
    attribute = random.choice(attributes)
    
    # 决定 MBTI 人格
    social, thinking, decision = make_mbti()
    mbti_key = f'{social}-{thinking}-{decision}'
    
    # 查人格标签
    labels = load_personality_labels()
    personality_label = labels.get(f'{attribute}-{mbti_key}', mbti_key)
    
    # 查稀有称号
    titles = load_rare_titles()
    title = titles.get(f'{attribute}-{mbti_key}', f'{attribute}鸭')
    
    # 校区
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
        'personality_label': personality_label
    }

def get_rarity_emoji(rarity: str) -> str:
    return {'N': '🦆', 'R': '🦆', 'SR': '🦢', 'SSR': '🦚'}.get(rarity, '🦆')

def format_draw_result(d: dict) -> str:
    emoji = get_rarity_emoji(d['rarity'])
    rarity_name = {'N': '普通', 'R': '稀有', 'SR': '超稀有', 'SSR': '极稀有'}.get(d['rarity'], '')
    return f"{emoji} {rarity_name} — 【{d['attribute']}】{d['personality_label']}\n🏷️ 称号：{d['title']}\n📍 校区：{d['campus']}"
