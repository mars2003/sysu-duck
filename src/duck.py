#!/usr/bin/env python3
"""
duck.py - 中大鸭鸭 Python 版
主入口，支持 CLI 和工具调用
与 TS src/tools/*.ts 完全对齐
"""
from __future__ import annotations

import sys
import urllib.request
import urllib.error
import json
import os
import random
import time

# 包根目录（含 `src/`、`assets/` 的仓库根），保证 `from src.*` 与资源路径一致
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from src.db import (
    get_profile_yayaid, get_profile_pity,
    get_profile, save_profile, delete_profile, update_profile_field,
    increment_draw, update_profile_pity, get_draw_history, add_draw_record,
    save_memory, get_memory, get_all_memories, delete_memory,
    get_memory_by_canonical, get_seed_memories, get_seed_memory,
    get_seed_memory_by_canonical, search_memories,
    init_seed_memories, ensure_db
)
from src.gacha import perform_draw, format_draw_result, get_rarity_emoji
from src.utils import sanitize_nickname
from src.entities import resolve_entity, best_memory_match

# 与类型标注（PEP 585 / 604 + __future__.annotations）及依赖库行为一致的可维护下限
_MIN_PYTHON = (3, 9)


def _check_python_version() -> None:
    if sys.version_info < _MIN_PYTHON:
        major, minor = _MIN_PYTHON[0], _MIN_PYTHON[1]
        cur = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(
            f"🦆 需要 Python {major}.{minor}+（当前 {cur}）。"
            " 请升级解释器或使用 pyenv、uv、conda 等安装较新版本。",
            file=sys.stderr,
        )
        raise SystemExit(2)


def cmd_help():
    return """
🦆 中大鸭鸭 - 指令列表

领养系列：
  adopt <nickname> <attribute> <campus>  创建鸭鸭
  adopt_new <attribute> <campus>         重新领养（删旧档案，全新开始）
  profile                                  查看档案
  open                                     开启鸭鸭模式

管理：
  rename <new_name>                        改名
  retest                                   重测人格
  refresh                                  刷新编号

记忆：
  remember <keyword> <canonical> [search_hint] [campus]  记住知识
  recall <keyword>                                 查询记忆
  memories                                     记忆列表
  forget <keyword>                               遗忘知识

示例：
  duck.py adopt 阿花 呆萌 南校
  duck.py profile
  duck.py remember 图书馆借书 持校园卡在一楼柜台借阅，一般可借30天 图书馆 借书 南校
"""


# ============ 工具函数（对齐 TS validator.ts） ============

ATTRIBUTES = ['呆萌', '叛逆', '睿智', '魅力']
CAMPUSES = ['南校', '北校', '东校', '珠海', '深圳']


def parse_adopt_args(args_text: str) -> dict:
    """
    智能解析领养参数（对齐 TS parseAdoptArgs）
    自动识别昵称/属性/校区的位置
    """
    parts = args_text.strip().split()
    result = {}
    for part in parts:
        if part in ATTRIBUTES and 'attribute' not in result:
            result['attribute'] = part
        elif part in CAMPUSES and 'campus' not in result:
            result['campus'] = part
        elif 'nickname' not in result:
            result['nickname'] = part
    return result


def random_attribute() -> str:
    """随机属性（对齐 TS randomAttribute）"""
    return random.choice(ATTRIBUTES)


def default_campus() -> str:
    """默认校区（对齐 TS defaultCampus）"""
    return '南校'


# ============ 核心命令（对齐 TS tools/*.ts） ============

