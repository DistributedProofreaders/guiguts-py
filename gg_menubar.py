# GGmenubar class is tk.Menu, used for main menubar
# Creates its child menus

import re
import tkinter as tk

from gg_menu import GGmenu
from gg_tkutils import isMac


class GGmenubar(tk.Menu):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
