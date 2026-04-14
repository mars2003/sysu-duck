"""
db.py - 鸭鸭数据库操作
纯 Python + sqlite3，内置无需安装额外模块
与 TS src/lib/db.ts 完全对齐
"""
import sqlite3
import os
import time
from typing import Optional, List, Dict, Any

_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.environ.get('DUCK_DB_PATH', os.path.join(_DB_DIR, 'duck.db'))

# update_profile_field 仅允许白名单字段，防止 SQL 注入与误改核心列
_PROFILE_UPDATABLE_FIELDS = frozenset({'nickname', 'yayaid'})


def ensure_db():
    """确保 data 目录和数据库存在"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    init_db()


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """初始化数据库表结构（对齐 TS schema）"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 鸭鸭档案表
    c.execute('''CREATE TABLE IF NOT EXISTS duck_profiles (
        user_id TEXT PRIMARY KEY,
        nickname TEXT NOT NULL DEFAULT '鸭鸭',
        attribute TEXT NOT NULL,
        social TEXT NOT NULL,
        thinking TEXT NOT NULL,
        decision TEXT NOT NULL,
        campus TEXT NOT NULL,
        total_draws INTEGER DEFAULT 0,
        pity_counter INTEGER DEFAULT 0,
        ssr_pity_counter INTEGER DEFAULT 0,
        yayaid TEXT DEFAULT '',
        created_at TEXT DEFAULT '',
        updated_at TEXT DEFAULT ''
    )''')

    # 抽卡记录表（对齐 TS draw_history schema）
    c.execute('''CREATE TABLE IF NOT EXISTS draw_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        draw_type TEXT NOT NULL,
        attribute TEXT NOT NULL,
        social TEXT NOT NULL,
        thinking TEXT NOT NULL,
        decision TEXT NOT NULL,
        rarity TEXT NOT NULL,
        title TEXT,
        is_pity INTEGER DEFAULT 0,
        created_at TEXT DEFAULT ''
    )''')

    # 会话记忆表
    c.execute('''CREATE TABLE IF NOT EXISTS conversation_memory (
        user_id TEXT NOT NULL,
        keyword TEXT NOT NULL,
        canonical TEXT NOT NULL,
        search_hint TEXT NOT NULL,
        campus TEXT NOT NULL DEFAULT '南校',
        learned_at TEXT DEFAULT '',
        PRIMARY KEY(user_id, keyword)
    )''')

    conn.commit()
    conn.close()


def ts():
    return time.strftime('%Y-%m-%d %H:%M:%S')


# ============ 档案操作 ============

def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM duck_profiles WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'user_id': row[0], 'nickname': row[1], 'attribute': row[2],
        'social': row[3], 'thinking': row[4], 'decision': row[5],
        'campus': row[6], 'total_draws': row[7], 'pity_counter': row[8],
        'ssr_pity_counter': row[9], 'yayaid': row[10] if len(row) > 10 else '',
        'created_at': row[11] if len(row) > 11 else '',
        'updated_at': row[12] if len(row) > 12 else ''
    }


def save_profile(user_id: str, nickname: str, attribute: str, social: str,
                thinking: str, decision: str, campus: str):
    """保存档案 - 存在时保留 yayaid 和抽卡计数"""
    conn = get_conn()
    c = conn.cursor()
    now = ts()

    c.execute('SELECT yayaid, total_draws, pity_counter, ssr_pity_counter FROM duck_profiles WHERE user_id=?', (user_id,))
    row = c.fetchone()

    if row:
        c.execute('''UPDATE duck_profiles SET
            nickname=?, attribute=?, social=?, thinking=?, decision=?, campus=?,
            updated_at=?
            WHERE user_id=?''',
            (nickname, attribute, social, thinking, decision, campus, now, user_id))
    else:
        c.execute('''INSERT INTO duck_profiles
            (user_id, nickname, attribute, social, thinking, decision, campus,
             total_draws, pity_counter, ssr_pity_counter, yayaid, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,0,0,0,'',?,?)''',
            (user_id, nickname, attribute, social, thinking, decision, campus, now, now))
    conn.commit()
    conn.close()


def delete_profile(user_id: str):
    """删除档案及所有相关数据（对齐 TS）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM duck_profiles WHERE user_id=?', (user_id,))
    c.execute('DELETE FROM draw_history WHERE user_id=?', (user_id,))
    c.execute('DELETE FROM conversation_memory WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()


def update_profile_field(user_id: str, field: str, value: str):
    if field not in _PROFILE_UPDATABLE_FIELDS:
        raise ValueError(f'不允许更新的字段: {field}')
    conn = get_conn()
    c = conn.cursor()
    c.execute(f'UPDATE duck_profiles SET {field}=?, updated_at=? WHERE user_id=?',
              (value, ts(), user_id))
    conn.commit()
    conn.close()


def get_profile_yayaid(user_id: str) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT yayaid FROM duck_profiles WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else ''


def increment_draw(user_id: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE duck_profiles SET total_draws=total_draws+1, updated_at=? WHERE user_id=?',
              (ts(), user_id))
    conn.commit()
    conn.close()


def update_profile_pity(user_id: str, pity_counter: int, ssr_pity_counter: int):
    """更新保底计数器"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE duck_profiles SET pity_counter=?, ssr_pity_counter=?, updated_at=? WHERE user_id=?',
              (pity_counter, ssr_pity_counter, ts(), user_id))
    conn.commit()
    conn.close()


