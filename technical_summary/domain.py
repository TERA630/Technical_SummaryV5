import math
from typing import Optional

import pandas as pd

from .config import (
    DEEP_MA25_BREAK_DEV25,
    MAIN_GOOD_DEV25_MAX,
    MAIN_GOOD_DEV25_MIN,
    MAIN_HIGH_DEV25_MAX,
    NORMAL_GOOD_DEV25_MAX,
    NORMAL_GOOD_DEV25_MIN,
    RSI_HIGH_MAX,
    RSI_MAIN_MAX,
    STRONG_THEME_CODES,
    STRONG_THEME_KEYWORDS,
    VWAP_NEAR_MIN,
    VWAP_RECOVERY_MIN,
)


def is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))


def compute_rsi(close: pd.Series, period: int = 14) -> Optional[float]:
    close = close.dropna()
    if len(close) < period + 1:
        return None

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]

    if pd.isna(val):
        return None
    return float(val)


def is_strong_theme(name: str, code: str) -> bool:
    if code in STRONG_THEME_CODES:
        return True
    return any(keyword in name for keyword in STRONG_THEME_KEYWORDS)


def calc_main_score(row: dict) -> int:
    """
    主役判定用スコア。8点満点。
    - 資金集中: 0-2点
    - トレンド: 0-2点
    - 押しの浅さ/位置: 0-2点
    - RSI: 0-1点
    - 強テーマ: 0-1点
    """
    score = 0
    latest = row.get("latest")
    vwap = row.get("vwap")
    ma5 = row.get("ma5")
    ma25 = row.get("ma25")
    dev25 = row.get("dev25")
    rsi = row.get("rsi")
    vol_ratio = row.get("volume_ratio_pct")

    # 資金集中：20日平均比の増加率。+50%以上なら強い。
    if not is_missing(vol_ratio):
        if vol_ratio >= 50.0:
            score += 2
        elif vol_ratio >= 20.0:
            score += 1

    # トレンド：VWAP・5日線・25日線の上にいるか。
    if not any(is_missing(x) for x in [latest, vwap, ma5, ma25]):
        if latest >= vwap and latest >= ma5 and latest >= ma25:
            score += 2
        elif latest >= vwap and latest >= ma25:
            score += 1

    # 位置：主役押し目の25日線レンジを高く評価する。
    if not is_missing(dev25):
        if MAIN_GOOD_DEV25_MIN <= dev25 <= MAIN_GOOD_DEV25_MAX:
            score += 2
        elif NORMAL_GOOD_DEV25_MIN <= dev25 <= MAIN_GOOD_DEV25_MAX:
            score += 1

    # RSI：50〜70は勢いがあり、過熱しすぎていない。
    if not is_missing(rsi) and 50.0 <= rsi < RSI_MAIN_MAX:
        score += 1

    # 強テーマ：半導体・電線・電機・防衛など。
    if row.get("theme_strength"):
        score += 1

    return score


def classify_row(row: dict) -> str:
    if row.get("error"):
        return "ERROR"

    dev25 = row.get("dev25")
    rsi = row.get("rsi")
    vwap_dev_pct = row.get("vwap_dev_pct")
    is_main = row.get("is_main_stock", False) or row.get("main_score", 0) >= 6

    if any(is_missing(x) for x in [dev25, vwap_dev_pct]):
        return "D.トレンド弱い"

    dev25 = float(dev25)
    vwap_dev_pct = float(vwap_dev_pct)
    rsi_value = 999.0 if is_missing(rsi) else float(rsi)
    entry_vwap_ok = vwap_dev_pct >= VWAP_NEAR_MIN
    above_vwap = vwap_dev_pct >= 0.0

    if dev25 >= MAIN_HIGH_DEV25_MAX or rsi_value >= RSI_HIGH_MAX:
        return "B2.過熱"

    if vwap_dev_pct < VWAP_RECOVERY_MIN or dev25 <= DEEP_MA25_BREAK_DEV25:
        return "D.トレンド弱い"

    if is_main and MAIN_GOOD_DEV25_MIN <= dev25 <= MAIN_GOOD_DEV25_MAX and entry_vwap_ok and rsi_value < RSI_MAIN_MAX:
        return "A1.主役押し目"

    if NORMAL_GOOD_DEV25_MIN <= dev25 <= NORMAL_GOOD_DEV25_MAX and entry_vwap_ok and rsi_value < RSI_MAIN_MAX:
        return "A2.通常位置良好"

    if above_vwap and dev25 < NORMAL_GOOD_DEV25_MIN:
        return "C.弱い戻り"

    if VWAP_RECOVERY_MIN <= vwap_dev_pct < 0.0 and dev25 > DEEP_MA25_BREAK_DEV25:
        return "E.VWAP回復待ち"

    if (
        (is_main and MAIN_GOOD_DEV25_MAX <= dev25 < MAIN_HIGH_DEV25_MAX)
        or ((not is_main) and NORMAL_GOOD_DEV25_MAX < dev25 < MAIN_HIGH_DEV25_MAX)
        or (RSI_MAIN_MAX <= rsi_value < RSI_HIGH_MAX)
    ):
        return "B1.高値圏"

    if dev25 < NORMAL_GOOD_DEV25_MIN:
        return "D.トレンド弱い"

    return "D.トレンド弱い"

