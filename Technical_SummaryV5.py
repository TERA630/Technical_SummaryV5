from pathlib import Path
import sys
from typing import Optional

from technical_summary.app import main as _main
from technical_summary.data import empty_row, fetch_all_rows, fetch_intraday_vwap, fetch_stock_row
from technical_summary.domain import calc_main_score, classify_row, compute_rsi, is_missing, is_strong_theme
from technical_summary.formatting import (
    fmt_price,
    fmt_price_diff,
    fmt_price_with_pct,
    fmt_pct,
    fmt_rsi,
    fmt_volume,
    fmt_volume_with_ratio,
    fmt_vwap_with_diff,
)
from technical_summary.gui_tk import choose_file
from technical_summary.io import atomic_write_text, build_output_filename
from technical_summary.parsing import parse_tickers_from_md
from technical_summary.report import build_markdown, build_table_for_category, sort_key


def main(input_path: Optional[Path] = None) -> None:
    _main(input_path)


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(input_path)
