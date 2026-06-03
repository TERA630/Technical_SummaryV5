import math
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None
    filedialog = None


# =========================
# 判定パラメータ
# =========================
NORMAL_GOOD_DEV25_MIN = -2.0
NORMAL_GOOD_DEV25_MAX = 4.0
STRONG_THEME_GOOD_DEV25_MAX = 8.0
MAIN_GOOD_DEV25_MIN = 1.0
MAIN_GOOD_DEV25_MAX = 7.0
MAIN_HIGH_DEV25_MAX = 12.0
RSI_MAIN_MAX = 65.0
RSI_HIGH_MAX = 70.0
VWAP_NEAR_MIN = -0.5
VWAP_NEAR_MAX = 0.5
VWAP_RECOVERY_MIN = -2.0
DEEP_MA25_BREAK_DEV25 = -3.0
VOLUME_AVG_DAYS = 20
MAX_WORKERS = 6

# 業種データなしでも使えるよう、強テーマはコード・銘柄名で暫定判定する。
# 必要に応じてここへ追加する。
STRONG_THEME_CODES = {
    # 半導体・半導体材料・製造装置・電子部品
    "3436", "4063", "6315", "6323", "6503", "6754", "6954", "6963", "3132",
    # 電線・電力インフラ
    "5802", "5803",
    # 防衛・重工・宇宙関連
    "7011", "7721", "6946",
    # AI/情報通信・大型ハイテク候補
    "6501", "6701",
}

STRONG_THEME_KEYWORDS = [
    "半導体", "信越", "SUMCO", "ローツェ", "TOWA", "マクニカ", "ローム", "ファナック",
    "フジクラ", "住友電", "電線", "三菱電機", "日立", "日本電気", "NEC",
    "三菱重工", "東京計器", "アビオニクス", "防衛", "重工",
]

CATEGORY_ORDER = [
    "A1.主役押し目",
    "A2.通常位置良好",
    "B1.高値圏",
    "B2.過熱",
    "C.弱い戻り",
    "E.VWAP回復待ち",
    "D.トレンド弱い",
]


# =========================
# 入出力・フォーマット
# =========================
def choose_file() -> Path:
    if tk is None or filedialog is None:
        raise RuntimeError("tkinter が使えません。GUI付きPythonを使ってください。")

    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="事前の監視銘柄.md を選択",
        filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
    )
    root.destroy()

    if not path:
        raise RuntimeError("ファイルが選択されませんでした。")

    return Path(path)


def parse_tickers_from_md(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"(?:-\s*)?(?:\*\*)?\s*([^\n\(\*]+?)\s*\((\d{4})\)(?:\*\*)?")
    matches = pattern.findall(text)

    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, code in matches:
        cleaned_name = name.strip()
        if code not in seen:
            seen.add(code)
            results.append((cleaned_name, code))
    return results


def is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))


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


# =========================
# 指標計算
# =========================
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


def fetch_intraday_vwap(ticker: yf.Ticker) -> Optional[float]:
    try:
        intraday = ticker.history(period="2d", interval="5m", auto_adjust=False, prepost=False)
        if intraday is None or intraday.empty:
            return None

        intraday = intraday[["High", "Low", "Close", "Volume"]].dropna()
        if intraday.empty:
            return None

        last_day = pd.Timestamp(intraday.index[-1]).date()
        intraday = intraday[pd.to_datetime(intraday.index).date == last_day]
        if intraday.empty:
            return None

        typical = (intraday["High"] + intraday["Low"] + intraday["Close"]) / 3
        volume = intraday["Volume"]
        vol_sum = volume.sum()
        if vol_sum == 0:
            return None

        vwap = (typical * volume).sum() / vol_sum
        if pd.isna(vwap):
            return None
        return float(vwap)
    except Exception:
        return None


def empty_row(name: str, code: str, error: str) -> dict:
    return {
        "name": name,
        "code": code,
        "date": "N/A",
        "prev_close": None,
        "open": None,
        "high": None,
        "low": None,
        "latest": None,
        "day_change_pct": None,
        "vwap": None,
        "vwap_diff": None,
        "vwap_dev_pct": None,
        "ma5": None,
        "dev5": None,
        "ma25": None,
        "dev25": None,
        "rsi": None,
        "today_volume": None,
        "avg20_volume": None,
        "volume_ratio_pct": None,
        "theme_strength": False,
        "main_score": 0,
        "is_main_stock": False,
        "category": "ERROR",
        "error": error,
    }


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