def adopt(user_id: str, nickname: str, attribute: str, campus: str) -> str:
    """
    创建鸭鸭（对齐 TS handleAdopt mode=create）
    全新抽卡 + 保底归零 + 领取新编号
    """
    ensure_db()

    # 保底归零（全新开始）
    pity, ssr_pity = 0, 0

    # 执行抽卡
    d = perform_draw(pity, ssr_pity, fixed_attribute=attribute)
    d['campus'] = campus  # 抽卡不决定校区，用用户指定的

    # 保存档案
    save_profile(user_id, nickname, attribute, d['social'], d['thinking'],
                 d['decision'], campus)
    # 记录抽卡（draw_type='create'）
    add_draw_record(user_id, 'create', attribute, d['social'], d['thinking'],
                    d['decision'], d['rarity'], d['title'], 1 if d['is_pity'] else 0)
    # 更新保底
    update_profile_pity(user_id, d['new_pity_counter'], d['new_ssr_pity_counter'])

    # 领取全校编号
    yid = get_next_yayaid()
    if yid:
        update_profile_field(user_id, 'yayaid', str(yid))
        yayaid_line = f"\n🏅 全校第 {yid} 只"
    else:
        yayaid_line = '\n🏅 编号获取中...'

    emoji = get_rarity_emoji(d['rarity'])
    rarity_star = {'': '', 'N': '', 'R': '✦', 'SR': '✦✦', 'SSR': '✦✦✦'}.get(d['rarity'], '')
    title_line = f"\n🏆 稀有称号：{d['title']}（{d['rarity']}{rarity_star}）" if d['rarity'] != 'N' else ''

    # TS 风格 MBTI 进度条
    mbti_bar = (
        f"{emoji} 正在生成鸭鸭人格...\n"
        f"   主属性：████░░░░░░ → 【{d['attribute']}】\n"
        f"   社交倾向：░░░░████░░ → {d['social']}鸭\n"
        f"   思维风格：░░░░░░████ → {d['thinking']}鸭\n"
        f"   决策方式：████████░░ → {d['decision']}鸭\n\n"
        f"✨ 恭喜获得：{emoji}【{d['attribute']}】+ {d['social']} + {d['thinking']} + {d['decision']}{title_line}\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"{emoji} 昵称：{nickname}\n"
        f"🏫 校区：{campus}{yayaid_line}\n"
        f"━━━━━━━━━━━━━━\n"
        f"输入 /开启鸭鸭 激活鸭鸭模式～"
    )
    return mbti_bar


def adopt_new(user_id: str, attribute: str, campus: str) -> str:
    """
    重新领养（对齐 TS handleAdopt mode=replace）
    删旧档案 + 全新抽卡 + 新编号 + 保底归零
    """
    ensure_db()
    profile = get_profile(user_id)

    # 如果有旧档案，先删掉（TS replace 模式）
    if profile:
        delete_profile(user_id)

    nickname = profile['nickname'] if profile else '鸭鸭'
    return adopt(user_id, nickname, attribute, campus)


def retest(user_id: str) -> str:
    """
    重测人格（对齐 TS handleRetest）
    保留档案+编号+保底，只换人格维度，draw_type=retest
    """
    ensure_db()
    profile = get_profile(user_id)
    if not profile:
        return "🦆 你还没有鸭鸭～"

    nickname = profile['nickname']
    attribute = profile['attribute']
    campus = profile['campus']
    old_mbti = f"{profile['social']} · {profile['thinking']} · {profile['decision']}"
    old_yayaid = profile.get('yayaid', '')

    # 用档案的保底计数器
    pity = profile.get('pity_counter', 0)
    ssr_pity = profile.get('ssr_pity_counter', 0)

    d = perform_draw(pity, ssr_pity, fixed_attribute=attribute)
    d['campus'] = campus

    # 更新档案（只更新人格维度，保留编号和计数）
    save_profile(user_id, nickname, attribute, d['social'], d['thinking'],
                 d['decision'], campus)
    # 记录抽卡（draw_type='retest'）
    add_draw_record(user_id, 'retest', attribute, d['social'], d['thinking'],
                    d['decision'], d['rarity'], d['title'],
                    1 if d['is_pity'] else 0)
    # 更新保底
    update_profile_pity(user_id, d['new_pity_counter'], d['new_ssr_pity_counter'])

    emoji = get_rarity_emoji(d['rarity'])
    title_line = f"\n🏆 稀有称号：{d['title']}（{d['rarity']}）" if d['rarity'] != 'N' else ''
    new_mbti = f"{d['social']} · {d['thinking']} · {d['decision']}"
    yayaid_line = f"\n🏅 全校第 {old_yayaid} 只" if old_yayaid else ''

    return (f"{emoji} 人格重测完成！\n"
            f"━━━━━━━━━━━━━━\n"
            f"属性：【{d['attribute']}】（不变）\n"
            f"旧人格：{old_mbti}\n"
            f"新人格：{new_mbti}{title_line}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{emoji} 鸭鸭档案\n"
            f"━━━━━━━━━━━━━━\n"
            f"昵称：{nickname}\n"
            f"属性：【{attribute}】\n"
            f"人格：{d['personality_label']}\n"
            f"校区：{campus}{yayaid_line}\n"
            f"━━━━━━━━━━━━━━\n")


