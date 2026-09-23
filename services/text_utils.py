import re
from difflib import SequenceMatcher, get_close_matches

_LATIN_TO_CYRILLIC = str.maketrans({
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н",
    "I": "І", "K": "К", "M": "М", "N": "Н", "O": "О",
    "P": "Р", "T": "Т", "V": "В", "X": "Х", "Y": "У",
})


def normalize_group_name(value: str) -> str:
    group = value.strip().replace("_", "-").replace("–", "-").replace("—", "-")
    group = re.sub(r"\s+", "", group).upper().translate(_LATIN_TO_CYRILLIC)
    group = re.sub(r"[^А-ЯІЇЄҐ0-9-]", "", group)
    group = re.sub(r"^([^\d-]+)(\d{3})$", r"\1-\2", group)
    return re.sub(r"-+", "-", group).strip("-")


def match_group_name(raw: str, candidates: list[str]) -> tuple[str | None, str, list[str]]:
    normalized = normalize_group_name(raw)
    canonical = sorted({normalize_group_name(candidate) for candidate in candidates if candidate})
    if normalized in canonical:
        return normalized, "matched", []

    closest = get_close_matches(normalized, canonical, n=3, cutoff=0.78)
    if not closest:
        return None, "unmatched", []
    scores = [SequenceMatcher(None, normalized, candidate).ratio() for candidate in closest]
    if len(closest) == 1 or scores[0] - scores[1] >= 0.05:
        return closest[0], "matched-fuzzy", closest
    return None, "unmatched", closest