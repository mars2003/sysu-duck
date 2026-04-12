"""
entities.py - 实体识别 + 模糊匹配
"""
import json
import os
from utils import SequenceMatcher, fuzzy_match

_entities_cache = None


def get_entities_path() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), 'config', 'entities.json'),
        os.path.join(os.path.dirname(__file__), '..', 'config', 'entities.json'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def load_entities() -> dict:
    global _entities_cache
    if _entities_cache is not None:
        return _entities_cache
    path = get_entities_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            _entities_cache = json.load(f)
    except Exception:
        _entities_cache = {}
    return _entities_cache


def resolve_entity(text: str) -> dict:
    """
    实体识别：将用户输入识别为标准实体
    返回 {canonical, hint, campus}
    """
    entities = load_entities()
    lowered = text.strip()

    # 1. 精确 alias 匹配
    for canonical, entry in entities.items():
        aliases = entry.get('aliases', [])
        if any(alias == lowered for alias in aliases):
            return {
                'canonical': canonical,
                'hint': entry.get('hint', ''),
                'campus': entry.get('campus', '')
            }

    # 2. 模糊 alias 匹配（相似度 > 0.75）
    best = None
    best_score = 0.0

    for canonical, entry in entities.items():
        for alias in entry.get('aliases', []):
            score = SequenceMatcher(lowered, alias)['ratio']()
            if score > 0.75 and score > best_score:
                best = {'canonical': canonical, 'hint': entry.get('hint', ''),
                        'campus': entry.get('campus', ''), 'score': score}
                best_score = score

        # 直接匹配 canonical 名
        score = SequenceMatcher(lowered, canonical)['ratio']()
        if score > 0.8 and score > best_score:
            best = {'canonical': canonical, 'hint': entry.get('hint', ''),
                    'campus': entry.get('campus', ''), 'score': score}
            best_score = score

    if best:
        return {'canonical': best['canonical'], 'hint': best['hint'], 'campus': best['campus']}

    # 3. 无匹配，返回原文
    return {'canonical': text, 'hint': '', 'campus': ''}


def best_memory_match(keyword: str, memories: list[dict]) -> dict | None:
    """
    从记忆列表中找到与关键词最相似的记录
    返回 {keyword, answer, score} 或 None
    """
    lowered = keyword.strip()

    for mem in memories:
        if mem.get('keyword', '').lower() == lowered:
            return {'keyword': mem['keyword'], 'answer': mem.get('answer', mem.get('canonical', '')), 'score': 1.0}

    best = None
    best_score = 0.0

    for mem in memories:
        mem_kw = mem.get('keyword', '')
        score = SequenceMatcher(lowered, mem_kw.lower())['ratio']()
        if score > 0.6 and score > best_score:
            best = {
                'keyword': mem_kw,
                'answer': mem.get('answer', mem.get('canonical', '')),
                'score': score
            }
            best_score = score

    return best if best and best_score >= 0.6 else None
