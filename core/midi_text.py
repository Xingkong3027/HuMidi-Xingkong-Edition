from __future__ import annotations


def _midi_text_score(value: str) -> float:
    """Score a decoded MIDI text candidate for likely human readability."""
    score = 0.0
    for char in value:
        code = ord(char)
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            score += 5.0
        elif char.isalnum() or char in " _-()[]{}.,·—+&/\\":
            score += 0.35
        elif char.isprintable():
            score += 0.05
        else:
            score -= 8.0
        if char == "�":
            score -= 12.0
    # Typical UTF-8-as-Latin-1 mojibake fragments.
    score -= sum(value.count(mark) for mark in ("Ã", "Â", "æ", "ç", "å", "ä", "ð")) * 1.5
    return score


def decode_midi_text(value: str) -> str:
    """Recover per-field MIDI text encoded as UTF-8, GB18030, Big5 or Shift-JIS.

    The MIDI file is opened as Latin-1 so every byte maps reversibly to one
    Unicode code point.  This function then evaluates common real-world
    encodings for each track/instrument name independently.
    """
    if not value or any(0x3400 <= ord(ch) <= 0x9FFF for ch in value):
        return value
    try:
        raw = value.encode("latin1")
    except UnicodeEncodeError:
        return value

    candidates: list[tuple[int, str]] = [(99, value)]
    for priority, encoding in enumerate(("utf-8", "gb18030", "big5", "shift_jis")):
        try:
            decoded = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        candidates.append((priority, decoded))

    # Prefer the more likely text score; encoding priority resolves close ties.
    _priority, best = max(candidates, key=lambda pair: (_midi_text_score(pair[1]), -pair[0]))
    return best.strip("\x00")
