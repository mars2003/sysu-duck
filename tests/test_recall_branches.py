"""cmd_recall 模糊匹配与实体解析分支（可控 mock）。"""
import os
import tempfile
import importlib
import unittest
from unittest.mock import patch


def _reload_db_duck(path: str):
    os.environ['DUCK_DB_PATH'] = path
    import src.db as db
    import src.duck as duck
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
        import src.db as db
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

    def test_entity_step6_user_hit_by_entity_keyword(self):
        """第 6 步：实体 canonical 与用户记忆的 keyword 一致时命中。"""
        self.db.save_memory('u1', '标准实体名', '用户保存的答案', '', '南校')
        fake_res = {'canonical': '标准实体名', 'hint': '', 'campus': '南校'}
        with patch.object(self.duck, 'resolve_entity', return_value=fake_res):
            with patch.object(self.duck, 'best_memory_match', return_value=None):
                r = self.duck.cmd_recall('u1', '用户口头别名说法')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'user')
        self.assertIn('entity_hint', r)
        self.assertEqual(r['canonical'], '用户保存的答案')

    def test_entity_step6_user_hit_by_canonical_column(self):
        """第 6 步：keyword 与实体名不同，但 canonical 列与解析结果一致时命中。"""
        self.db.save_memory('u1', '口语关键词', '唯一canonical值', '', '东校')
        fake_res = {'canonical': '唯一canonical值', 'hint': '', 'campus': ''}
        with patch.object(self.duck, 'resolve_entity', return_value=fake_res):
            with patch.object(self.duck, 'best_memory_match', return_value=None):
                r = self.duck.cmd_recall('u1', '某别名')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'user')
        self.assertIn('entity_hint', r)
        self.assertEqual(r['canonical'], '唯一canonical值')


if __name__ == '__main__':
    unittest.main()