def fetch_stock_row(name: str, code: str) -> dict:
    symbol = f"{code}.T"
    ticker = yf.Ticker(symbol)

    hist = ticker.history(period="3mo", auto_adjust=False)
    if hist is None or hist.empty:
        return empty_row(name, code, "価格データなし")

    hist = hist[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if len(hist) < 25:
        return empty_row(name, code, "データ不足(25営業日未満)")

    last = hist.iloc[-1]
    latest = float(last["Close"])
    open_price = float(last["Open"])
    high_price = float(last["High"])
    low_price = float(last["Low"])
    today_volume = float(last["Volume"])

    prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else None

    ma5 = hist["Close"].rolling(5).mean().iloc[-1]
    ma25 = hist["Close"].rolling(25).mean().iloc[-1]
    avg20_volume = hist["Volume"].rolling(VOLUME_AVG_DAYS).mean().iloc[-1]

    vwap = fetch_intraday_vwap(ticker)
    if vwap is None:
        vwap = float((last["High"] + last["Low"] + last["Close"]) / 3)

    ma5 = None if pd.isna(ma5) else float(ma5)
    ma25 = None if pd.isna(ma25) else float(ma25)
    avg20_volume = None if pd.isna(avg20_volume) else float(avg20_volume)

    dev5 = None if ma5 in (None, 0) else (latest / ma5 - 1) * 100
    dev25 = None if ma25 in (None, 0) else (latest / ma25 - 1) * 100
    day_change_pct = None if prev_close in (None, 0) else (latest / prev_close - 1) * 100
    vwap_diff = None if vwap is None else latest - vwap
    vwap_dev_pct = None if vwap in (None, 0) else (latest / vwap - 1) * 100
    # 20日平均比は「平均より何％多い/少ないか」で表示する。
    volume_ratio_pct = None if avg20_volume in (None, 0) else (today_volume / avg20_volume - 1) * 100

    rsi = compute_rsi(hist["Close"], 14)

    last_date = hist.index[-1]
    try:
        last_date = pd.Timestamp(last_date).tz_localize(None)
    except Exception:
        last_date = pd.Timestamp(last_date)

    row = {
        "name": name,
        "code": code,
        "date": last_date.strftime("%Y-%m-%d"),
        "prev_close": prev_close,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "latest": latest,
        "day_change_pct": day_change_pct,
        "vwap": vwap,
        "vwap_diff": vwap_diff,
        "vwap_dev_pct": vwap_dev_pct,
        "ma5": ma5,
        "dev5": dev5,
        "ma25": ma25,
        "dev25": dev25,
        "rsi": rsi,
        "today_volume": today_volume,
        "avg20_volume": avg20_volume,
        "volume_ratio_pct": volume_ratio_pct,
        "theme_strength": is_strong_theme(name, code),
        "error": None,
    }
    row["main_score"] = calc_main_score(row)
    row["is_main_stock"] = row["main_score"] >= 6
    row["category"] = classify_row(row)
    return row


# =========================
# Markdown出力
# =========================
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


def build_output_filename(now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    # ':' は Windows で使えないため、クロスプラットフォーム優先で HHMM を採用
    return f"Stock_Summery_{now.strftime('%Y-%m-%d_%H%M')}.md"


def atomic_write_text(output_path: Path, text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path_str = tempfile.mkstemp(
        prefix=f".{output_path.stem}_",
        suffix=output_path.suffix,
        dir=str(output_path.parent),
        text=True,
    )
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, output_path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def fetch_all_rows(tickers: list[tuple[str, str]]) -> list[dict]:
    total = len(tickers)
    rows: list[dict] = []

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, total))) as executor:
        future_to_meta = {
            executor.submit(fetch_stock_row, name, code): (idx, name, code)
            for idx, (name, code) in enumerate(tickers, start=1)
        }
        for future in as_completed(future_to_meta):
            idx, name, code = future_to_meta[future]
            print(f"[{idx}/{total}] 取得完了: {name} ({code})")
            try:
                row = future.result()
            except Exception as e:
                row = empty_row(name, code, str(e))
            rows.append(row)

    rows.sort(key=sort_key)
    return rows


def main():
    try:
        input_path = choose_file()
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    try:
        text = input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = input_path.read_text(encoding="utf-8-sig")

    tickers = parse_tickers_from_md(text)
    if not tickers:
        print("[ERROR] 監視銘柄.md から '銘柄名 (4桁コード)' を抽出できませんでした。")
        return

    print(f"監視銘柄数: {len(tickers)}")
    rows = fetch_all_rows(tickers)

    output_text = build_markdown(rows, input_path.name)
    output_path = input_path.parent / build_output_filename()
    atomic_write_text(output_path, output_text)

    print("")
    print(f"保存完了: {output_path}")


if __name__ == "__main__":
    main()
