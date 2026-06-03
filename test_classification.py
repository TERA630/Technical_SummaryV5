import unittest

from Technical_SummaryV4 import classify_row


def row(dev25, vwap_dev_pct, rsi=60.0, main_score=0, is_main_stock=False):
    return {
        "dev25": dev25,
        "vwap_dev_pct": vwap_dev_pct,
        "rsi": rsi,
        "main_score": main_score,
        "is_main_stock": is_main_stock,
        "error": None,
    }


class ClassificationTest(unittest.TestCase):
    def test_a1_main_pullback_has_priority_at_dev25_seven(self):
        self.assertEqual(
            classify_row(row(dev25=7.0, vwap_dev_pct=-0.5, rsi=64.9, main_score=6)),
            "A1.主役押し目",
        )

    def test_a2_normal_good_position(self):
        self.assertEqual(
            classify_row(row(dev25=0.0, vwap_dev_pct=-0.5)),
            "A2.通常位置良好",
        )

    def test_vwap_below_minus_half_enters_recovery_wait_when_dev25_is_ok(self):
        self.assertEqual(
            classify_row(row(dev25=3.38, vwap_dev_pct=-0.51, rsi=56.69, main_score=6)),
            "E.VWAP回復待ち",
        )

    def test_b1_main_high_area(self):
        self.assertEqual(
            classify_row(row(dev25=7.0, vwap_dev_pct=0.0, rsi=66.0, main_score=6)),
            "B1.高値圏",
        )
        self.assertEqual(
            classify_row(row(dev25=11.9, vwap_dev_pct=1.0, rsi=69.9, main_score=6)),
            "B1.高値圏",
        )
        self.assertEqual(classify_row(row(dev25=4.0, vwap_dev_pct=0.5, rsi=64.0)), "A2.通常位置良好")
        self.assertEqual(classify_row(row(dev25=4.1, vwap_dev_pct=0.5, rsi=64.0)), "B1.高値圏")
        self.assertEqual(classify_row(row(dev25=0.0, vwap_dev_pct=0.5, rsi=65.0)), "B1.高値圏")

    def test_b2_overheated_by_dev25_or_rsi_at_threshold(self):
        self.assertEqual(classify_row(row(dev25=12.0, vwap_dev_pct=0.5)), "B2.過熱")
        self.assertEqual(classify_row(row(dev25=2.0, vwap_dev_pct=0.5, rsi=70.0)), "B2.過熱")

    def test_weak_rebound_above_vwap(self):
        self.assertEqual(
            classify_row(row(dev25=-2.5, vwap_dev_pct=0.1)),
            "C.弱い戻り",
        )

    def test_vwap_recovery_wait(self):
        self.assertEqual(
            classify_row(row(dev25=-2.5, vwap_dev_pct=-1.0)),
            "E.VWAP回復待ち",
        )

    def test_weak_trend_by_vwap_or_deep_ma25_break(self):
        self.assertEqual(classify_row(row(dev25=0.0, vwap_dev_pct=-2.1)), "D.トレンド弱い")
        self.assertEqual(classify_row(row(dev25=-3.0, vwap_dev_pct=-1.0)), "D.トレンド弱い")

    def test_previous_gap_bands_are_classified(self):
        self.assertEqual(classify_row(row(dev25=-2.9, vwap_dev_pct=-0.4, rsi=64.0)), "E.VWAP回復待ち")
        self.assertEqual(classify_row(row(dev25=5.0, vwap_dev_pct=0.5, rsi=64.0)), "B1.高値圏")
        self.assertEqual(classify_row(row(dev25=8.0, vwap_dev_pct=0.5, rsi=70.0, main_score=6)), "B2.過熱")
        self.assertEqual(classify_row(row(dev25=12.0, vwap_dev_pct=0.5, rsi=64.0)), "B2.過熱")

    def test_missing_values_are_weak_trend(self):
        self.assertEqual(classify_row(row(dev25=None, vwap_dev_pct=0.0)), "D.トレンド弱い")
        self.assertEqual(classify_row(row(dev25=0.0, vwap_dev_pct=None)), "D.トレンド弱い")


if __name__ == "__main__":
    unittest.main()
