import re


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

