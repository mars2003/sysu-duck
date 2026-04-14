"""编号服务 HTTP 层与解析逻辑测试。"""
import unittest
from unittest.mock import patch, MagicMock

import duck


class TestParseYayaidBody(unittest.TestCase):
    def test_valid_json(self):
        self.assertEqual(duck._parse_yayaid_body(b'{"number": 42}'), 42)

    def test_string_number(self):
        self.assertEqual(duck._parse_yayaid_body(b'{"number": "7"}'), 7)

    def test_zero_or_invalid(self):
        self.assertEqual(duck._parse_yayaid_body(b'{"number": 0}'), 0)
        self.assertEqual(duck._parse_yayaid_body(b'not json'), 0)


class TestGetNextYayaid(unittest.TestCase):
    def _fake_urlopen(self, body: bytes):
        """返回可作为上下文管理器的响应对象。"""
        resp = MagicMock()
        resp.read.return_value = body
        cm = MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = None
        return cm

    def test_success_first_try(self):
        cm = self._fake_urlopen(b'{"number": 100}')
        with patch.object(duck.urllib.request, 'urlopen', return_value=cm):
            self.assertEqual(duck.get_next_yayaid(), 100)

    def test_retries_until_success(self):
        """第一次 JSON 无效，第二次成功。"""
        bad_cm = self._fake_urlopen(b'{}')
        good_cm = self._fake_urlopen(b'{"number": 2}')
        with patch.object(duck.urllib.request, 'urlopen', side_effect=[bad_cm, good_cm]):
            with patch.dict('os.environ', {'DUCK_YAYAID_RETRIES': '2', 'DUCK_YAYAID_BACKOFF': '0'}, clear=False):
                with patch.object(duck.time, 'sleep'):
                    self.assertEqual(duck.get_next_yayaid(), 2)

    def test_all_fail_returns_zero(self):
        cm = self._fake_urlopen(b'{}')
        with patch.object(duck.urllib.request, 'urlopen', return_value=cm):
            with patch.dict('os.environ', {'DUCK_YAYAID_RETRIES': '1'}, clear=False):
                self.assertEqual(duck.get_next_yayaid(), 0)


if __name__ == '__main__':
    unittest.main()
