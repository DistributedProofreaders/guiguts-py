"""Script to extract links from manual & create wiki index.

Usage: From the repository root directory run
    poetry run python scripts/generate_wiki_index.py

For now, it just writes to "Guiguts_Index.wiki" in the current dir.
"""

import html

from bs4 import BeautifulSoup
import requests

# List of pages to fetch
pages = [
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

all_headings: list[tuple[str, str, str]] = []

for page in pages:
    print(f"Scraping {page}")
    url = BASE_URL + page
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        print(f"Warning: could not fetch {url}")
        continue

    # Iterate over all heading tags
    soup = BeautifulSoup(resp.text, "html.parser")
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        # Extract the text of the heading & the id
        span = h.find("span", class_="mw-headline")
        if span and span.get("id"):
            heading_text = html.unescape(span.get_text()).strip()
            # Remove leading "A" or "The" or period (e.g. ".json")
            heading_text = (
                heading_text.removeprefix("A ").removeprefix("The ").removeprefix(".")
            )
            heading_id = span["id"].replace("[", "%5B").replace("]", "%5D")
            all_headings.append((heading_text, page, heading_id))

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
            text = f"{text}, {page}"
        link = f"[[../{page}#{hid}|{text}]]"
        mw_lines.append(link + "\n")
    mw_lines.append("")


# Write to file
with open("Guiguts_Index.wiki", "w", encoding="utf-8") as f:
    f.write("\n".join(mw_lines))
