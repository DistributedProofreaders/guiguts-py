import os
import sys

project = "Guiguts 2.0"

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
    "private-members": True,
}

coverage_show_missing_items = True
coverage_statistics_to_stdout = False
