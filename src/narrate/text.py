"""Turn agent output (markdown) into speakable chunks."""

from __future__ import annotations

import re
import unicodedata

# Kokoro sounds best on utterances of roughly 100-200 tokens; for Portuguese
# that is about this many characters.
MAX_CHUNK_CHARS = 220
# A short first chunk makes speech start quickly; later chunks are
# synthesized while earlier ones play.
FIRST_CHUNK_CHARS = 80

_FENCE = re.compile(r"^\s*(```|~~~)")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}")
_HEADING = re.compile(r"^#{1,6}\s+")
_QUOTE = re.compile(r"^>\s?")
_LIST_MARKER = re.compile(r"^([-*+]|\d+[.)])\s+")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_STAR_EMPHASIS = re.compile(r"(\*\*|\*|~~)(?=\S)(.+?)(?<=\S)\1")
_UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)(__|_)(?=\S)(.+?)(?<=\S)\1(?!\w)")
_SNAKE_CASE_JOINER = re.compile(r"(?<=\w)_(?=\w)")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([.,!?;:])")
_MULTIPLE_SPACES = re.compile(r"\s{2,}")
_SENTENCE_END = re.compile(r"(?<=[.!?;:])\s+")
_CLAUSE_END = re.compile(r"(?<=,)\s+")
_ENDS_WITH_PUNCTUATION = ".!?:;,"


def _strip_symbols(line: str) -> str:
    # Emoji and other pictographs: espeak would spell out their names.
    return "".join(c for c in line if unicodedata.category(c) != "So")


def clean_markdown(text: str) -> str:
    """Drop code blocks and markdown syntax, keeping the prose."""
    lines: list[str] = []
    in_code = False
    for raw in text.splitlines():
        if _FENCE.match(raw):
            in_code = not in_code
            continue
        if in_code or _TABLE_SEPARATOR.match(raw):
            continue
        line = raw.strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            line = ", ".join(cells)
        line = _HEADING.sub("", line)
        line = _QUOTE.sub("", line)
        line = _LIST_MARKER.sub("", line)
        line = _LINK.sub(r"\1", line)
        line = _URL.sub("link", line)
        line = _INLINE_CODE.sub(r"\1", line)
        line = _STAR_EMPHASIS.sub(r"\2", line)
        line = _UNDERSCORE_EMPHASIS.sub(r"\2", line)
        line = _SNAKE_CASE_JOINER.sub(" ", line)
        line = _strip_symbols(line)
        line = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", line)
        line = _MULTIPLE_SPACES.sub(" ", line).strip()
        if not line:
            continue
        # Headings and list items have no final punctuation; without it they
        # run into the next line with no pause.
        if line[-1] not in _ENDS_WITH_PUNCTUATION:
            line += "."
        lines.append(line)
    return "\n".join(lines)


def split_chunks(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    first_max_chars: int = FIRST_CHUNK_CHARS,
) -> list[str]:
    """Group sentences into chunks of up to max_chars (first_max_chars for the first)."""
    pieces: list[str] = []
    for paragraph in text.split("\n"):
        for sentence in _SENTENCE_END.split(paragraph.strip()):
            if not sentence.strip():
                continue
            if len(sentence) > max_chars:
                pieces.extend(p for p in _CLAUSE_END.split(sentence) if p.strip())
            else:
                pieces.append(sentence)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        limit = max_chars if chunks else first_max_chars
        if current and len(current) + 1 + len(piece) > limit:
            chunks.append(current)
            current = piece
        else:
            current = f"{current} {piece}".strip()
    if current:
        chunks.append(current)
    return chunks
