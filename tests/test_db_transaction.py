"""db_execute 写入失败时整段事务回滚。"""
import os
import sqlite3
import tempfile
import importlib
import unittest


class TestDbExecuteRollback(unittest.TestCase):
    def test_rollback_on_integrity_error(self):
        fd, path = tempfile.mkstemp(suffix='.duck.db')
        os.close(fd)
        os.environ['DUCK_DB_PATH'] = path
        try:
            import db
            importlib.reload(db)
            db.ensure_db()

            def run_broken_transaction():
                with db.db_execute(write=True) as conn:
                    c = conn.cursor()
                    now = db.ts()
                    c.execute(
                        '''INSERT INTO duck_profiles
                        (user_id, nickname, attribute, social, thinking, decision, campus,
                         created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?)''',
                        ('rb_user', 'n', '呆萌', 'E', 'N', 'T', '南校', now, now),
                    )
                    c.execute(
                        '''INSERT INTO duck_profiles
                        (user_id, nickname, attribute, social, thinking, decision, campus,
                         created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?)''',
                        ('rb_user', 'n2', '呆萌', 'E', 'N', 'T', '南校', now, now),
                    )

            with self.assertRaises(sqlite3.IntegrityError):
                run_broken_transaction()

            with db.db_execute(write=False) as conn:
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM duck_profiles WHERE user_id=?', ('rb_user',))
                n = c.fetchone()[0]
            self.assertEqual(n, 0)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
            os.environ.pop('DUCK_DB_PATH', None)
            import db as db_mod
            importlib.reload(db_mod)


if __name__ == '__main__':
    unittest.main()
