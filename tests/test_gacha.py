"""抽卡与稀有度合并逻辑测试。"""
import unittest

from gacha import merge_draw_and_title_rarity, rarity_rank, update_pity


class TestGacha(unittest.TestCase):
    def test_merge_prefers_title_when_higher(self):
        self.assertEqual(merge_draw_and_title_rarity('N', 'SR'), 'SR')
        self.assertEqual(merge_draw_and_title_rarity('R', 'SSR'), 'SSR')

    def test_merge_prefers_draw_when_higher(self):
        self.assertEqual(merge_draw_and_title_rarity('SSR', 'N'), 'SSR')
        self.assertEqual(merge_draw_and_title_rarity('SR', 'R'), 'SR')

    def test_merge_equal_uses_draw(self):
        self.assertEqual(merge_draw_and_title_rarity('R', 'R'), 'R')

    def test_rarity_rank_order(self):
        self.assertLess(rarity_rank('N'), rarity_rank('SSR'))

    def test_update_pity_ssr_resets(self):
        self.assertEqual(update_pity('SSR', 5, 5), (0, 0))

    def test_update_pity_sr(self):
        self.assertEqual(update_pity('SR', 3, 2), (0, 3))


if __name__ == '__main__':
    unittest.main()
