"""
utils.py - 通用工具函数
"""
import os
import re

# Python difflib.SequenceMatcher 的纯 Python 实现
def SequenceMatcher(a: str, b: str) -> dict:
    """
    返回 {ratio: float}，类似 Python difflib.SequenceMatcher
    """
    s1 = a.lower()
    s2 = b.lower()

    if s1 == s2:
        return {'ratio': lambda: 1.0}

    m = min(len(s1), len(s2))
    if m == 0:
        return {'ratio': lambda: 0.0}

    # 简单版：字符级相似度
    matches = 0
    i, j = 0, 0
    visited = set()

    while i < len(s1) and j < len(s2):
        if s1[i] == s2[j]:
            matches += 1
            i += 1
            j += 1
        else:
            found = False
            for ki in range(i + 1, min(i + 3, len(s1))):
                for lj in range(j + 1, min(j + 3, len(s2))):
                    key = f'{ki},{lj}'
                    if key not in visited and s1[ki] == s2[lj]:
                        visited.add(key)
                        i = ki
                        j = lj
                        found = True
                        break
                if found:
                    break
            if not found:
                break

    ratio = (2.0 * matches) / (len(s1) + len(s2))
    return {'ratio': lambda: round(ratio, 2)}


def fuzzy_match(text: str, keywords: list[str], threshold: float = 0.6) -> tuple[str, float] | None:
    """
    从关键词列表中找到与text最相似的，返回 (keyword, score) 或 None
    """
    best = None
    best_score = 0.0
    lower_text = text.strip().lower()

    for kw in keywords:
        if kw.lower() == lower_text:
            return (kw, 1.0)
        score = SequenceMatcher(lower_text, kw.lower())['ratio']()
        if score > threshold and score > best_score:
            best = (kw, score)
            best_score = score

    return best


def sanitize_nickname(name: str) -> tuple[bool, str]:
    """
    校验昵称合法性
    返回 (valid, error_message)
    """
    trimmed = name.strip()
    if not trimmed:
        return (False, '昵称不能为空')
    if len(trimmed) > 8:
        return (False, '昵称太长了，8个字以内哦')
    # 只允许中文、英文、数字
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9]+$', trimmed):
        return (False, '昵称只能包含中文、英文和数字')
    return (True, '')
