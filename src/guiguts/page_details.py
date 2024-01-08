"""Store and manipulate page labels."""

import roman  # type: ignore[import-untyped]

STYLE_ARABIC = "Arabic"
STYLE_ROMAN = "Roman"
STYLE_DITTO = '"'
NUMBER_INCREMENT = "+1"
NUMBER_NONE = "None"
PAGE_LABEL_PREFIX = "Pg "


class PageDetail(dict):
    """Page detail information for one page.

    Attributes:
        index: Index of start of page in file.
        style: Page number style: "Arabic" or "Roman"
        number:
    """

    def __init__(
        self, index: str, style: str = '"', number: str = NUMBER_INCREMENT
    ) -> None:
        """Initialize a PageDetail object to hold page information."""
        self["index"] = index
        self["style"] = style
        self["number"] = number
        self["label"] = ""


class PageDetails(dict):
    """Dictionary of Page Detail objects: key is png name."""

    def __init__(self) -> None:
        """Initialize dictionary."""
        super().__init__()

    def recalculate(self) -> None:
        """Recalculate labels from details."""
        number = 0
        style = STYLE_ARABIC
        for png, detail in sorted(self.items()):
            if detail["number"] == NUMBER_NONE:
                detail["label"] = ""
            else:
                if detail["number"] == NUMBER_INCREMENT:
                    number += 1
                else:
                    number = int(detail["number"])
                if detail["style"] != STYLE_DITTO:
                    style = detail["style"]
                if style == STYLE_ROMAN:
                    label = roman.toRoman(number).lower()
                else:
                    label = str(number)
                detail["label"] = PAGE_LABEL_PREFIX + label

    def png_from_label(self, label: str) -> str:
        """Find the png corresponding to the page with the given label.

        Args:
            label: The label to match against.

        Returns:
            The png number corresponding to the given label, or empty string.
        """
        for png, detail in self.items():
            if detail["label"] == label:
                return png
        return ""
