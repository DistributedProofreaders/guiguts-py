# GGmenubar class is tk.Menu, used for main menubar
# Creates its child menus

import tkinter as tk


class GGmenubar(tk.Menu):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