def get_profile_pity(user_id: str) -> tuple[int, int]:
    """获取保底计数器"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT pity_counter, ssr_pity_counter FROM duck_profiles WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return (row[0] or 0, row[1] or 0)
    return (0, 0)


# ============ 抽卡记录（对齐 TS schema） ============

def get_draw_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM draw_history WHERE user_id=?
        ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
    rows = c.fetchall()
    conn.close()
    # 字段顺序: id, user_id, draw_type, attribute, social, thinking, decision, rarity, title, is_pity, created_at
    return [dict(zip(['id','user_id','draw_type','attribute','social','thinking',
                      'decision','rarity','title','is_pity','created_at'], r)) for r in rows]


def add_draw_record(user_id: str, draw_type: str, attribute: str,
                    social: str, thinking: str, decision: str,
                    rarity: str, title: str, is_pity: int):
    """
    记录抽卡（对齐 TS recordDraw schema）
    draw_type: 'create' | 'replace' | 'retest'
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO draw_history
        (user_id, draw_type, attribute, social, thinking, decision, rarity, title, is_pity, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (user_id, draw_type, attribute, social, thinking, decision,
         rarity, title, is_pity, ts()))
    conn.commit()
    conn.close()


# ============ 记忆操作（对齐 TS 全部函数） ============

def save_memory(user_id: str, keyword: str, canonical: str, search_hint: str, campus: str = ''):
    """保存记忆（INSERT OR REPLACE，对齐 TS saveMemory）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO conversation_memory
        (user_id, keyword, canonical, search_hint, campus, learned_at)
        VALUES (?,?,?,?,?,?)''',
        (user_id, keyword, canonical, search_hint, campus, ts()))
    conn.commit()
    conn.close()


def get_memory(user_id: str, keyword: str) -> Optional[Dict[str, Any]]:
    """精确查询一条记忆"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM conversation_memory
        WHERE user_id=? AND keyword=?''', (user_id, keyword))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'user_id': row[0], 'keyword': row[1], 'canonical': row[2],
            'search_hint': row[3], 'campus': row[4], 'learned_at': row[5]}


def search_memories(user_id: str, keyword: str) -> List[Dict[str, Any]]:
    """LIKE 模糊搜索记忆（对齐 TS searchMemories）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM conversation_memory
        WHERE user_id=? AND keyword LIKE ?
        ORDER BY learned_at DESC''', (user_id, f'%{keyword}%'))
    rows = c.fetchall()
    conn.close()
    return [dict(user_id=r[0], keyword=r[1], canonical=r[2],
                  search_hint=r[3], campus=r[4], learned_at=r[5]) for r in rows]


def get_all_memories(user_id: str) -> List[Dict[str, Any]]:
    """获取用户所有记忆"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM conversation_memory
        WHERE user_id=? ORDER BY learned_at DESC''', (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(user_id=r[0], keyword=r[1], canonical=r[2],
                 search_hint=r[3], campus=r[4], learned_at=r[5]) for r in rows]


def delete_memory(user_id: str, keyword: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM conversation_memory WHERE user_id=? AND keyword=?', (user_id, keyword))
    conn.commit()
    conn.close()


def get_memory_by_canonical(user_id: str, canonical: str) -> Optional[Dict[str, Any]]:
    """通过 canonical 反向查记忆（对齐 TS getMemoryByCanonical）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute('''SELECT * FROM conversation_memory
        WHERE user_id=? AND canonical=?''', (user_id, canonical))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'user_id': row[0], 'keyword': row[1], 'canonical': row[2],
            'search_hint': row[3], 'campus': row[4], 'learned_at': row[5]}


# ============ 种子记忆（对齐 TS） ============

def get_seed_memories() -> List[Dict[str, Any]]:
    """获取全局种子记忆（__seed__，对齐 TS getSeedMemories）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM conversation_memory WHERE user_id='__seed__'")
    rows = c.fetchall()
    conn.close()
    return [dict(user_id=r[0], keyword=r[1], canonical=r[2],
                 search_hint=r[3], campus=r[4], learned_at=r[5]) for r in rows]


def get_seed_memory(keyword: str) -> Optional[Dict[str, Any]]:
    """精确查询种子记忆（对齐 TS getSeedMemory）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM conversation_memory WHERE user_id='__seed__' AND keyword=?",
              (keyword,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'user_id': row[0], 'keyword': row[1], 'canonical': row[2],
            'search_hint': row[3], 'campus': row[4], 'learned_at': row[5]}


def get_seed_memory_by_canonical(canonical: str) -> Optional[Dict[str, Any]]:
    """通过 canonical 查询种子记忆（对齐 TS getSeedMemoryByCanonical）"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM conversation_memory WHERE user_id='__seed__' AND canonical=?",
              (canonical,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {'user_id': row[0], 'keyword': row[1], 'canonical': row[2],
            'search_hint': row[3], 'campus': row[4], 'learned_at': row[5]}


def init_seed_memories():
    """初始化种子记忆（从 CSV 导入）"""
    import csv
    seed_file = os.path.join(os.path.dirname(__file__), 'seed', 'conversation_memory_seed_sysu.csv')
    if not os.path.exists(seed_file):
        return 0

    conn = get_conn()
    c = conn.cursor()
    count = 0
    with open(seed_file, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('user_id') == '__seed__':
                c.execute('''INSERT OR IGNORE INTO conversation_memory
                    (user_id, keyword, canonical, search_hint, campus, learned_at)
                    VALUES (?,?,?,?,?,?)''',
                    ('__seed__', row['keyword'], row['canonical'],
                     row.get('search_hint', ''), row.get('campus', ''), ts()))
                count += 1
    conn.commit()
    conn.close()
    return count
