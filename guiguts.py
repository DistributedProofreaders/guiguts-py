# typical python convention is to put built-in libraries first (which all of
# these are) followed by 3rd party libraries all alpha sorted by module
from os.path import basename, dirname
import re
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import webbrowser

from menubar import MenuBar


class Guiguts:
    def __init__(self):
        self.filename = ""

        # Create main window
        self.root = Tk()
        self.windowsystem = self.root.tk.call(
            "tk", "windowingsystem"
        )  # returns x11, win32 or aqua
        global isMac
        isMac = self.windowsystem == "aqua"
        self.root.option_add("*tearOff", FALSE)  # old & outdated! Not on aqua anyway?
        self.root.geometry("800x400")

        self.mainframe = ttk.Frame(self.root, padding="5 5 5 5")
        self.mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.rowconfigure(0, weight=1)

        self.textwgt = self.initTextWidget()

        # Menus
        self.menus = MenuBar(self.root, self.textwgt)
        # because self.menus is now a MenuBar object, we can access its
        # variables directly to to pull out the menubar:
        self.root["menu"] = self.menus.menubar

        ### Bind menu entry events to functions
        self.root.bind("<<openFile>>", self.openFile)
        self.root.bind("<<saveFile>>", self.saveFile)
        self.root.bind("<<saveasFile>>", self.saveasFile)
        self.root.bind("<<quitProgram>>", self.quitProgram)
        self.root.bind("<<helpManual>>", self.helpManual)
        self.root.bind("<<helpAbout>>", self.helpAbout)

        self.textwgt.bind("<<Modified>>", self.modFlagChanged)

        if isMac:
            self.root.createcommand(
                "tk::mac::ShowPreferences", self.showMyPreferencesDialog
            )
            self.root.createcommand("tk::mac::OpenDocument", self.openDocument)
            self.root.createcommand("tk::mac::Quit", self.quitProgram)

        self.updateTitle()
        self.textwgt.focus_set()

    def run(self):
        self.root.mainloop()

    def initTextWidget(self):
        # Text widget
        textwgt = Text(
            self.mainframe,
            width=40,
            height=10,
            undo=True,
            autoseparators=True,
            maxundo=-1,
        )
        textwgt.grid(column=0, row=0, sticky=(N, W, E, S))
        s = ttk.Scrollbar(self.root, orient=VERTICAL, command=textwgt.yview)
        s.grid(column=1, row=0, sticky=(N, S))
        textwgt["yscrollcommand"] = s.set
        return textwgt

    # This function is bound to <<Modified>> event which happens when the widget's modified flag is changed
    def modFlagChanged(self, *args):
        self.setModified(
            self.isModified()
        )  # to trigger side effects, like "edited" text in title bar

    def setModified(self, mod):
        self.textwgt.edit_modified(mod)
        self.updateTitle()

    def isModified(self):
        return self.textwgt.edit_modified()

    def updateTitle(self):
        modtitle = " - edited" if self.isModified() else ""
        filetitle = " - " + self.filename if self.filename else ""
        self.root.title(
            "Guiguts 2.0 (" + self.windowsystem + ")" + modtitle + filetitle
        )

    def doSave(self, fname):
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(self.textwgt.get(1.0, END))
            self.setModified(False)

    def doOpen(self, fname):
        with open(fname, "r", encoding="utf-8") as fh:
            self.textwgt.delete("1.0", END)
            self.textwgt.insert(END, fh.read())
            self.setModified(False)

    def openFile(self, *args):
        fn = filedialog.askopenfilename(
            filetypes=(("Text files", "*.txt *.html *.htm"), ("All files", "*.*"))
        )
        if fn:
            self.filename = fn
            self.doOpen(self.filename)
            self.updateTitle()

    def saveFile(self, *args):
        if self.filename:
            self.doSave(self.filename)
        else:
            self.saveasFile()

    def saveasFile(self, *args):
        fn = filedialog.asksaveasfilename(
            initialfile=basename(self.filename),
            initialdir=dirname(self.filename),
            filetypes=[("All files", "*")],
        )
        if fn:
            self.filename = fn
            self.doSave(self.filename)
            self.updateTitle()

    def quitProgram(self, *args):
        self.root.quit()

    def helpAbout(self, *args):
        messagebox.showinfo(
            title="About Guiguts", message="Here's some information about Guiguts"
        )

    def showMyPreferencesDialog(self, *args):
        messagebox.showwarning(
            title="Preferences", message="Prefs dialog hasn't been written yet"
        )

    def openDocument(self, args):
        filename = args[0]  # Take first of list of filenames
        self.doOpen(filename)
        self.updateTitle()

    def helpManual(self, *args):
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_Manual")


# in python, because every python file can be a module (library) we don't
# want to run anything in the global context, but if this is the entrypoint
# we want to treat it as a program, not a module. We use this pythonism
# to achieve this:
if __name__ == "__main__":
    guiguts = Guiguts()
    guiguts.run()
