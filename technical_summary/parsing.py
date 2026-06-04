import re


def parse_tickers_from_md(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"^\s*(?:-\s*)?(?:\*\*)?\s*([^\n\(\*]+?)\s*\((\d{4})\)(?:\*\*)?")
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for line in text.splitlines():
        match = pattern.search(line)
        if not match:
            continue

        name, code = match.groups()
        cleaned_name = name.strip()
        if code not in seen:
            seen.add(code)
            results.append((cleaned_name, code))
    return results
