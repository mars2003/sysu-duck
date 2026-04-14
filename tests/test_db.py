"""数据库安全与基础操作测试。"""
import os
import tempfile
import unittest


class TestDbFieldWhitelist(unittest.TestCase):
    def test_rejects_unknown_field_without_touching_db(self):
        import db as db_mod

        with self.assertRaises(ValueError) as ctx:
            db_mod.update_profile_field('any_user', "campus='x", 'y')
        self.assertIn('不允许更新', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