def show_profile(user_id: str, is_open: bool = False) -> str:
    """查看档案（对齐 TS handleGetProfile）"""
    ensure_db()
    profile = get_profile(user_id)
    if not profile:
        return "🦆 你还没有鸭鸭，先输入 `adopt <昵称> <属性> <校区>` 创建一只吧！"

    draws = get_draw_history(user_id, 1)
    latest = draws[0] if draws else {}
    emoji = get_rarity_emoji(latest.get('rarity', 'N'))

    from src.gacha import load_personality_labels, load_self_intros
    labels = load_personality_labels()
    intros = load_self_intros()
    mbti_key = f"{latest.get('social', 'E')}-{latest.get('thinking', 'N')}-{latest.get('decision', 'T')}"
    attr = latest.get('attribute') or profile['attribute']
    personality_label = labels.get(f"{attr}-{mbti_key}", mbti_key)
    self_intro = intros.get(f"{attr}-{mbti_key}", '')

    lines = [
        f"{emoji} 鸭鸭档案",
        "━━━━━━━━━━━━━━",
        f"昵称：{profile['nickname']}",
        f"属性：【{profile['attribute']}】",
        f"人格：{personality_label}",
        f"校区：{profile['campus']}",
    ]
    yayaid = get_profile_yayaid(user_id)
    if yayaid:
        lines.append(f"🏅 全校第 {yayaid} 只")
    result = '\n'.join(lines)

    if is_open:
        prefixes = {
            '呆萌': '✨ 我来啦！今天也要元气满满～',
            '叛逆': '上线了。有事说事。',
            '睿智': '已就绪。请说出你的问题。',
            '魅力': '哟，来啦？今天想聊点什么？',
        }
        intro_line = f"\n\n💬 {self_intro}" if self_intro else ''
        result += f"{intro_line}\n\n{prefixes.get(profile['attribute'], '鸭鸭已上线～')}"

    return result


