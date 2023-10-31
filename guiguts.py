# Main Guiguts class, derived from Tk - serves as root window


import os.path
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser

from gg_mainimage import GGmainimage
from gg_maintext import GGmaintext
from gg_menubar import GGmenubar
from gg_prefs import GGprefs
from gg_prefsdialog import GGprefsdialog
from gg_tkutils import isMac, ggRoot, ggMainText, ggMainImage


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
        maintext = GGmaintext(
            frame,
            undo=True,
            wrap="none",
            autoseparators=True,
            maxundo=-1,
        )
        ggMainText(maintext)

        # Main image widget
        mainimage = GGmainimage(frame)
        ggMainImage(mainimage)

        # Menus
        self["menu"] = GGmenubar(self)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        ggMainText().grid(column=0, row=0, sticky="NSEW")

        frame.columnconfigure(1, weight=0)
        if GGprefs().get("ImageWindow") == "Docked":
            self.dockImage()
        else:
            self.floatImage()

        if isMac():
            self.createcommand("tk::mac::ShowPreferences", self.showMyPreferencesDialog)
            self.createcommand("tk::mac::OpenDocument", self.openDocument)
            self.createcommand("tk::mac::Quit", self.quitProgram)

        self.filename = ""
        self.updateTitle()

        ggMainText().focus_set()
        ggMainText().addModifiedCallback(self.updateTitle)

    def run(self):
        self.mainloop()

    #
    # Update title field with filename
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
            self.updateTitle()

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
            self.updateTitle()

    def quitProgram(self, *args):
        self.quit()

    def helpAbout(self, *args):
        messagebox.showinfo(
            title="About Guiguts", message="Here's some information about Guiguts"
        )

    def showMyPreferencesDialog(self, *args):
        GGprefsdialog(self, "Set Preferences")

    # Handle drag/drop on Macs
    def openDocument(self, args):
        filename = args[0]  # Take first of list of filenames
        ggMainText().doOpen(filename)
        self.updateTitle()

    def helpManual(self, *args):
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_Manual")

    # Handle image window
    def floatImage(self, *args):
        self.wm_manage(ggMainImage())
        ggMainImage().lift()
        tk.Wm.protocol(ggMainImage(), "WM_DELETE_WINDOW", self.dockImage)
        GGprefs().set("ImageWindow", "Floated")

    def dockImage(self, *args):
        self.wm_forget(ggMainImage())
        ggMainImage().grid(column=1, row=0, sticky="NSEW")
        GGprefs().set("ImageWindow", "Docked")

    def loadImage(self, *args):
        filename = ggMainText().getImageFilename()
        ggMainImage().loadImage(filename)
        ggMainImage().lift()

    # Handle spawning a process
    def spawnProcess(self, *args):
        result = subprocess.run(
            "python child.py",
            input="Convert me to uppercase",
            text=True,
            capture_output=True,
        )
        messagebox.showinfo(title="Spawn stdout", message=result.stdout)
        messagebox.showinfo(title="Spawn stderr", message=result.stderr)

    #
    # Set default preference values - will be overridden by any values set in the GGprefs file
    def setPrefsDefaults(self):
        GGprefs().setDefault("ImageWindow", "Docked")


if __name__ == "__main__":
    guiguts = Guiguts()
    guiguts.run()
