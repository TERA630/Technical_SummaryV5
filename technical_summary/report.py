from datetime import datetime

from .config import (
    CATEGORY_ORDER,
    DEEP_MA25_BREAK_DEV25,
    MAIN_GOOD_DEV25_MAX,
    MAIN_GOOD_DEV25_MIN,
    MAIN_HIGH_DEV25_MAX,
    NORMAL_GOOD_DEV25_MAX,
    NORMAL_GOOD_DEV25_MIN,
    RSI_HIGH_MAX,
    RSI_MAIN_MAX,
    VOLUME_AVG_DAYS,
    VWAP_NEAR_MIN,
    VWAP_RECOVERY_MIN,
)
from .formatting import (
    fmt_price,
    fmt_price_with_pct,
    fmt_pct,
    fmt_rsi,
    fmt_volume_with_ratio,
    fmt_vwap_with_diff,
)


def sort_key(row: dict):
    category = row.get("category")
    code = row.get("code", "")
    dev25 = row.get("dev25")
    main_score = row.get("main_score", 0)
    day_change_pct = row.get("day_change_pct")

    if row.get("error"):
        return (99, float("inf"), code)

    order = {name: i for i, name in enumerate(CATEGORY_ORDER)}.get(category, 90)

    if category == "A1.主役押し目":
        # 主役スコア高、25日乖離が+2〜+10の中央に近いものを上位へ。
        target = 5.0
        return (order, -main_score, abs((dev25 if dev25 is not None else 999) - target), code)
    if category == "A2.通常位置良好":
        return (order, abs(dev25) if dev25 is not None else float("inf"), code)
    if category == "B1.高値圏":
        return (order, -main_score, dev25 if dev25 is not None else float("inf"), code)
    if category == "B2.過熱":
        return (order, -(dev25 if dev25 is not None else -float("inf")), code)
    if category == "C.弱い戻り":
        return (order, -(day_change_pct if day_change_pct is not None else -float("inf")), code)
    if category == "E.VWAP回復待ち":
        return (order, dev25 if dev25 is not None else float("inf"), code)
    return (order, day_change_pct if day_change_pct is not None else float("inf"), code)


def build_table_for_category(title: str, rows: list[dict]) -> list[str]:
    lines = [f"# {title}", ""]
    lines.append("| 銘柄 | 前日終値 | 始値 | 高値 | 安値 | 最新値(騰落) | VWAP(差分) | 5日乖離 | 25日線(25日乖離) | RSI | 出来高(20日平均比) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    if not rows:
        lines.append("| なし | - | - | - | - | - | - | - | - | - | - |")
        lines.append("")
        return lines

    for r in rows:
        lines.append(
            f"| {r['name']} ({r['code']}) "
            f"| {fmt_price(r['prev_close'])} "
            f"| {fmt_price(r['open'])} "
            f"| {fmt_price(r['high'])} "
            f"| {fmt_price(r['low'])} "
            f"| {fmt_price_with_pct(r['latest'], r['day_change_pct'])} "
            f"| {fmt_vwap_with_diff(r['vwap'], r['vwap_diff'])} "
            f"| {fmt_pct(r['dev5'])} "
            f"| {fmt_price_with_pct(r['ma25'], r['dev25'])} "
            f"| {fmt_rsi(r['rsi'])} "
            f"| {fmt_volume_with_ratio(r['today_volume'], r['volume_ratio_pct'])} |"
        )

    lines.append("")
    return lines


def build_markdown(rows: list[dict], source_name: str) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(f"# Stock Summery ({now_str})")
    lines.append("")
    lines.append(f"- 元ファイル: {source_name}")
    lines.append(f"- 出来高平均: {VOLUME_AVG_DAYS}営業日")
    lines.append("")

    categorized = {key: [] for key in CATEGORY_ORDER}
    errors = []

    for row in rows:
        if row.get("error"):
            errors.append(row)
        else:
            categorized.setdefault(row["category"], []).append(row)

    for key in CATEGORY_ORDER:
        categorized[key].sort(key=sort_key)
        lines.extend(build_table_for_category(key, categorized[key]))

    lines.append("# 取得エラー")
    lines.append("")
    if not errors:
        lines.append("- なし")
    else:
        for row in sorted(errors, key=lambda x: x["code"]):
            lines.append(f"- {row['name']} ({row['code']}): {row['error']}")
    lines.append("")

    lines.append("# 表示仕様・分類仕様")
    lines.append("")
    lines.append("## 表示仕様")
    lines.append("")
    lines.append("- 株価・VWAP・25日線: 500円未満は小数2桁、500円以上は整数")
    lines.append("- VWAP: VWAP比ではなく、現在値との差分を表示")
    lines.append("- 騰落率・5日乖離・25日乖離・出来高比: 小数2桁")
    lines.append("- RSI: 小数2桁")
    lines.append("- 出来高: 万株単位、小数1桁")
    lines.append("")
    lines.append("## 分類仕様")
    lines.append("")
    lines.append(f"- A1.主役押し目: 主役S 6点以上、25日乖離 +{MAIN_GOOD_DEV25_MIN:.0f}%〜+{MAIN_GOOD_DEV25_MAX:.0f}%、VWAP乖離 {VWAP_NEAR_MIN:.1f}%以上、RSI < {RSI_MAIN_MAX:.0f}")
    lines.append(f"- A2.通常位置良好: 25日乖離 {NORMAL_GOOD_DEV25_MIN:.0f}%〜+{NORMAL_GOOD_DEV25_MAX:.0f}%、VWAP乖離 {VWAP_NEAR_MIN:.1f}%以上、RSI < {RSI_MAIN_MAX:.0f}")
    lines.append(f"- B1.高値圏: 主役S 6点以上で25日乖離 +{MAIN_GOOD_DEV25_MAX:.0f}%〜+{MAIN_HIGH_DEV25_MAX:.0f}%未満、非主役で25日乖離 +{NORMAL_GOOD_DEV25_MAX:.0f}%超〜+{MAIN_HIGH_DEV25_MAX:.0f}%未満、またはRSI {RSI_MAIN_MAX:.0f}〜{RSI_HIGH_MAX:.0f}未満")
    lines.append(f"- B2.過熱: 25日乖離 +{MAIN_HIGH_DEV25_MAX:.0f}%以上、またはRSI >= {RSI_HIGH_MAX:.0f}")
    lines.append(f"- C.弱い戻り: VWAP上だが25日乖離 < {NORMAL_GOOD_DEV25_MIN:.0f}%")
    lines.append(f"- E.VWAP回復待ち: VWAP乖離 {VWAP_RECOVERY_MIN:.1f}%以上0.0%未満、かつ25日乖離 > {DEEP_MA25_BREAK_DEV25:.0f}%")
    lines.append(f"- D.トレンド弱い: VWAP乖離 < {VWAP_RECOVERY_MIN:.1f}%、または25日乖離 <= {DEEP_MA25_BREAK_DEV25:.0f}%")
    lines.append("")
    lines.append("## 内部判定")
    lines.append("")
    lines.append("- テーマ適格 True: 半導体、電線、防衛、重電、AI、電力インフラなど")
    lines.append("- 主役S: 出来高・トレンド・25日線乖離・RSI・テーマ適格を8点満点で評価。表には表示しない")
    lines.append("")
    return "\n".join(lines)

