"""PPhtml tool."""

from html.parser import HTMLParser
import os.path
from typing import Any

from PIL import Image
import regex as re

from guiguts.checkers import CheckerDialog
from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.utilities import IndexRange, IndexRowCol


class OutlineHTMLParser(HTMLParser):
    """Parse HTML file to get document outline of h1-h6 elements"""

    h1_6_tags = ("h1", "h2", "h3", "h4", "h5", "h6")

    def __init__(self) -> None:
        """Initialize HTML outline parser."""
        super().__init__()
        self.outline: list[tuple[str, IndexRange]] = []
        self.tag = ""
        self.showh = False
        self.tag_start = IndexRowCol(0, 0)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
                indent = "  " * int(match.group(1))
                tag_index = self.getpos()
                self.outline.append(
                    (
                        "  " + indent + self.tag,
                        IndexRange(
                            self.tag_start, IndexRowCol(tag_index[0], tag_index[1] + 5)
                        ),
                    )
                )


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


class PPhtmlChecker:
    """PPhtml checker"""

    def __init__(self) -> None:
        """Initialize PPhtml checker"""
        self.dialog = PPhtmlCheckerDialog.show_dialog(rerun_command=self.run)
        self.images_dir = ""
        self.image_files: list[str] = []  # list of files in images folder
        self.filedata: list[str] = []  # string of image file information

    def run(self) -> None:
        """Run PPhtml"""

        self.dialog.reset()
        self.image_tests()
        self.heading_outline()

        self.dialog.display_entries()

    def image_tests(self) -> None:
        """Various checks relating to image files."""

        # find filenames of all the images
        self.images_dir = os.path.join(os.path.dirname(the_file().filename), "images")
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
        # self.allImagesUsed()
        # self.allTargetsAvailable()
        # self.allImages200k()
        # self.coverImage()
        # self.otherImage()
        # if self.verbose:
        #     self.imageSummary()

    def scan_images(self) -> None:
        """Scan each image, getting size, checking filename, etc."""
        errors = []
        test_passed = True
        # Check filenames
        for filename in self.image_files:
            if " " in filename:
                errors.append(f"  filename '{filename}' contains spaces")
                test_passed = False
            if re.search(r"\p{Lu}", filename):
                errors.append(f"  filename '{filename}' not all lower case")
                test_passed = False

        # Make sure all are JPEG or PNG images
        for filename in self.image_files:
            try:
                with Image.open(os.path.join(self.images_dir, filename)) as im:
                    self.filedata.append(
                        f"{filename}|{im.format}|{im.size[0]}x{im.size[1]}|{im.mode}"
                    )
            except IOError:
                errors.append(f"  file '{filename}' is not an image")
                test_passed = False
                continue
            if im.format not in ("JPEG", "PNG"):
                errors.append(f"  file '{filename}' is of type {im.format }")
                test_passed = False

        pass_string = "[pass]" if test_passed else "*FAIL*"
        self.add_subsection(f"{pass_string} Image folder consistency tests")
        for line in errors:
            self.dialog.add_entry(line)

    def heading_outline(self) -> None:
        """Output Document Heading Outline."""
        # Document Heading Outline
        parser = OutlineHTMLParser()
        parser.feed(maintext().get_text())
        self.add_section("Document Heading Outline")
        for line, pos in parser.outline:
            self.dialog.add_entry(line, pos)

    def add_section(self, text: str) -> None:
        """Add section heading to dialog."""
        self.dialog.add_header("", f"----- {text} -----")

    def add_subsection(self, text: str) -> None:
        """Add subsection heading to dialog."""
        self.dialog.add_header(f"--- {text} ---")


def pphtml() -> None:
    """Instantiate & run PPhtml checker."""
    PPhtmlChecker().run()