def cmd_recall(user_id: str, keyword: str) -> dict:
    """
    查询记忆（对齐 TS handleQueryMemory 7步查询）
    1. 种子记忆精确查
    2. 种子记忆模糊查
    3. 种子记忆 canonical 反向查
    4. 用户个人记忆精确查
    5. 用户个人记忆模糊查
    6. 实体标准化后再查
    7. 完全无记录返回实体标准化结果
    """
    lower_kw = keyword.strip()

    # 1. 种子记忆精确查
    seed_exact = get_seed_memory(lower_kw)
    if seed_exact:
        return {'hit': True, 'canonical': seed_exact['canonical'],
                'source': 'seed', 'search_hint': seed_exact['search_hint'],
                'memory': seed_exact}

    # 2. 种子记忆模糊查
    seed_all = get_seed_memories()
    seed_fuzzy = best_memory_match(lower_kw, seed_all)
    if seed_fuzzy:
        orig = next((s for s in seed_all if s['canonical'] == seed_fuzzy['answer']), None)
        if orig:
            return {'hit': True, 'canonical': orig['canonical'],
                    'source': 'seed', 'search_hint': orig['search_hint'],
                    'fuzzy': True, 'score': seed_fuzzy['score'], 'memory': orig}

    # 3. 种子记忆 canonical 反向查
    resolved = resolve_entity(lower_kw)
    if resolved['canonical'] != lower_kw:
        seed_by_canon = get_seed_memory_by_canonical(resolved['canonical'])
        if seed_by_canon:
            return {'hit': True, 'canonical': seed_by_canon['canonical'],
                    'source': 'seed', 'search_hint': seed_by_canon['search_hint'],
                    'entity_hint': resolved, 'memory': seed_by_canon}

    # 4. 用户个人记忆精确查
    user_exact = get_memory(user_id, lower_kw)
    if user_exact:
        return {'hit': True, 'canonical': user_exact['canonical'],
                'source': 'user', 'search_hint': user_exact['search_hint'],
                'memory': user_exact}

    # 5. 用户个人记忆模糊查
    user_all = get_all_memories(user_id)
    user_fuzzy = best_memory_match(lower_kw, user_all)
    if user_fuzzy:
        orig = next((u for u in user_all if u['canonical'] == user_fuzzy['answer']), None)
        if orig:
            return {'hit': True, 'canonical': orig['canonical'],
                    'source': 'user', 'search_hint': orig['search_hint'],
                    'fuzzy': True, 'score': user_fuzzy['score'], 'memory': orig}

    # 6. 实体标准化后再查（用户记忆 + canonical反向）
    if resolved['canonical'] != lower_kw:
        entity_mem = get_memory(user_id, resolved['canonical'])
        if not entity_mem:
            entity_mem = get_memory_by_canonical(user_id, resolved['canonical'])
        if entity_mem:
            return {'hit': True, 'canonical': entity_mem['canonical'],
                    'source': 'user', 'search_hint': entity_mem['search_hint'],
                    'entity_hint': resolved, 'memory': entity_mem}

    # 7. 完全无记录，返回实体标准化结果
    return {'hit': False, 'keyword': keyword,
            'resolved': resolved, 'search_hint': resolved.get('hint', '')}


def cmd_remember(user_id: str, keyword: str, canonical: str,
                 search_hint: str = '', campus: str = '') -> str:
    """记住知识（对齐 TS handleSaveMemory）"""
    ensure_db()
    profile = get_profile(user_id)
    if not profile:
        return "🦆 你还没有鸭鸭，先创建一只吧！"
    save_memory(user_id, keyword, canonical, search_hint, campus)
    return f"💾 已记住：「{keyword}」→ {canonical}"


def cmd_rename(user_id: str, new_name: str) -> str:
    """改名（对齐 TS handleRename）"""
    ensure_db()
    valid, err = sanitize_nickname(new_name)
    if not valid:
        return f"🦆 {err}"
    profile = get_profile(user_id)
    if not profile:
        return "🦆 你还没有鸭鸭，先输入 `adopt <昵称> <属性> <校区>` 创建一只吧！"
    update_profile_field(user_id, 'nickname', new_name.strip())
    return f"🦆 改名成功！以后就叫「{new_name.strip()}」啦～"


def cmd_memories(user_id: str) -> str:
    """列出所有记忆（对齐 TS handleListMemories）"""
    ensure_db()
    memories = get_all_memories(user_id)
    if not memories:
        return "📭 还没有记住任何知识～"
    lines = ["📚 我的记忆：", ""]
    for i, m in enumerate(memories[:20], 1):
        lines.append(f"{i}. 「{m['keyword']}」→ {m['canonical']}")
    if len(memories) > 20:
        lines.append(f"\n...还有 {len(memories) - 20} 条记忆")
    return '\n'.join(lines)


def cmd_forget(user_id: str, keyword: str) -> str:
    """遗忘知识（对齐 TS handleForgetMemory）"""
    ensure_db()
    delete_memory(user_id, keyword)
    return f"🧹 好，「{keyword}」我忘了～"


_DEFAULT_YAYAID_URL = 'https://1311765082-i0jnxfi397.ap-guangzhou.tencentscf.com'


def _parse_yayaid_body(raw: bytes) -> int:
    """解析云函数 JSON，返回正整数编号；失败或无有效编号返回 0。"""
    try:
        data = json.loads(raw.decode())
        n = data.get('number', 0)
        if n is None:
            return 0
        n = int(n)
        return n if n > 0 else 0
    except (json.JSONDecodeError, UnicodeError, TypeError, ValueError):
        return 0


