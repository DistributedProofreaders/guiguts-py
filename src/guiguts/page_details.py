"""Store and manipulate page labels."""

STYLE_ARABIC = "Arabic"
STYLE_ROMAN = "Roman"
STYLE_DITTO = '"'


class PageDetail(dict):
    """Page detail information for one page.

    Attributes:
        index: Index of start of page in file.
        style: Page number style: "Arabic" or "Roman"
        number:
    """

    def __init__(self, index: str, style: str = '"', number: str = "+1") -> None:
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
