"""Generate Guiguts confusables.json from Unicode's confusablesSummary.txt.

confusablesSummary.txt can be obtained from
https://www.unicode.org/Public/UCD/latest/security/confusablesSummary.txt

This script converts it to a json file for storing under the release in
src/guiguts/data/confusables/confusables.json

Characters are filtered to only include letters, and ignore some scripts
such as Arabic which has many similar-looking characters.
"""

import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Unicode contains confusable characters from many scripts which aren't
# particularly useful for the sort of documents Guiguts normally handles.
# We exclude those characters individually, rather than excluding a whole
# confusable group. Thus a Latin character can still be retained if another
# member of its group belongs to an excluded script.
EXCLUDED_SCRIPTS = (
    "ARABIC",
    "CANADIAN SYLLABICS",
    "CJK COMPATIBILITY IDEOGRAPH",
    "CJK UNIFIED IDEOGRAPH",
    "HANGUL CHOSEONG",
    "HANGUL JUNGSEONG",
    "HANGUL JONGSEONG",
    "HANGUL SYLLABLE",
    "TANGUT",
    "YI SYLLABLE",
)


def useful_character(char: str) -> bool:
    """Return whether character is a letter (and not in an excluded script)"""
    if len(char) != 1:
        return False

    name = unicodedata.name(char, "")
    if not name:
        return False

    if any(part in name for part in EXCLUDED_SCRIPTS):
        return False

    return unicodedata.category(char).startswith("L")


def parse_codepoint(line: str) -> str | None:
    """Extract the character represented by a confusablesSummary line."""
    fields = line.split("\t")

    # The format is:
    #
    #   ←    ( character )    CODEPOINT(S)    NAME
    #
    # The code-point field is therefore field 2. We deliberately use this
    # rather than trying to extract the character from the
    # second field, which contains invisible formatting characters.
    if len(fields) < 3:
        return None

    codepoints = fields[2].strip()

    if not codepoints:
        return None

    try:
        char = "".join(chr(int(codepoint, 16)) for codepoint in codepoints.split())
    except ValueError:
        return None

    return char


def read_confusables(source: Path) -> dict[str, set[str]]:
    """Read Unicode's confusablesSummary.txt."""
    confusables: dict[str, set[str]] = defaultdict(set)
    group: list[str] = []

    def finish_group() -> None:
        """Add useful single-character letter relationships."""
        useful = {char for char in group if useful_character(char)}

        for char in useful:
            confusables[char].update(useful - {char})

    for line in source.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("#"):
            finish_group()
            group = []
            continue

        if not stripped:
            continue

        char = parse_codepoint(line)

        if char is not None:
            group.append(char)

    finish_group()

    return dict(confusables)


def main() -> None:
    """Generate the filtered JSON file."""
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python scripts/make_confusables.py confusablesSummary.txt"
        )

    source = Path(sys.argv[1])

    destination = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "guiguts"
        / "data"
        / "confusables"
        / "confusables.json"
    )

    confusables = read_confusables(source)

    data = {
        char: sorted(chars, key=ord)
        for char, chars in sorted(confusables.items(), key=lambda item: ord(item[0]))
        if chars
    }

    destination.parent.mkdir(parents=True, exist_ok=True)

    destination.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )

    print(
        f"Wrote {len(data):,} characters "
        f"and {sum(len(chars) for chars in data.values()):,} relationships "
        f"to {destination}"
    )


if __name__ == "__main__":
    main()