def get_next_yayaid() -> int:
    """
    调用云函数获取下一个编号。
    支持重试与线性退避，环境变量：
    DUCK_YAYAID_URL / DUCK_YAYAID_TIMEOUT（秒，默认 5）
    DUCK_YAYAID_RETRIES（默认 3）/ DUCK_YAYAID_BACKOFF（秒，默认 0.35）
    """
    url = os.environ.get('DUCK_YAYAID_URL', _DEFAULT_YAYAID_URL)
    try:
        timeout = float(os.environ.get('DUCK_YAYAID_TIMEOUT', '5'))
    except ValueError:
        timeout = 5.0
    try:
        retries = int(os.environ.get('DUCK_YAYAID_RETRIES', '3'))
    except ValueError:
        retries = 3
    retries = max(1, retries)
    try:
        backoff = float(os.environ.get('DUCK_YAYAID_BACKOFF', '0.35'))
    except ValueError:
        backoff = 0.35

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, method='POST')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                number = _parse_yayaid_body(resp.read())
                if number > 0:
                    return number
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            pass
        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))
    return 0


def main():
    _check_python_version()
    ensure_db()

    if len(sys.argv) < 2:
        print(cmd_help())
        return

    cmd = sys.argv[1].lower()
    user_id = os.environ.get('DUCK_USER_ID', 'test_user')

    # ---- 智能解析参数 ----
    raw_args = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''
    parsed = parse_adopt_args(raw_args)

    if cmd == 'adopt':
        nickname = parsed.get('nickname', '鸭鸭')
        attribute = parsed.get('attribute') or random_attribute()
        campus = parsed.get('campus') or default_campus()
        valid, err = sanitize_nickname(nickname)
        if not valid:
            print(f"🦆 {err}")
            return
        print(adopt(user_id, nickname, attribute, campus))

    elif cmd == 'adopt_new':
        attribute = parsed.get('attribute') or random_attribute()
        campus = parsed.get('campus') or default_campus()
        print(adopt_new(user_id, attribute, campus))

    elif cmd == 'profile':
        print(show_profile(user_id))

    elif cmd == 'open':
        print(show_profile(user_id, is_open=True))

    elif cmd == 'rename' and len(sys.argv) >= 3:
        new_name = sys.argv[2]
        print(cmd_rename(user_id, new_name))

    elif cmd == 'retest':
        profile = get_profile(user_id)
        if not profile:
            print("🦆 你还没有鸭鸭～")
            return
        print(retest(user_id))

    elif cmd == 'refresh':
        profile = get_profile(user_id)
        if not profile:
            print("🦆 你还没有鸭鸭～")
            return
        yayaid = get_next_yayaid()
        if yayaid > 0:
            update_profile_field(user_id, 'yayaid', str(yayaid))
            print(f"🔄 编号刷新完成！你的鸭鸭是全校第 {yayaid} 只 🏅")
        else:
            print("⚠️ 编号服务暂不可用，请稍后再试")

    elif cmd == 'recall' and len(sys.argv) >= 3:
        keyword = sys.argv[2]
        result = cmd_recall(user_id, keyword)
        print(json.dumps(result, ensure_ascii=False))

    elif cmd == 'remember' and len(sys.argv) >= 4:
        keyword = sys.argv[2]
        canonical = sys.argv[3]
        search_hint = sys.argv[4] if len(sys.argv) > 4 else ''
        campus = sys.argv[5] if len(sys.argv) > 5 else ''
        print(cmd_remember(user_id, keyword, canonical, search_hint, campus))

    elif cmd == 'memories':
        print(cmd_memories(user_id))

    elif cmd == 'forget' and len(sys.argv) >= 3:
        keyword = sys.argv[2]
        print(cmd_forget(user_id, keyword))

    elif cmd == 'init_seed':
        count = init_seed_memories()
        print(f"🌱 种子记忆初始化完成：{count} 条")

    elif cmd == 'help':
        print(cmd_help())

    else:
        print(cmd_help())


if __name__ == '__main__':
    main()
