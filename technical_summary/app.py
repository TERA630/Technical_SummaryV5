from pathlib import Path
from typing import Optional

from .data import fetch_all_rows
from .gui_tk import choose_file
from .io import atomic_write_text, build_output_filename, read_text_utf8
from .parsing import parse_tickers_from_md
from .report import build_markdown


def run(input_path: Path) -> Path:
    text = read_text_utf8(input_path)
    tickers = parse_tickers_from_md(text)
    if not tickers:
        raise RuntimeError("監視銘柄.md から '銘柄名 (4桁コード)' を抽出できませんでした。")

    print(f"監視銘柄数: {len(tickers)}")
    rows = fetch_all_rows(tickers)

    output_text = build_markdown(rows, input_path.name)
    output_path = input_path.parent / build_output_filename()
    atomic_write_text(output_path, output_text)
    return output_path


def main(input_path: Optional[Path] = None) -> None:
    try:
        selected_path = input_path or choose_file()
        output_path = run(selected_path)
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    print("")
    print(f"保存完了: {output_path}")

