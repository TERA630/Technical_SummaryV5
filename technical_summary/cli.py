import argparse
from pathlib import Path

from .app import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="監視銘柄Markdownからテクニカルサマリーを生成します。")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="入力Markdownファイル。省略時はローカル環境向けにTkinterのファイル選択を開きます。",
    )
    return parser.parse_args()


def cli_main() -> None:
    args = parse_args()
    main(args.input)


if __name__ == "__main__":
    cli_main()

