from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import yfinance as yf

from .config import MAX_WORKERS, VOLUME_AVG_DAYS
from .domain import calc_main_score, classify_row, compute_rsi, is_strong_theme
from .report import sort_key


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

