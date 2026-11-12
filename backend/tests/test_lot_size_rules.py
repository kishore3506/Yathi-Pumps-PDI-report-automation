import unittest

from services.report_generator import allocate_lot_quantity, report_count_for_lot


class LotSizeRulesTests(unittest.TestCase):
    def test_requested_band_boundaries(self):
        cases = {
            1: 1, 10: 1, 11: 1, 100: 1,
            101: 2, 1200: 2, 1201: 3, 2500: 3,
            2501: 4, 4000: 4, 4001: 5,
        }
        for lot_size, expected in cases.items():
            with self.subTest(lot_size=lot_size):
                self.assertEqual(report_count_for_lot(lot_size), expected)

    def test_allocations_sum_to_lot_and_distribute_remainder_first(self):
        self.assertEqual(allocate_lot_quantity(101, 2), [51, 50])
        self.assertEqual(allocate_lot_quantity(2501, 4), [626, 625, 625, 625])
        self.assertEqual(sum(allocate_lot_quantity(9001, 5)), 9001)

    def test_zero_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            report_count_for_lot(0)


if __name__ == "__main__":
    unittest.main()
