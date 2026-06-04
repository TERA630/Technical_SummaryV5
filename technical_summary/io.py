import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional


def read_text_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")


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

