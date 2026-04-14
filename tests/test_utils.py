"""工具函数测试。"""
import unittest

from src.utils import SequenceMatcher, sanitize_nickname, similarity_ratio


class TestUtils(unittest.TestCase):
    def test_similarity_identical(self):
        self.assertEqual(similarity_ratio('图书馆', '图书馆'), 1.0)

    def test_sequence_matcher_compat(self):
        self.assertAlmostEqual(SequenceMatcher('ab', 'ab')['ratio'](), 1.0)

    def test_sanitize_nickname(self):
        ok, err = sanitize_nickname('阿花Pro')
        self.assertTrue(ok)
        self.assertEqual(err, '')

    def test_sanitize_rejects_special_chars(self):
        ok, err = sanitize_nickname('a*b')
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
