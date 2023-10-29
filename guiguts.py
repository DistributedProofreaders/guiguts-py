# Main Guiguts class, derived from Tk - serves as root window


from os.path import basename, dirname
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser

from gg_maintext import GGmaintext
from gg_menubar import GGmenubar
from gg_tkutils import isMac, ggRoot, ggMainText


class Guiguts(tk.Tk):
    def __init__(self):
        super().__init__()

        ggRoot(self)
        self.geometry("800x400")
        self.option_add("*tearOff", False)

        # Main text widget
        maintext = GGmaintext(
            self,
            undo=True,
            wrap="none",
            autoseparators=True,
            maxundo=-1,
        )
        ggMainText(maintext)

        # Menus
        self["menu"] = GGmenubar(self)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        maintext.grid(column=0, row=0, sticky="NSEW")
        # maintext.initContextMenu()

        if isMac():
            self.createcommand("tk::mac::ShowPreferences", self.showMyPreferencesDialog)
            self.createcommand("tk::mac::OpenDocument", self.openDocument)
            self.createcommand("tk::mac::Quit", self.quitProgram)

        self.filename = ""
        self.updateTitle()
        maintext.focus_set()

        maintext.addModifiedCallback(self.updateTitle)

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
            initialfile=basename(self.filename),
            initialdir=dirname(self.filename),
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
        messagebox.showwarning(
            title="Preferences", message="Prefs dialog hasn't been written yet"
        )

    # Handle drag/drop on Macs
    def openDocument(self, args):
        filename = args[0]  # Take first of list of filenames
        ggMainText().doOpen(filename)
        self.updateTitle()

    def helpManual(self, *args):
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_Manual")


if __name__ == "__main__":
    guiguts = Guiguts()
    guiguts.run()
