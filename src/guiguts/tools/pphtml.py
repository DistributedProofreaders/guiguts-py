"""PPhtml tool."""

from dataclasses import dataclass
from html.parser import HTMLParser
import os.path
from textwrap import wrap
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from PIL import Image
import regex as re

from guiguts.checkers import CheckerDialog, CheckerEntryType
from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.preferences import preferences, PrefKey, PersistentBoolean
from guiguts.utilities import IndexRange, IndexRowCol, sing_plur


class PPhtmlCheckerDialog(CheckerDialog):
    """Dialog to show PPhtml results."""

    manual_page = "HTML_Menu#PPhtml"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize PPhtml dialog."""
        super().__init__(
            "PPhtml Results",
            tooltip="\n".join(
                [
                    "Left click: Select & find error",
                    "Right click: Hide error",
                    "Shift Right click: Hide all matching errors",
                ]
            ),
            **kwargs,
        )
        ttk.Checkbutton(
            self.custom_frame,
            text="Verbose",
            variable=PersistentBoolean(PrefKey.PPHTML_VERBOSE),
        ).grid(row=0, column=0, sticky="NSEW")


@dataclass
class PPhtmlFileData:
    """Class to hold info about an image file."""

    width: int
    height: int
    format: Optional[str]
    mode: str
    filesize: int


class PPhtmlChecker:
    """PPhtml checker"""

    def __init__(self) -> None:
        """Initialize PPhtml checker."""
        self.dialog = PPhtmlCheckerDialog.show_dialog(rerun_command=self.run)
        self.images_dir = ""
        self.image_files: list[str] = []  # list of files in images folder
        # dict of image file information (width, height, format, mode, filesize)
        self.filedata: dict[str, PPhtmlFileData] = {}
        self.file_text = ""  # Text of file
        self.file_lines: list[str] = []  # Text split into lines
        self.links: dict[str, list[IndexRange]] = {}
        self.targets: dict[str, list[IndexRange]] = {}
        self.used_classes: set[str] = set()
        self.defined_classes: set[str] = set()

    def reset(self) -> None:
        """Reset PPhtml checker."""
        self.dialog.reset()
        self.images_dir = os.path.join(os.path.dirname(the_file().filename), "images")
        self.image_files = []
        self.filedata = {}
        self.file_text = maintext().get_text()
        self.file_lines = self.file_text.split("\n")
        self.links = {}
        self.targets = {}
        self.used_classes = set()
        self.defined_classes = set()

    def run(self) -> None:
        """Run PPhtml."""
        self.reset()
        self.image_tests()
        self.link_tests()
        self.ppv_tests()
        self.pg_tests()
        self.test_css()
        self.misc_checks()

        self.dialog.display_entries()
        # Select first entry (which might not be one with a line number)
        self.dialog.select_entry_by_index(0)

    # Image tests

    def image_tests(self) -> None:
        """Various checks relating to image files."""

        # find filenames of all the images
        self.add_section("Image Checks")
        if not os.path.isdir(self.images_dir):
            self.dialog.add_entry("*** No images folder found ***")
            return
        self.image_files = [
            fn
            for fn in os.listdir(self.images_dir)
            if os.path.isfile(os.path.join(self.images_dir, fn))
        ]
        self.scan_images()
        self.all_images_used()
        self.all_targets_available()
        self.image_file_sizes()
        self.image_dimensions()
        if preferences.get(PrefKey.PPHTML_VERBOSE):
            self.image_summary()

    def scan_images(self) -> None:
        """Scan each image, getting size, checking filename, etc."""
        errors = []
        test_passed = True
        # Check filenames
        for filename in self.image_files:
            if " " in filename:
                errors.append(f"  Filename '{filename}' contains spaces")
                test_passed = False
            if re.search(r"\p{Lu}", filename):
                errors.append(f"  Filename '{filename}' not all lower case")
                test_passed = False

        # Make sure all are JPEG, PNG or SVG images
        for filename in self.image_files:
            filepath = os.path.join(self.images_dir, filename)
            _, extension = os.path.splitext(filename.lower())
            fsize = os.path.getsize(filepath)
            if extension in (".jpg", ".jpeg", ".png"):
                try:
                    with Image.open(filepath) as im:
                        self.filedata[filename] = PPhtmlFileData(
                            im.width,
                            im.height,
                            im.format,
                            im.mode,
                            fsize,
                        )
                except IOError:
                    errors.append(
                        f"  File '{filename}' is not valid {'PNG' if extension == '.png' else 'JPG'} format"
                    )
                    test_passed = False
                    continue
            elif extension == ".svg":
                with open(filepath, "r", encoding="utf-8") as file:
                    file_contents = file.read()
                # Check start of file is compatible with it being SVG format
                if re.match(
                    r"(?:<\?xml\b[^>]*>[^<]*)?(?:<!--.*?-->[^<]*)*(?:<svg|<!DOCTYPE svg)\b",
                    file_contents,
                ):
                    self.filedata[filename] = PPhtmlFileData(0, 0, "SVG", "", fsize)
                else:
                    errors.append(f"  File '{filename}' is not valid SVG format")
                    test_passed = False
                    continue
            else:
                errors.append(
                    f"  File '{filename}' does not have extension jpg, png or svg"
                )
                test_passed = False
                continue
            if self.filedata[filename].format not in ("JPEG", "PNG", "SVG"):
                errors.append(
                    f"  File '{filename}' is of type {self.filedata[filename].format}"
                )
                test_passed = False
        self.output_subsection_errors(
            test_passed, "Image folder consistency tests", errors
        )

    def all_images_used(self) -> None:
        """Verify all images in the images folder are used in the HTML."""
        errors = []
        test_passed = True
        count_images = 0
        for fn in self.filedata:
            count_images += 1
            if f"images/{fn}" not in self.file_text:
                errors.append(f"  Image '{fn}' not used in HTML")
                test_passed = False
        self.output_subsection_errors(
            test_passed, "Image folder files used in the HTML", errors
        )

    def all_targets_available(self) -> None:
        """Verify all target images in HTML are available in images folder."""
        errors = []
        test_passed = True
        for match in re.finditer(
            r"(?<=images/)[\p{Lowercase_Letter}-_\d]+\.(jpg|jpeg|png)", self.file_text
        ):
            filename = match[0]
            if filename not in self.filedata:
                errors.append(
                    f"  Image '{filename}' referenced in HTML not in images folder"
                )
                test_passed = False
        self.output_subsection_errors(
            test_passed, "Target images in HTML available in images folder", errors
        )

    def image_file_sizes(self) -> None:
        """Show image sizes, and warn/error about large images."""
        errors = []
        test_passed = True
        size_list = sorted(
            [(fname, data.filesize) for fname, data in self.filedata.items()],
            key=lambda tup: tup[1],
            reverse=True,
        )
        for fname, fsize in size_list:
            if fsize > 1024 * 1024:
                severity = "ERROR: "
                test_passed = False
            elif fsize > 256 * 1024:
                severity = "WARNING: "
            else:
                severity = ""
            errors.append(f"  {severity}{fname} ({int(fsize / 1024)}K)")
        self.output_subsection_errors(test_passed, "Image File Sizes", errors)

    def image_dimensions(self) -> None:
        """Cover image width should be >=1600 px and height should be >= 2560 px.
        Other images must be <= 5000x5000."""
        errors: list[str] = []
        test_passed = True
        for fname, filedata in self.filedata.items():
            wd = filedata.width
            ht = filedata.height
            if fname == "cover.jpg" and ht < wd:
                errors.insert(
                    0,
                    f"  INFO: {fname} is landscape format: {wd}x{ht}",
                )
            if fname == "cover.jpg" and ht >= wd and (wd < 1600 or ht < 2560):
                errors.insert(
                    0,
                    f"  WARNING: {fname} too small (actual: {wd}x{ht}; recommended >= 1600x2560)",
                )
                test_passed = False
            elif fname == "cover.jpg" and ht < wd and (wd < 2560 or ht < 1600):
                errors.insert(
                    0,
                    f"  WARNING: {fname} too small (actual: {wd}x{ht}; recommended >= 2560x1600)",
                )
                test_passed = False
            elif wd > 5000 or ht > 5000:
                errors.insert(
                    0,
                    f"  WARNING: {fname} too large (actual: {wd}x{ht}; recommended <= 5000x5000)",
                )
                test_passed = False

        self.output_subsection_errors(test_passed, "Image Dimensions Check", errors)

    def image_summary(self) -> None:
        """Show information about image (verbose mode only)."""
        type_desc = {
            "1": "(1-bit pixels, black and white, stored with one pixel per byte)",
            "L": "(8-bit pixels, black and white)",
            "P": "(8-bit pixels, mapped to any other mode using a color palette)",
            "RGB": "(3x8-bit pixels, true color)",
            "RGBA": "(4x8-bit pixels, true color with transparency mask)",
            "CMYK": "(4x8-bit pixels, color separation)",
            "YCbCr": "(3x8-bit pixels, color video format)",
            "LAB": "(3x8-bit pixels, the L*a*b color space)",
            "HSV": "(3x8-bit pixels, Hue, Saturation, Value color space)",
            "I": "(32-bit signed integer pixels)",
            "F": "(32-bit floating point pixels)",
        }

        messages = []
        for fname, filedata in self.filedata.items():
            mode_desc = type_desc.get(filedata.mode, filedata.mode)
            size_desc = (
                f"{filedata.width}x{filedata.height}, "
                if filedata.width != 0 or filedata.height != 0
                else ""
            )
            messages.append(f"  {fname}, {size_desc}{filedata.format} {mode_desc}")
        self.output_subsection_errors(None, "Image Summary", messages)

    # Link tests

    def link_tests(self) -> None:
        """Consolidated link tests."""
        self.add_section("Link Tests")

        self.external_links()
        self.link_to_cover()
        self.find_links()
        self.find_targets()
        self.link_counts()
        self.do_resolve()

    def external_links(self) -> None:
        """Report and external href links."""
        errors: list[tuple[str, Optional[IndexRange]]] = []
        test_passed = True
        count_links = 0
        for line_num, line in enumerate(self.file_lines):
            if match := re.search(r"https?://[^'\"\) ]*", line):
                test_passed = False
                if count_links <= 10:
                    start = IndexRowCol(line_num + 1, match.span()[0])
                    end = IndexRowCol(line_num + 1, match.span()[1])
                    errors.append(
                        (f"External link: {match[0]}", IndexRange(start, end))
                    )
                if not preferences.get(PrefKey.PPHTML_VERBOSE):
                    count_links += 1
        self.output_subsection_errors(test_passed, "External Links Check", errors)
        if count_links > 10:
            self.dialog.new_section()
            self.dialog.add_entry(
                "  (more external links not reported)",
                entry_type=CheckerEntryType.FOOTER,
            )

    def link_to_cover(self) -> None:
        """Check that an epub cover has been provided:
        1. id of "coverpage" on an image
        2. `link rel="icon"` in header
        3. file named "cover.jpg" or "cover.png" in images folder
        """
        title = "Link to cover image for epub"
        test_passed = False
        if re.search("id *= *['\"]coverpage['\"]", self.file_text):
            test_passed = True
            title += " (using id='coverpage' on image)"
        elif re.search("rel *= *['\"]icon['\"]", self.file_text):
            test_passed = True
            title += " (using link rel='icon')"
        elif "cover.jpg" in self.filedata:
            test_passed = True
            title += " (found cover.jpg in images folder)"
        elif "cover.png" in self.filedata:
            test_passed = True
            title += " (found cover.png in images folder)"
        self.output_subsection_errors(test_passed, title, [])

    def find_links(self) -> None:
        """Build dictionary of IndexRanges where internal link occurs, keyed on target name."""
        link_count = 0
        for line_num, line in enumerate(self.file_lines):
            for match in re.finditer(r"href\s*=\s*[\"']#(.*?)[\"']", line):
                link_count += 1
                tgt = match[1]
                idx_range = IndexRange(
                    IndexRowCol(line_num + 1, match.start()),
                    IndexRowCol(line_num + 1, match.end()),
                )
                if tgt in self.links:
                    self.links[tgt].append(idx_range)
                else:
                    self.links[tgt] = [idx_range]
        self.output_subsection_errors(
            None,
            f"File has {link_count} internal links to {len(self.links)} expected targets",
            [],
        )

    def find_targets(self) -> None:
        """Build dictionary of IndexRanges where targets occur, keyed on target name.
        Should be only one for each id."""

        class IDHTMLParser(HTMLParser):
            """Parse HTML file to get ID attributes of all elements"""

            def __init__(self) -> None:
                """Initialize HTML ID parser."""
                super().__init__()
                self.ids: dict[str, list[IndexRange]] = {}

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                if tag == "meta":
                    return
                tag_index = self.getpos()
                tag_start = IndexRowCol(tag_index[0], tag_index[1])
                id_name = None
                for attr in attrs:
                    if attr[0] == "id":
                        id_name = attr[1]
                        break
                if id_name is None:
                    return
                tag_text = self.get_starttag_text()
                assert tag_text is not None  # Can never happen in this method
                idx_range = IndexRange(
                    tag_start,
                    maintext().rowcol(f"{tag_start.index()}+{len(tag_text)}c"),
                )
                try:
                    self.ids[id_name].append(idx_range)
                except KeyError:
                    self.ids[id_name] = [idx_range]

        parser = IDHTMLParser()
        parser.feed(self.file_text)
        self.targets = parser.ids

        errors: list[tuple[str, Optional[IndexRange]]] = []
        test_passed = True
        for tgt, idx_ranges in self.targets.items():
            if len(idx_ranges) > 1:
                test_passed = False
                for idx_range in idx_ranges:
                    errors.append((f"Duplicate id: {tgt}", idx_range))
        self.output_subsection_errors(
            test_passed,
            f"Duplicate ID Check (file has {len(self.targets)} unique IDs)",
            errors,
        )

    def link_counts(self) -> None:
        """Check for multiple links to the same ID, and report number of image links."""
        errors: list[tuple[str, Optional[IndexRange]]] = []
        test_passed = True
        num_reused = 0
        for tgt, idx_ranges in self.links.items():
            if len(idx_ranges) > 1:
                test_passed = False
                num_reused += 1
                for idx_range in idx_ranges:
                    errors.append((f"WARNING: Multiple links to id {tgt}", idx_range))
        if num_reused <= 5:
            self.output_subsection_errors(
                test_passed,
                "Check for IDs targeted by multiple links",
                errors,
            )
        else:
            self.output_subsection_errors(
                None,
                f"Not reporting {num_reused} IDs linked to more than once (file may have an index)",
                [],
            )

        im_count = 0
        inc_cover = ""
        for match in re.finditer(r'href=["\']images/(.*?)["\']', self.file_text):
            if match[1].startswith("cover."):
                inc_cover = f" (including {match[1]})"
            im_count += 1
        if im_count > 0:
            self.output_subsection_errors(
                None,
                f"File has {sing_plur(im_count, 'link')} to images{inc_cover}",
                [],
            )

    def do_resolve(self) -> None:
        """Every link must go to one link target that exists (or flag missing link target).
        Every target should come from one or more links (or flag unused target)
        """
        errors: list[tuple[str, Optional[IndexRange]]] = []
        test_passed = True
        for alink, idx_ranges in self.links.items():
            if alink not in self.targets:
                test_passed = False
                for idx_range in idx_ranges:
                    errors.append((f"  Target {alink} not found", idx_range))
        self.output_subsection_errors(
            test_passed, "Check links point to valid targets", errors
        )

        reported = 0
        report_limit = 20
        untargeted = []
        for atarget in self.targets:
            if atarget not in self.links:
                reported += 1
                if reported > report_limit:
                    break
                untargeted.append(atarget)
        join_string = ", ".join(untargeted)
        wrapped_lines = wrap(
            join_string, width=60, initial_indent="  ", subsequent_indent="  "
        )
        if reported > report_limit:
            wrapped_lines[-1] += " ... more not reported"
        self.output_subsection_errors(
            None, "Check for unreferenced targets", wrapped_lines
        )

    # PPV tests

    def ppv_tests(self) -> None:
        """Consolidated tests particular to DP PPV."""
        self.add_section("DP PPV Tests")

        self.h1_title()
        self.pre_tags()
        self.charset_check()
        self.dtd_check()
        self.alt_tags()
        self.lang_check()
        self.heading_outline()

    def h1_title(self) -> None:
        """Find what's in <title> and compare to what's in <h1>"""
        h1_cnt = title_cnt = 0
        h1_str = title_str = ""
        for match in re.finditer(
            r"<title>(.*?)</title>", self.file_text, flags=re.DOTALL
        ):
            title_cnt += 1
            if title_cnt > 1:
                break
            title_str = match.group(1)
        for match in re.finditer(
            r"<h1( .+?)?>(.*?)</h1>", self.file_text, flags=re.DOTALL
        ):
            h1_cnt += 1
            if h1_cnt > 1:
                break
            h1_str = match.group(2)

        if title_cnt == 0:
            self.output_subsection_errors(
                False, "Title/h1 check: missing <title>...</title>", []
            )
        elif title_cnt > 1:
            self.output_subsection_errors(
                False, "Title/h1 check: too many <title>...</title>", []
            )
        if h1_cnt == 0:
            self.output_subsection_errors(
                False, "Title/h1 check: missing <h1>...</h1>", []
            )
        elif h1_cnt > 1:
            self.output_subsection_errors(
                False, "Title/h1 check: too many <h1>...</h1>", []
            )
        if title_cnt != 1 or h1_cnt != 1:
            return

        title_str = re.sub(r"\s+", " ", title_str.strip())
        h1_str = re.sub(r"<br.*?>", " ", h1_str.strip())
        h1_str = re.sub(r"<.*?>", "", h1_str)
        h1_str = re.sub(r"\s+", " ", h1_str)
        test_passed = title_str.endswith(" | Project Gutenberg")
        errors: list[tuple[str, Optional[IndexRange]]] = []
        if not test_passed:
            errors.append(
                (
                    '    Title should be of the form "Alice’s Adventures in Wonderland | Project Gutenberg"',
                    None,
                )
            )
        rowcol = IndexRowCol(maintext().search("<title>", "1.0", tk.END))
        errors.append((f"title: {title_str}", IndexRange(rowcol, rowcol)))
        rowcol = IndexRowCol(maintext().search("<h1[ >]", "1.0", tk.END, regexp=True))
        errors.append((f"   h1: {h1_str}", IndexRange(rowcol, rowcol)))

        self.output_subsection_errors(test_passed, "Title/h1 check", errors)

    def pre_tags(self) -> None:
        """Check no pre tags in HTML."""
        errors: list[tuple[str, Optional[IndexRange]]] = []
        count = 0
        for line_num, line in enumerate(self.file_lines):
            if match := re.search("<pre( .+?)?>", line):
                start = IndexRowCol(line_num + 1, match.start())
                if end_idx := maintext().search("</pre>", start.index(), tk.END):
                    end = IndexRowCol(end_idx)
                    end.col += 6
                    msg_text = maintext().get(start.index(), end.index())
                    if len(msg_text) > 35:
                        msg_text = msg_text[0:31] + "..."
                else:
                    end = IndexRowCol(line_num + 1, match.end())
                    msg_text = "No matching </pre> found"
                idx_range = IndexRange(
                    start,
                    end,
                )
                errors.append((f"Use of <pre> tag: {msg_text}", idx_range))
                count += 1
        count_str = "" if count == 0 else f" ({count} found)"
        self.output_subsection_errors(
            len(errors) == 0, f"<pre> tags check{count_str}", errors
        )

    def charset_check(self) -> None:
        """Character set should be UTF-8."""
        if match := re.search("charset *= *['\"](.*?)['\"]", self.file_text):
            charset = match.group(1)
            test_passed = charset.lower() == "utf-8"
            msg = f"Charset is {charset}"
        else:
            test_passed = False
            msg = "No charset found"
        self.output_subsection_errors(test_passed, msg, [])

    def dtd_check(self) -> None:
        """Check for valid HTML5 document type header."""
        if "<!DOCTYPE html>" in self.file_lines[0]:
            self.output_subsection_errors(
                True, "Document Type Header (file is HTML5)", []
            )
        else:
            self.output_subsection_errors(False, "Document Type Header not HTML5", [])

    def lang_check(self) -> None:
        """Show user what document claims is the language."""
        if match := re.search(r"<html.+?lang *= *['\"](.+?)['\"]", self.file_text):
            self.output_subsection_errors(
                True, f"Language code check: {match.group(1)}", []
            )
        else:
            self.output_subsection_errors(
                False, "Language code check: none specified", []
            )

    def alt_tags(self) -> None:
        """All img tags get evaluated for alt behavior."""

        class AltTagHTMLParser(HTMLParser):
            """Parse HTML file to check alt tags of img elements"""

            def __init__(self) -> None:
                """Initialize HTML alt tag parser."""
                super().__init__()
                self.alts: list[tuple[str | None, IndexRange]] = []
                self.tag_start = IndexRowCol(0, 0)
                self.alt: Optional[str] = None

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                """Handle img start tag - grab alt if any."""
                if tag != "img":
                    return
                tag_index = self.getpos()
                self.tag_start = IndexRowCol(tag_index[0], tag_index[1])
                self.alt = None
                for attr in attrs:
                    if attr[0] == "alt":
                        self.alt = attr[1]
                        break
                tag_text = self.get_starttag_text()
                assert tag_text is not None  # Can never happen in this method
                self.alts.append(
                    (
                        self.alt,
                        IndexRange(
                            self.tag_start,
                            maintext().rowcol(
                                f"{self.tag_start.index()}+{len(tag_text)}c"
                            ),
                        ),
                    )
                )

        parser = AltTagHTMLParser()
        parser.feed(self.file_text)
        errors: list[tuple[str, Optional[IndexRange]]] = []
        alt_is_missing = 0
        alt_is_empty = 0
        alt_is_blank = 0
        alt_is_text = 0
        for alt, pos in parser.alts:
            if alt is None:
                errors.append(("Img has no alt tag", pos))
                alt_is_missing += 1
            elif alt == "":
                alt_is_empty += 1
            elif alt.isspace():
                errors.append(("Non-empty blank alt string", pos))
                alt_is_blank += 1
            else:
                alt_is_text += 1
        test_passed = alt_is_missing == 0 and alt_is_blank == 0
        summary: list[tuple[str, Optional[IndexRange]]] = []
        sum_missing_text = "" if alt_is_missing == 0 else " (ERROR)"
        sum_blank_text = "" if alt_is_missing == 0 else " (ERROR)"
        summary.append(
            (
                f"   {alt_is_missing} images with missing alt tags{sum_missing_text}",
                None,
            )
        )
        summary.append(
            (f"   {alt_is_blank} images with blank alt tags{sum_blank_text}", None)
        )
        summary.append((f"   {alt_is_empty} images with empty alt tags", None))
        summary.append((f"   {alt_is_text} images with textual alt tags", None))
        self.output_subsection_errors(
            test_passed, "Image Alt Tag Tests", summary + errors
        )

    def heading_outline(self) -> None:
        """Output Document Heading Outline."""

        class OutlineHTMLParser(HTMLParser):
            """Parse HTML file to get document outline of h1-h6 elements"""

            h1_6_tags = ("h1", "h2", "h3", "h4", "h5", "h6")

            def __init__(self) -> None:
                """Initialize HTML outline parser."""
                super().__init__()
                self.outline: list[tuple[str, IndexRange | None]] = []
                self.tag = ""
                self.showh = False
                self.tag_start = IndexRowCol(0, 0)

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                """Handle h1-h6 start tag."""
                if tag in self.h1_6_tags:
                    self.tag = tag + ": "
                    self.showh = True
                    tag_index = self.getpos()
                    self.tag_start = IndexRowCol(tag_index[0], tag_index[1])

            def handle_data(self, data: str) -> None:
                """Get contents of h1-h6 tag."""
                if self.showh:
                    self.tag = self.tag + " " + data

            def handle_endtag(self, tag: str) -> None:
                """Handle h1-h6 end tag."""
                if tag in self.h1_6_tags:
                    self.showh = False
                    self.tag = self.tag.rstrip()
                    self.tag = re.sub(r"\s+", " ", self.tag)
                    match = re.match(r"h(\d)", self.tag)
                    if match:
                        indent = "  " * (int(match.group(1)) - 1)
                        tag_index = self.getpos()
                        self.outline.append(
                            (
                                indent + self.tag,
                                IndexRange(
                                    self.tag_start,
                                    IndexRowCol(tag_index[0], tag_index[1] + 5),
                                ),
                            )
                        )

        parser = OutlineHTMLParser()
        parser.feed(self.file_text)
        self.output_subsection_errors(None, "Document Heading Outline", parser.outline)

    # PG checks

    def pg_tests(self) -> None:
        """Consolidated tests particular to Project Gutenberg."""
        self.add_section("Project Gutenberg Tests")
        self.classchcount()

    def classchcount(self) -> None:
        """Class chapter count and h2 count summary."""

        class ChapterHTMLParser(HTMLParser):
            """Parse HTML file to count `class="chapter"` and `h2`."""

            def __init__(self) -> None:
                """Initialize HTML outline parser."""
                super().__init__()
                self.cchcount = 0
                self.h2count = 0

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                """Handle start tags, count "chapter" divs and h2's."""
                if tag == "div":
                    for attr in attrs:
                        if (
                            attr[0] == "class"
                            and attr[1] is not None
                            and "chapter" in attr[1].split()
                        ):
                            self.cchcount += 1
                            return
                elif tag == "h2":
                    self.h2count += 1

        parser = ChapterHTMLParser()
        parser.feed(self.file_text)
        self.output_subsection_errors(
            None,
            f'{parser.h2count} <h2> tags; {parser.cchcount} class="chapter" attributes',
            [],
        )

    # CSS checks

    def test_css(self) -> None:
        """CSS tests."""
        self.add_section("CSS Tests")

        self.find_used_css()
        self.find_defined_css()
        self.resolve_css()

    def find_used_css(self) -> None:
        """Find CSS classes used in HTML class attributes."""

        class ClassHTMLParser(HTMLParser):
            """Parse HTML file to find `class="..."`."""

            def __init__(self) -> None:
                """Initialize HTML outline parser."""
                super().__init__()
                self.classes: set[str] = set()

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                """Handle start tags to find classes used."""
                for attr in attrs:
                    if attr[0] == "class" and attr[1] is not None:
                        self.classes.update(attr[1].split())
                        break

        parser = ClassHTMLParser()
        parser.feed(self.file_text)
        self.used_classes = parser.classes

    def find_defined_css(self) -> None:
        """Find CSS classes user has defined."""
        # Find all <style> blocks and concatenate them
        css_content = "\n".join(
            match.group(1).strip()
            for match in re.finditer(
                r"<style.*?>(.*?)</style>",
                self.file_text,
                flags=re.DOTALL | re.IGNORECASE,
            )
        )

        self.defined_classes = set()
        split_content = css_content.split("\n")

        # Strip out any comments in css
        lnum = 0
        while lnum < len(split_content):
            # Single line
            if split_content[lnum].strip().startswith("/*") and split_content[
                lnum
            ].strip().endswith("*/"):
                del split_content[lnum]
                continue
            # Nulti line
            if split_content[lnum].strip().startswith("/*"):
                del split_content[lnum]
                while not split_content[lnum].strip().endswith("*/"):
                    del split_content[lnum]
                del split_content[lnum]
            lnum += 1

        # Unwrap CSS to put whole of {...} on one line
        lnum = 0
        while lnum < len(split_content):
            # Keep joining lines until number of open/close braces are equal
            while lnum < len(split_content) - 1 and (
                split_content[lnum].count("{") != split_content[lnum].count("}")
            ):
                split_content[lnum] = (
                    split_content[lnum] + " " + split_content[lnum + 1]
                )
                del split_content[lnum + 1]
            # Warn user if we didn't manage to get open/close braces to match
            if split_content[lnum].count("{") != split_content[lnum].count("}"):
                line = re.sub(r"\s+", " ", split_content[lnum]).strip()
                if len(line) > 40:
                    line = line[0:40] + "..."
                self.output_subsection_errors(
                    False,
                    f"Runaway CSS block near: {line}",
                    [],
                )
                return
            lnum += 1

        for lnum, _ in enumerate(split_content):
            # Remove @media bracketing
            if "@media" in split_content[lnum]:
                split_content[lnum] = re.sub(r"@media.*?{", "", split_content[lnum])
                split_content[lnum] = re.sub(r"}$", "", split_content[lnum])
            # Remove declaration blocks: ".large { font-size: large; }" -> ".large"
            split_content[lnum] = re.sub(r"{[^}]+}", "", split_content[lnum])
            # Remove child combinator ">" div.linegroup > :first-child
            split_content[lnum] = re.sub(r">", "", split_content[lnum])
            # Remove element types: "hr.pb" -> ".pb"
            split_content[lnum] = re.sub(
                r"(?<![-\.\w])\w+(\.\w+)", r"\1", split_content[lnum]
            )

        for line in split_content:
            line = line.replace(".", " .")  # ".poem.apdx" becomes " .poem .apdx"
            line = line.replace(",", " ")  # splits h1,h2,h3
            line = re.sub("  +", " ", line)
            line = line.strip()
            for a_class in line.split(" "):
                # Classes that are not pseudo-classes
                if a_class.startswith(".") and ":" not in a_class:
                    self.defined_classes.add(a_class[1:])

    def resolve_css(self) -> None:
        """Resolve CSS classes used and defined."""

        join_string = ", ".join(sorted(self.defined_classes))
        wrapped_lines = wrap(
            join_string, width=60, initial_indent="  ", subsequent_indent="  "
        )
        self.output_subsection_errors(
            None,
            "Defined classes",
            wrapped_lines,
        )
        join_string = ", ".join(sorted(self.used_classes))
        wrapped_lines = wrap(
            join_string, width=60, initial_indent="  ", subsequent_indent="  "
        )
        self.output_subsection_errors(
            None,
            "Used classes",
            wrapped_lines,
        )

        # Classes used but not defined
        difference = [
            cl
            for cl in self.used_classes.difference(self.defined_classes)
            if not cl.startswith("x-ebookmaker")
        ]
        join_string = ", ".join(sorted(difference))
        wrapped_lines = wrap(
            join_string, width=60, initial_indent="  ", subsequent_indent="  "
        )
        self.output_subsection_errors(
            len(wrapped_lines) == 0,
            "Classes used but not defined",
            wrapped_lines,
        )

        # Classes defined but not used
        difference = [
            cl
            for cl in self.defined_classes.difference(self.used_classes)
            if not cl.startswith("x-ebookmaker")
        ]
        join_string = ", ".join(sorted(difference))
        wrapped_lines = wrap(
            join_string, width=60, initial_indent="  ", subsequent_indent="  "
        )
        self.output_subsection_errors(
            len(wrapped_lines) == 0,
            "Classes defined but not used",
            wrapped_lines,
            fail_string="*WARN*",
        )

    # Miscellaneous checks

    def misc_checks(self) -> None:
        """Miscellaneous checks taken from PPWB pphtml python and GG pphtml Perl tools."""
        self.add_section("Miscellaneous checks")

        self.misc_counts()
        self.misc_specials()
        self.misc_styles()

    def misc_counts(self) -> None:
        """Miscellaneous counting checks"""
        # "--" emdashes, ignoring HTML comments (typically from ppgen)
        count = 0
        for line in self.file_lines:
            if "<!--" not in line and "-->" not in line and "--" in line:
                count += 1
        self.output_subsection_errors(
            count == 0,
            f'Lines with "--" instead of "—" (should be 0): {count}',
            [],
        )
        # h2 headings
        count = self.file_text.count("<h2")
        self.output_subsection_errors(
            count > 0,
            f"Number of h2 tags (usually chapters; should be > 0): {count}",
            [],
        )
        # h3 headings
        count = self.file_text.count("<h3")
        self.output_subsection_errors(
            None,
            f"Number of h3 tags (usually sections): {count}",
            [],
        )
        # Tables
        count = self.file_text.count("<table")
        self.output_subsection_errors(
            None,
            f"Number of tables: {count}",
            [],
        )

    def misc_specials(self) -> None:
        """Check for markup etc. that has not been fully processed."""
        errors: list[tuple[str, Optional[IndexRange]]] = []
        for line_num, line in enumerate(self.file_lines):
            match: Optional[re.Match[str]]
            if match := re.search(r"\[Illustration", line):
                errors.append(
                    ("Unconverted illustration", self.idx_range(line_num, match))
                )
            if match := re.search(r"\[Sidenote", line):
                errors.append(("Unconverted sidenote", self.idx_range(line_num, match)))
            if match := re.search(r"\[Footnote", line):
                errors.append(("Unconverted footnote", self.idx_range(line_num, match)))
            if match := re.search(r"Blank Page", line):
                errors.append(("Blank Page", self.idx_range(line_num, match)))
            for match in re.finditer(r"\[[o|a]e\]", line):
                errors.append(("Unconverted ligature", self.idx_range(line_num, match)))
            if match := re.search(r"<hr style", line):
                errors.append(("HR using 'style'", self.idx_range(line_num, match)))
            for match in re.finditer(r"&amp;amp", line):
                errors.append(
                    ("Badly converted ampersand", self.idx_range(line_num, match))
                )
            for match in re.finditer(r"(?<=<p>)\.[a-z]{2}(?!\S)", line):
                errors.append(
                    ("Possible ppg/ppgen command", self.idx_range(line_num, match))
                )
            for match in re.finditer(r"`", line):
                errors.append(("Tick-mark", self.idx_range(line_num, match)))
            for match in re.finditer(r"(?<!= *)(''|‘‘|’’)", line):
                errors.append(("Double single quotes", self.idx_range(line_num, match)))
            for match in re.finditer(r"‘\s", line):
                errors.append(
                    (
                        "Left single quote followed by whitespace",
                        self.idx_range(line_num, match),
                    )
                )
            for match in re.finditer(r"“\s", line):
                errors.append(
                    (
                        "Left double quote followed by whitespace",
                        self.idx_range(line_num, match),
                    )
                )
            if match := re.search(r"(?<=(^|<p>))”", line):
                errors.append(
                    (
                        "Right double quote at start of line",
                        self.idx_range(line_num, match),
                    )
                )
            if match := re.search(r"“(?=($|</p>))", line):
                errors.append(
                    (
                        "Left double quote at end of line",
                        self.idx_range(line_num, match),
                    )
                )
        self.output_subsection_errors(
            len(errors) == 0,
            "Special checks",
            errors,
        )

    def misc_styles(self) -> None:
        """List styles used in body of text."""

        class StylesHTMLParser(HTMLParser):
            """Parse HTML file to find `style="..."`."""

            def __init__(self) -> None:
                """Initialize HTML outline parser."""
                super().__init__()
                self.styles: dict[str, int] = {}  # Count of style use

            def handle_starttag(
                self, _tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                """Handle start tags to find styles used."""
                for attr in attrs:
                    if attr[0] == "style" and attr[1] is not None:
                        try:
                            self.styles[attr[1]] += 1
                        except KeyError:
                            self.styles[attr[1]] = 1
                        break

        parser = StylesHTMLParser()
        parser.feed(self.file_text)
        styles: list[str] = []
        for style, count in parser.styles.items():
            styles.append(f"{style} ({count})")
        self.output_subsection_errors(
            None,
            "Styles used",
            styles,
        )

    # Utility routines

    def output_subsection_errors(
        self,
        test_passed: Optional[bool],
        title: str,
        errors: list[str] | list[tuple[str, Optional[IndexRange]]],
        fail_string: str = "*FAIL*",
    ) -> None:
        """Output collected errors underneath subsection title.

        Args:
            test_passed: Whether the test passed, i.e. no errors. None for info only
            title: Title for this check.
            errors: List of errors to be output.
            fail_string: Defaults to "*FAIL*" but can be overridden to "*WARN*"
        """
        if test_passed is None:
            pass_string = "[info]"
        else:
            pass_string = "[pass]" if test_passed else fail_string
        self.add_subsection(f"{pass_string} {title}")
        for error in errors:
            if isinstance(error, str):
                self.dialog.add_entry(error)
            else:
                self.dialog.add_entry(error[0], error[1])

    def add_section(self, text: str) -> None:
        """Add section heading to dialog."""
        self.dialog.add_header("", f"===== {text} =====")

    def add_subsection(self, text: str) -> None:
        """Add subsection heading to dialog."""
        self.dialog.add_header(f"--- {text} ---")

    def idx_range(self, line_num: int, match: re.Match) -> IndexRange:
        """Return IndexRange for match in text.

        Args:
            line_num: zero-based line number.
            match: Match object returned by `re.search` or `re.finditer`.

        Returns:
            IndexRange from start to end of match in file text.
        """
        return IndexRange(
            IndexRowCol(line_num + 1, match.start()),
            IndexRowCol(line_num + 1, match.end()),
        )


def pphtml() -> None:
    """Instantiate & run PPhtml checker."""
    PPhtmlChecker().run()
