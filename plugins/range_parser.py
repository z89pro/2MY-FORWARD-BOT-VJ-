import re
import logging
from typing import List, Tuple, Optional, Union

logger = logging.getLogger(__name__)

TG_LINK_RE = re.compile(
    r'(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/(?:c/)?([a-zA-Z0-9_]+)/(\d+)(?:-(\d+))?',
    re.IGNORECASE
)

NUM_RANGE_RE = re.compile(r'(\d+)\s*-\s*(\d+)')
SINGLE_NUM_RE = re.compile(r'\b(\d+)\b')


def merge_and_normalize_ranges(ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Sorts ranges and merges overlapping or immediately adjacent ranges.
    E.g. [(10, 20), (15, 25)] -> [(10, 25)]
    """
    if not ranges:
        return []
    # Ensure min <= max for each pair
    normalized = [(min(s, e), max(s, e)) for s, e in ranges]
    sorted_r = sorted(normalized, key=lambda x: x[0])
    merged = [sorted_r[0]]
    for cur_s, cur_e in sorted_r[1:]:
        prev_s, prev_e = merged[-1]
        if cur_s <= prev_e + 1:
            merged[-1] = (prev_s, max(prev_e, cur_e))
        else:
            merged.append((cur_s, cur_e))
    return merged


def parse_multi_ranges(
    text: str,
    default_chat_id: Optional[Union[int, str]] = None
) -> Tuple[Optional[Union[int, str]], List[Tuple[int, int]]]:
    """
    Parses flexible message range specifications from user input.
    Supports:
      - Single range link: 'https://t.me/c/123456789/10-50'
      - Two distinct links: 'https://t.me/c/123456789/10 https://t.me/c/123456789/50'
      - Multiple range links: 'https://t.me/c/123/10-20 https://t.me/c/123/30-40'
      - Mixed link + raw numbers: 'https://t.me/c/123/10-20, 25-30, 40-50'
      - Pure number ranges: '1-20, 30-40, 50-60' (when default_chat_id is provided)
    
    Returns:
      (chat_id, list_of_ranges) e.g. (-100123456789, [(10, 20), (30, 40)])
    """
    if not text:
        return default_chat_id, []

    clean_text = text.replace("?single", "").strip()
    tg_matches = list(TG_LINK_RE.finditer(clean_text))

    if tg_matches:
        first_match = tg_matches[0]
        raw_chat = first_match.group(1)
        chat_id = int("-100" + raw_chat) if raw_chat.isdigit() else raw_chat

        ranges = []

        # Special Case: User provided exactly 2 single-message links (start and end)
        if len(tg_matches) == 2 and not tg_matches[0].group(3) and not tg_matches[1].group(3):
            c1 = tg_matches[0].group(1)
            c2 = tg_matches[1].group(1)
            cid1 = int("-100" + c1) if c1.isdigit() else c1
            cid2 = int("-100" + c2) if c2.isdigit() else c2
            if cid1 != cid2:
                raise ValueError("Both links must be from the same channel!")
            m1 = int(tg_matches[0].group(2))
            m2 = int(tg_matches[1].group(2))
            ranges.append((m1, m2))
            return chat_id, merge_and_normalize_ranges(ranges)

        for m in tg_matches:
            c = m.group(1)
            cid = int("-100" + c) if c.isdigit() else c
            if cid != chat_id:
                raise ValueError("All links must be from the same channel!")
            start = int(m.group(2))
            end = int(m.group(3)) if m.group(3) else start
            ranges.append((start, end))

        # Check for remaining trailing numeric ranges (e.g. "https://t.me/c/123/10-20, 30-40")
        rem_text = TG_LINK_RE.sub("", clean_text)
        for nr in NUM_RANGE_RE.finditer(rem_text):
            s, e = int(nr.group(1)), int(nr.group(2))
            ranges.append((s, e))

        return chat_id, merge_and_normalize_ranges(ranges)

    elif default_chat_id:
        ranges = []
        for nr in NUM_RANGE_RE.finditer(clean_text):
            s, e = int(nr.group(1)), int(nr.group(2))
            ranges.append((s, e))
        return default_chat_id, merge_and_normalize_ranges(ranges)

    return None, []


def format_ranges_summary(ranges: List[Tuple[int, int]]) -> str:
    """Formats a list of ranges into a compact readable string."""
    if not ranges:
        return "None"
    return ", ".join(f"{s}-{e}" if s != e else str(s) for s, e in ranges)


def calculate_total_messages(ranges: List[Tuple[int, int]]) -> int:
    """Calculates total messages count across all parsed ranges."""
    return sum((end - start + 1) for start, end in ranges)
