"""Script to extract links from manual & create wiki index.

Usage: From the repository root directory run
    poetry run python scripts/generate_wiki_index.py

For now, it just writes to "Guiguts_Index.wiki" in the current dir.
"""

import argparse
import html

from bs4 import BeautifulSoup
import regex as re
import requests

parser = argparse.ArgumentParser()
parser.add_argument(
    "filenames",
    nargs="*",
    help="HTML files to read instead of scraping the wiki",
)
args = parser.parse_args()

# List of pages to fetch
PAGES = [
    "Introduction",
    "Navigation",
    "File_Menu",
    "Edit_Menu",
    "Search_Menu",
    "Tools_Menu",
    "Text_Menu",
    "HTML_Menu",
    "View_Menu",
    "Custom_Menu",
    "Help_Menu",
    "Content_Providing_Menu",
]

BASE_URL = "https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_2_Manual/"

INDEX_VERBS = {
    "add",
    "change",
    "configure",
    "create",
    "delete",
    "edit",
    "find",
    "goto",
    "insert",
    "move",
    "remove",
    "replace",
    "set",
    "show",
    "sort",
    "view",
}

INDEX_SPLIT_WORDS = {
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "to",
    "with",
}

pages: list[tuple[str, str]] = []

if args.filenames:
    for filename in args.filenames:
        print(f"Reading {filename}")

        with open(filename, encoding="utf-8") as f:
            page_html = f.read()

        # Extract the MediaWiki page name from the edit link.
        match = re.search(
            r'Guiguts_2_Manual/([^&"]+)',
            page_html,
        )

        if not match:
            print(f"Warning: could not determine page name from {filename}")
            continue

        page = match.group(1)
        pages.append((page, page_html))

else:
    for page in PAGES:
        print(f"Scraping {page}")
        url = BASE_URL + page
        resp = requests.get(url, timeout=10, cookies={"DP_Session": "1"})
        if resp.status_code != 200:
            print(f"Warning: could not fetch {url}")
            continue

        pages.append((page, resp.text))

all_headings: list[tuple[str, str, str]] = []


def add_heading(head_text, pg) -> None:
    """Pre-process then add index entry to list."""
    head_text = re.sub(r"^(a |the |and |\.)+", "", head_text, flags=re.IGNORECASE)
    heading_id = span["id"].replace("[", "%5B").replace("]", "%5D")
    all_headings.append((head_text, pg, heading_id))


for page, page_html in pages:
    soup = BeautifulSoup(page_html, "html.parser")

    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        span = h.find("span", class_="mw-headline")
        if not (span and span.get("id")):
            continue
        heading_text = html.unescape(span.get_text()).strip()
        add_heading(heading_text, page)

        words = heading_text.split()

        # If the heading starts with a recognised verb,
        # add an entry with the verb moved to the end.
        if len(words) >= 2 and words[0].lower() in INDEX_VERBS:
            index_text = f"{' '.join(words[1:])}, {words[0]}"
            add_heading(index_text, page)

        # Add an entry for each small connecting word.
        for i, word in enumerate(words):
            if 0 < i < len(words) - 1 and word.lower() in INDEX_SPLIT_WORDS:
                index_text = f"{' '.join(words[i + 1:])}, {' '.join(words[:i + 1])}"
                add_heading(index_text, page)

# Sort alphabetically by heading text
all_headings.sort(key=lambda x: x[0].lower())

# Group by first letter
grouped: dict[str, list[tuple[str, str, str]]] = {}
for text, page, hid in all_headings:
    first_char = text[0].upper()
    if not first_char.isalpha():
        first_char = "#"
    if first_char not in grouped:
        grouped[first_char] = []
    grouped[first_char].append((text, page, hid))

# Generate MediaWiki text - A-Z contents links first
mw_lines = [
    "__NOTOC__",
    "{{../Current_Version}}\n",
    "==Contents==\n",
    '<div style="font-size: 1.1em; border: thin solid gray; padding: .5em; background-color: #F8F9FA;">',
]

mw_lines.append(", ".join(f"[[#{let}|{let}]]" for let in sorted(grouped.keys())))
mw_lines.append("</div>\n")


for letter in sorted(grouped.keys()):
    mw_lines.append(f"=={letter}==\n")
    for text, page, hid in grouped[letter]:
        page = page.replace("_", " ")
        # Don't duplicate text, e.g. "File Menu, File Menu"
        if page != text:
            text = f"{text} | {page}"
        link = f"[[../{page}#{hid}|{text}]]"
        mw_lines.append(link + "\n")
    mw_lines.append("")


# Write to file
with open("Guiguts_Index.wiki", "w", encoding="utf-8") as f:
    f.write("\n".join(mw_lines))
