"""cmd_recall 与独立数据库文件的集成测试。"""
import os
import tempfile
import importlib
import unittest


class TestCmdRecallIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._fd, cls.db_path = tempfile.mkstemp(suffix='.duck.db')
        os.close(cls._fd)
        os.environ['DUCK_DB_PATH'] = cls.db_path
        import src.db as db
        import duck
        importlib.reload(db)
        importlib.reload(duck)
        cls.db = db
        cls.duck = duck
        db.ensure_db()
        conn = db.get_conn()
        c = conn.cursor()
        c.execute('DELETE FROM conversation_memory')
        conn.commit()
        conn.close()
        db.save_memory('__seed__', '图书馆借书', '持校园卡借阅', '图书馆', '南校')
        db.save_memory('u_recall', '我的宿舍', '至善园三号', '', '东校')

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls.db_path)
        except OSError:
            pass
        os.environ.pop('DUCK_DB_PATH', None)
        import src.db as db
        importlib.reload(db)

    def test_hit_seed_exact(self):
        r = self.duck.cmd_recall('u_recall', '图书馆借书')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'seed')
        self.assertEqual(r['canonical'], '持校园卡借阅')

    def test_hit_user_exact(self):
        r = self.duck.cmd_recall('u_recall', '我的宿舍')
        self.assertTrue(r['hit'])
        self.assertEqual(r['source'], 'user')
        self.assertEqual(r['canonical'], '至善园三号')

    def test_miss_returns_entity_resolve(self):
        r = self.duck.cmd_recall('u_recall', 'xyz不存在关键词999')
        self.assertFalse(r['hit'])
        self.assertIn('resolved', r)


if __name__ == '__main__':
    unittest.main()
