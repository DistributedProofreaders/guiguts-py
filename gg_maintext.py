# GGmaintext inherits from tk.Text, but actually creates a Frame
# containing the Text widget and two scrollbars. The layout and
# linking of the scrollbars to the Text widget is done here

import tkinter as tk
from tkinter import ttk

from gg_menu import GGmenu
from gg_tkutils import isMac


class GGmaintext(tk.Text):
    def __init__(self, parent, **kwargs):
        # Create surrounding Frame
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Create Text itself & place in Frame
        # ASK SOMEONE- why doesn't `super()` work in place of `tk.Text` below?
        tk.Text.__init__(self, self.frame, **kwargs)
        tk.Text.grid(self, column=0, row=0, sticky="NSEW")

        # Create scrollbars, place in Frame, and link to Text
        hscroll = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL, command=self.xview)
        hscroll.grid(column=0, row=1, sticky="EW")
        self["xscrollcommand"] = hscroll.set
        vscroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.yview)
        vscroll.grid(column=1, row=0, sticky="NS")
        self["yscrollcommand"] = vscroll.set

        # Set up response to text being modified
        self.modifiedCallbacks = []
        self.bind("<<Modified>>", self.modFlagChanged)

        self.initContextMenu()

    # Override grid, so placing GGmaintext widget actually places surrounding Frame
    def grid(self, *args, **kwargs):
        return self.frame.grid(*args, **kwargs)

    #
    # Handle modified flag
    #
    # This method is bound to <<Modified>> event which happens whenever the widget's
    # modified flag is changed - not just when changed to True
    # Causes all registered functions to be called
    def modFlagChanged(self, *args):
        for func in self.modifiedCallbacks:
            func()

    #
    # Manually set widget's modified flag (may trigger call to modFlagChanged)
    def setModified(self, mod):
        self.edit_modified(mod)

    #
    # Return if widget's text has been modified
    def isModified(self):
        return self.edit_modified()

    #
    # Add application function to be called when widget's modified flag changes
    def addModifiedCallback(self, func):
        self.modifiedCallbacks.append(func)

    #
    # Save text in widget to file
    def doSave(self, fname):
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(self.get(1.0, tk.END))
            self.setModified(False)

    #
    # Open file and load text into widget
    def doOpen(self, fname):
        with open(fname, "r", encoding="utf-8") as fh:
            self.delete("1.0", tk.END)
            self.insert(tk.END, fh.read())
            self.setModified(False)

    #
    # Create a context menu for the main text widget
    def initContextMenu(self):
        menu_context = GGmenu(self, "")
        menu_context.addCutCopyPaste()

        def postContextMenu(event):
            menu_context.post(event.x_root, event.y_root)

        if isMac():
            self.bind("<2>", postContextMenu)
            self.bind("<Control-1>", postContextMenu)
        else:
            self.bind("<3>", postContextMenu)

    #
    # Get the name of the image file the insert cursor is in
    def getImageFilename(self):
        sep_index = self.search("//-----File: ", self.index(tk.INSERT), backwards=True)
        return (
            self.get(sep_index + "+13c", sep_index + "lineend").rstrip("-")
            if sep_index
            else ""
        )
