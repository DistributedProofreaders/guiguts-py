import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
]

autodoc_member_order = "bysource"
autoclass_content = "both"

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "private-members": True,
}
