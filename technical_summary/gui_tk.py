from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    tk = None
    filedialog = None


def choose_file() -> Path:
    if tk is None or filedialog is None:
        raise RuntimeError("tkinter が使えません。CLIで入力ファイルを指定してください。")

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

