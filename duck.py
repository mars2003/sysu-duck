#!/usr/bin/env python3
"""
duck.py - 中大鸭鸭 Python 版
主入口，支持 CLI 和工具调用
"""
import sys
import urllib.request
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import (
    get_profile_yayaid, get_profile_pity,
    get_profile, save_profile, delete_profile, update_profile_field,
    increment_draw, update_profile_pity, get_draw_history, add_draw_record,
    save_memory, get_memory, get_all_memories, delete_memory,
    init_seed_memories, ensure_db
)
from gacha import perform_draw, format_draw_result, get_rarity_emoji
from utils import sanitize_nickname
from entities import resolve_entity, best_memory_match


def cmd_help():
    return """
🦆 中大鸭鸭 - 指令列表

领养系列：
  adopt <nickname> <attribute> <campus>  创建鸭鸭
  adopt_new <attribute> <campus>         重新领养
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


def adopt(user_id: str, nickname: str, attribute: str, campus: str):
    """创建鸭鸭 - 用户选择属性和校区，鸭鸭随机抽（保底贯通）"""
    ensure_db()

    # 读取当前保底计数器
    pity, ssr_pity = get_profile_pity(user_id)

    # 执行抽卡（读保底 → 抽 → 更新保底）
    d = perform_draw(pity, ssr_pity, fixed_attribute=attribute, fixed_campus=campus)

    # 保存档案
    save_profile(user_id, nickname, attribute, d['social'], d['thinking'],
                 d['decision'], campus)
    add_draw_record(user_id, d['rarity'], d['title'], attribute,
                   d['social'], d['thinking'], d['decision'], campus)
    increment_draw(user_id)
    update_profile_pity(user_id, d['new_pity_counter'], d['new_ssr_pity_counter'])

    # 领取全校编号
    yid = get_next_yayaid()
    if yid:
        update_profile_field(user_id, 'yayaid', str(yid))
        yayaid_line = f"\n🏅 全校第 {yid} 只"
    else:
        yayaid_line = ""

    result = format_draw_result(d)
    return f"🎉 恭喜！你抽到了：\n\n{result}{yayaid_line}\n\n✅ 鸭鸭「{nickname}」创建成功！"


def adopt_new(user_id: str, attribute: str, campus: str):
    """重新领养 - 等同TS replace模式：删旧档案、全新抽卡、领新编号"""
    ensure_db()
    profile = get_profile(user_id)

    # 如果有旧档案，先删掉
    if profile:
        delete_profile(user_id)

    # 全新领养（抽卡+新编号+保底归零）
    return adopt(user_id, profile['nickname'] if profile else '鸭鸭', attribute, campus)


def show_profile(user_id: str, is_open: bool = False):
    """查看档案"""
    ensure_db()
    profile = get_profile(user_id)
    if not profile:
        return "🦆 你还没有鸭鸭，先输入 `adopt <昵称> <属性> <校区>` 创建一只吧！"

    draws = get_draw_history(user_id, 1)
    latest = draws[0] if draws else {}
    emoji = get_rarity_emoji(latest.get('rarity', 'N'))

    from gacha import load_personality_labels, load_self_intros
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


def cmd_recall(user_id: str, keyword: str):
    """
    查询记忆（模糊匹配 + 实体识别）
    与 TS query_memory 对齐
    """
    ensure_db()

    # 1. 实体识别（entities.json）
    entity = resolve_entity(keyword)
    if entity['canonical'] != keyword:
        # 实体识别成功，用标准名查
        mem = get_memory(user_id, entity['canonical'])
        if mem:
            return {'hit': True, 'canonical': mem['canonical'],
                    'source': 'user', 'search_hint': entity.get('hint', ''),
                    'entity_hint': entity}

    # 2. 精确匹配用户记忆
    mem = get_memory(user_id, keyword)
    if mem:
        return {'hit': True, 'canonical': mem['canonical'],
                'source': 'user', 'search_hint': mem['search_hint']}

    # 3. 精确匹配种子记忆
    seed = get_memory('__seed__', keyword)
    if seed:
        return {'hit': True, 'canonical': seed['canonical'],
                'source': 'seed', 'search_hint': seed['search_hint']}

    # 4. 模糊匹配用户记忆
    all_user = get_all_memories(user_id)
    if all_user:
        best = best_memory_match(keyword, all_user)
        if best:
            return {'hit': True, 'canonical': best['answer'],
                    'source': 'user', 'search_hint': best['keyword'],
                    'fuzzy': True, 'score': best['score']}

    # 5. 模糊匹配种子记忆
    all_seed = get_all_memories('__seed__')
    if all_seed:
        best = best_memory_match(keyword, all_seed)
        if best:
            return {'hit': True, 'canonical': best['answer'],
                    'source': 'seed', 'search_hint': best['keyword'],
                    'fuzzy': True, 'score': best['score']}

    return {'hit': False, 'keyword': keyword}


def cmd_remember(user_id: str, keyword: str, canonical: str, search_hint: str = '', campus: str = ''):
    """记住知识"""
    ensure_db()
    save_memory(user_id, keyword, canonical, search_hint, campus)
    return f"💾 已记住：「{keyword}」→ {canonical}"


def cmd_rename(user_id: str, new_name: str):
    """改名（带校验）"""
    ensure_db()
    valid, err = sanitize_nickname(new_name)
    if not valid:
        return f"🦆 {err}"
    profile = get_profile(user_id)
    if not profile:
        return "🦆 你还没有鸭鸭，先输入 `adopt <昵称> <属性> <校区>` 创建一只吧！"
    update_profile_field(user_id, 'nickname', new_name.strip())
    return f"🦆 改名成功！以后就叫「{new_name.strip()}」啦～"


def cmd_memories(user_id: str):
    """列出所有记忆"""
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


def cmd_forget(user_id: str, keyword: str):
    """遗忘知识"""
    ensure_db()
    delete_memory(user_id, keyword)
    return f"🧹 好，「{keyword}」我忘了～"


def get_next_yayaid() -> int:
    """调用云函数获取下一个编号"""
    url = os.environ.get('DUCK_YAYAID_URL',
                         'https://1311765082-i0jnxfi397.ap-guangzhou.tencentscf.com')
    try:
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get('number', 0)
    except Exception:
        return 0


def main():
    ensure_db()

    if len(sys.argv) < 2:
        print(cmd_help())
        return

    cmd = sys.argv[1].lower()
    user_id = os.environ.get('DUCK_USER_ID', 'test_user')

    if cmd == 'adopt' and len(sys.argv) >= 5:
        nickname = sys.argv[2]
        attribute = sys.argv[3]
        campus = sys.argv[4]
        valid, err = sanitize_nickname(nickname)
        if not valid:
            print(f"🦆 {err}")
            return
        print(adopt(user_id, nickname, attribute, campus))

    elif cmd == 'adopt_new' and len(sys.argv) >= 4:
        attribute = sys.argv[2]
        campus = sys.argv[3]
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
        attribute = profile['attribute']
        campus = profile['campus']
        print(adopt_new(user_id, attribute, campus))

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
