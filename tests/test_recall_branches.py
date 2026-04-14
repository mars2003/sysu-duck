"""cmd_recall 模糊匹配与实体解析分支（可控 mock）。"""
import os
import tempfile
import importlib
import unittest
from unittest.mock import patch


def _reload_db_duck(path: str):
    os.environ['DUCK_DB_PATH'] = path
    import db
    import duck
    importlib.reload(db)
    importlib.reload(duck)
    return db, duck


class TestRecallFuzzyAndEntity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fd, path = tempfile.mkstemp(suffix='.duck.db')
        os.close(fd)
        cls.db_path = path
        cls.db, cls.duck = _reload_db_duck(path)
        cls.db.ensure_db()

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls.db_path)
        except OSError:
            pass
        os.environ.pop('DUCK_DB_PATH', None)
        import db
        importlib.reload(db)

    def setUp(self):
        conn = self.db.get_conn()
        c = conn.cursor()
        c.execute('DELETE FROM conversation_memory')
        conn.commit()
        conn.close()

    def test_seed_fuzzy_hit(self):
        self.db.save_memory('__seed__', '关键词原始', '答案正文存储', 'hint', '全校')

        def fake_match(kw, memories):
            if memories and memories[0].get('user_id') == '__seed__':
                return {'keyword': '近似', 'answer': '答案正文存储', 'score': 0.72}
            return None

        with patch.object(self.duck, 'best_memory_match', side_effect=fake_match):
            r = self.duck.cmd_recall('u1', '用户说的近似句')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'seed')
        self.assertTrue(r.get('fuzzy'))
        self.assertEqual(r['canonical'], '答案正文存储')

    def test_user_fuzzy_hit(self):
        self.db.save_memory('u1', '我的关键词', '用户侧答案', '', '东校')

        def fake_match(kw, memories):
            if not memories:
                return None
            uid = memories[0].get('user_id')
            if uid == '__seed__':
                return None
            if uid == 'u1':
                return {'keyword': 'x', 'answer': '用户侧答案', 'score': 0.65}
            return None

        with patch.object(self.duck, 'best_memory_match', side_effect=fake_match):
            r = self.duck.cmd_recall('u1', '口语化说法')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'user')
        self.assertTrue(r.get('fuzzy'))

    def test_entity_resolves_seed_by_canonical(self):
        self.db.save_memory('__seed__', 'k_seed', '实体标准canonical段落', 'h', '南校')
        fake = {'canonical': '实体标准canonical段落', 'hint': '中山大学', 'campus': '南校'}

        with patch.object(self.duck, 'resolve_entity', return_value=fake):
            r = self.duck.cmd_recall('u1', 'zzz_no_fuzzy_overlap_query_31415')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'seed')
        self.assertIn('entity_hint', r)
        self.assertEqual(r['canonical'], '实体标准canonical段落')


if __name__ == '__main__':
    unittest.main()
