"""
utils.py - 通用工具函数
"""
from __future__ import annotations

import difflib
import re


def similarity_ratio(a: str, b: str) -> float:
    """
    两段文本的相似度 [0,1]，保留两位小数；使用标准库 difflib，比手写字符扫窗更稳健。
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio(), 2)


def SequenceMatcher(a: str, b: str) -> dict:
    """
    兼容旧调用：SequenceMatcher(a, b)['ratio']()
    """
    r = similarity_ratio(a, b)
    return {'ratio': (lambda v=r: v)}


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
