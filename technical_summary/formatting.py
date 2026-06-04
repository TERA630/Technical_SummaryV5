from .domain import is_missing


def fmt_price(value) -> str:
    """株価・VWAP・移動平均線用。500円未満は小数2桁、500円以上は整数。"""
    if is_missing(value):
        return "N/A"
    value = float(value)
    if abs(value) < 500:
        return f"{value:,.2f}"
    return f"{int(round(value)):,}"


def fmt_price_diff(value) -> str:
    """VWAP差分用。絶対値500円未満は小数2桁、500円以上は整数。"""
    if is_missing(value):
        return "N/A"
    value = float(value)
    if abs(value) < 500:
        return f"{value:+,.2f}"
    return f"{int(round(value)):+,d}"


def fmt_pct(value) -> str:
    """騰落率・乖離率・出来高比用。小数2桁。"""
    if is_missing(value):
        return "N/A"
    return f"{float(value):+.2f}%"


def fmt_rsi(value) -> str:
    """RSI用。小数2桁。"""
    if is_missing(value):
        return "N/A"
    return f"{float(value):.2f}"


def fmt_volume(value) -> str:
    """出来高用。万株単位、小数1桁。"""
    if is_missing(value):
        return "N/A"
    return f"{float(value) / 10_000:.1f}万株"


def fmt_price_with_pct(price, pct) -> str:
    return f"{fmt_price(price)} ({fmt_pct(pct)})"


def fmt_vwap_with_diff(vwap, diff) -> str:
    return f"{fmt_price(vwap)} ({fmt_price_diff(diff)})"


def fmt_volume_with_ratio(volume, ratio_pct) -> str:
    return f"{fmt_volume(volume)} ({fmt_pct(ratio_pct)})"

