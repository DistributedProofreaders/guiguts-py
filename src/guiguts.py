# Main Guiguts class, derived from Tk - serves as root window


import datetime
import os.path
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser

from mainwindow import MainImage, MainText, Menu, MenuBar, StatusBar
from preferences import Preferences
from gg_prefsdialog import PreferencesDialog

from tk_utilities import isMac, ggRoot, ggMainText, ggMainImage, ggStatusBar


class Guiguts(tk.Tk):
    def __init__(self):
        super().__init__()

        ggRoot(self)
        self.geometry("800x400")
        self.option_add("*tearOff", False)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.setPrefsDefaults()

        frame = ttk.Frame(self, padding="5 5 5 5")
        frame.grid(column=0, row=0, sticky="NSEW")
        # Main text widget
        maintext = MainText(
            frame,
            undo=True,
            wrap="none",
            autoseparators=True,
            maxundo=-1,
        )
        ggMainText(maintext)

        menubar = MenuBar(self)
        self.initMenus(menubar)
        self["menu"] = menubar

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        ggMainText().grid(column=0, row=0, sticky="NSEW")

        # Main image widget
        mainimage = MainImage(frame)
        ggMainImage(mainimage)
        frame.columnconfigure(1, weight=0)
        if Preferences().get("ImageWindow") == "Docked":
            self.dockImage()
        else:
            self.floatImage()

        # Status bar
        statusbar = StatusBar(frame)
        ggStatusBar(statusbar)
        self.initStatusBar(statusbar)
        statusbar.grid(column=0, row=1, columnspan=2, sticky="NSEW")

        if isMac():
            self.createcommand("tk::mac::ShowPreferences", self.showMyPreferencesDialog)
            self.createcommand("tk::mac::OpenDocument", self.openDocument)
            self.createcommand("tk::mac::Quit", self.quitProgram)

        self.filename = ""
        self.updateFilenameLabels()

        ggMainText().focus_set()
        ggMainText().addModifiedCallback(self.updateTitle)

    def run(self):
        self.mainloop()

    #
    # Update title field & statusbar with filename
    def updateTitle(self):
        modtitle = " - edited" if ggMainText().isModified() else ""
        filetitle = " - " + self.filename if self.filename else ""
        self.title("Guiguts 2.0" + modtitle + filetitle)

    #
    # Open and load a text file
    def openFile(self, *args):
        fn = filedialog.askopenfilename(
            filetypes=(("Text files", "*.txt *.html *.htm"), ("All files", "*.*"))
        )
        if fn:
            self.filename = fn
            ggMainText().doOpen(self.filename)
            self.updateFilenameLabels()

    #
    # Save the current file
    def saveFile(self, *args):
        if self.filename:
            ggMainText().doSave(self.filename)
        else:
            self.saveasFile()

    #
    # Save current text as new file
    def saveasFile(self, *args):
        fn = filedialog.asksaveasfilename(
            initialfile=os.path.basename(self.filename),
            initialdir=os.path.dirname(self.filename),
            filetypes=[("All files", "*")],
        )
        if fn:
            self.filename = fn
            ggMainText().doSave(self.filename)
            self.updateFilenameLabels()

    def quitProgram(self, *args):
        self.quit()

    def helpAbout(self, *args):
        messagebox.showinfo(
            title="About Guiguts", message="Here's some information about Guiguts"
        )

    def showMyPreferencesDialog(self, *args):
        PreferencesDialog(self, "Set Preferences")

    # Handle drag/drop on Macs
    def openDocument(self, args):
        filename = args[0]  # Take first of list of filenames
        ggMainText().doOpen(filename)
        self.updateFilenameLabels()

    def helpManual(self, *args):
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_Manual")

    # Handle image window
    def floatImage(self, *args):
        ggMainImage().grid_remove()
        if ggMainImage().isImageLoaded():
            self.wm_manage(ggMainImage())
            ggMainImage().lift()
            tk.Wm.protocol(ggMainImage(), "WM_DELETE_WINDOW", self.dockImage)
        else:
            self.wm_forget(ggMainImage())
        Preferences().set("ImageWindow", "Floated")

    def dockImage(self, *args):
        self.wm_forget(ggMainImage())
        if ggMainImage().isImageLoaded():
            ggMainImage().grid(column=1, row=0, sticky="NSEW")
        else:
            ggMainImage().grid_remove()

        Preferences().set("ImageWindow", "Docked")

    def loadImage(self, *args):
        filename = ggMainText().getImageFilename()
        ggMainImage().loadImage(filename)
        if Preferences().get("ImageWindow") == "Docked":
            self.dockImage()
        else:
            self.floatImage()

    # Handle spawning a process
    def spawnProcess(self, *args):
        try:
            result = subprocess.run(
                ["python", "child.py"],
                input="Convert me to uppercase",
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            result = subprocess.run(
                ["python3", "child.py"],
                input="Convert me to uppercase",
                text=True,
                capture_output=True,
            )
        messagebox.showinfo(title="Spawn stdout", message=result.stdout)
        messagebox.showinfo(title="Spawn stderr", message=result.stderr)

    def updateFilenameLabels(self):
        self.updateTitle()
        ggStatusBar().set("filename", os.path.basename(self.filename))

    #
    # Set default prefs - will be overridden by any values set in the Preferences file
    def setPrefsDefaults(self):
        Preferences().setDefault("ImageWindow", "Docked")

    def initMenus(self, menubar):
        self.initFileMenu(menubar)
        self.initEditMenu(menubar)
        self.initViewMenu(menubar)
        self.initHelpMenu(menubar)
        self.initOSMenu(menubar)

    def initFileMenu(self, parent):
        menu_file = Menu(parent, "~File")
        menu_file.addButton("~Open...", self.openFile, "Cmd/Ctrl+O")
        menu_file.addButton("~Save", self.saveFile, "Cmd/Ctrl+S")
        menu_file.addButton("Save ~As...", self.saveasFile, "Cmd/Ctrl+Shift+S")
        menu_file.add_separator()
        menu_file.addButton("Spawn ~Process", self.spawnProcess)
        menu_file.add_separator()
        menu_file.addButton("~Quit", self.quitProgram, "Cmd+Q" if isMac() else "")

    def initEditMenu(self, parent):
        menu_edit = Menu(parent, "~Edit")
        menu_edit.addButton("~Undo", "<<Undo>>", "Cmd/Ctrl+Z")
        menu_edit.addButton("~Redo", "<<Redo>>", "Cmd+Shift+Z" if isMac() else "Ctrl+Y")
        menu_edit.add_separator()
        menu_edit.addCutCopyPaste()
        menu_edit.add_separator()
        menu_edit.addButton("Select ~All", "<<SelectAll>>", "Cmd/Ctrl+A")
        menu_edit.add_separator()
        menu_edit.addButton("Pre~ferences...", self.showMyPreferencesDialog)

    def initViewMenu(self, parent):
        menu_view = Menu(parent, "~View")
        menu_view.addButton("~Dock", self.dockImage, "Cmd/Ctrl+D")
        menu_view.addButton("~Float", self.floatImage, "Cmd/Ctrl+F")
        menu_view.addButton("~Load Image", self.loadImage, "Cmd/Ctrl+L")

    def initHelpMenu(self, parent):
        menu_help = Menu(parent, "~Help")
        menu_help.addButton("Guiguts ~Manual", self.helpManual)
        menu_help.addButton("About ~Guiguts", self.helpAbout)

    def initOSMenu(self, parent):
        if isMac():
            # Apple menu
            menu_app = Menu(parent, "", name="apple")
            menu_app.addButton("About ~Guiguts", self.helpAbout)
            menu_app.add_separator()
            # Window menu
            Menu(parent, "Window", name="window")
        else:
            menu_app = None

    def initStatusBar(self, statusbar):
        statusbar.add(
            "rowcol",
            lambda: re.sub(r"(\d)\.(\d)", r"L:\1 C:\2", ggMainText().index(tk.INSERT)),
            width=10,
        )
        statusbar.add("filename", width=12)
        statusbar.add(
            "time", lambda: datetime.datetime.now().strftime("%H:%M:%S"), width=8
        )


if __name__ == "__main__":
    guiguts = Guiguts()
    guiguts.run()
