# typical python convention is to put built-in libraries first (which all of
# these are) followed by 3rd party libraries all alpha sorted by module
from os.path import basename, dirname
import re
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import webbrowser


class MenuBar:
    def __init__(self, root, textwgt):
        # we pass in the root and textwgt into the constructor since some
        # of the menu functions need them, but we create a object-local copy
        # (self.root). Note that python passes *everything* by reference, so
        # anything we do to self.root here will be done to the root variable
        # passed into this constructor.
        self.root = root
        self.textwgt = textwgt
        self.menubar = Menu(self.root)

        self.windowsystem = self.root.tk.call(
            "tk", "windowingsystem"
        )  # returns x11, win32 or aqua
        global isMac
        isMac = self.windowsystem == "aqua"
        # init all of the menus. I'm unclear if we need to store the menu
        # objects at all, but it seems like a good idea in case we need to
        # access them later. we could have just defined these within the
        # methods instead of passing them back, but it felt clearer to me
        # to pass them back and manage the class objects here in the constructor
        # I toyed with passing in self.menubar into the functions rather than
        # using the class object within them -- I think both make sense to me
        self.file_menu = self.initFileMenu()
        self.edit_menu = self.initEditMenu()
        self.help_menu = self.initHelpMenu()
        self.os_menu = self.initOSMenu()
        self.context_menu = self.initContextMenu()

    def keyBind(self, keyevent, bindevent):
        lk = re.sub("[A-Z]>$", lambda m: m.group(0).lower(), keyevent)
        uk = re.sub("[A-Z]>$", lambda m: m.group(0).upper(), keyevent)
        self.textwgt.bind(lk, lambda *args: self.textwgt.event_generate(bindevent))
        self.textwgt.bind(uk, lambda *args: self.textwgt.event_generate(bindevent))

    # Returns (accelerator, event)
    # technically this does not need to be a class function since it doesn't
    # use anything in the class -- it could just be a global function
    def acceventMeta(self, key):
        global isMac
        if isMac:
            return (f"Command+{key}", f"<Meta-{key}>")
        else:
            return (f"Ctrl+{key}", f"<Control-{key}>")

    # Returns (accelerator, event)
    def acceventShiftMeta(self, key):
        (accel, event) = self.acceventMeta(key)
        accel = "Shift+" + accel
        event = event[0] + "Shift-" + event[1:]
        return (accel, event)

    # if we wanted to make the add_command()s a bit simpler, we could create
    # helper functions in the class and use them, eg:
    def getRootEvent(self, event):
        return lambda: self.root.focus_get().event_generate(event)
        # used like add_command.(..., command=self.getRootEvent("<<Cut>>"))

    def getTextwgtEvent(self, event):
        return lambda: self.textwgt.event_generate(event)
        # used like add_command.(..., command=self.getTextwgtEvent("<<OpenFiles>>"))

    # Cut/Copy/Paste segment of menu
    def addCutCopyPaste(self, menu):
        (accel, event) = self.acceventMeta("X")
        menu.add_command(
            label="Cut",
            accelerator=accel,
            command=lambda: self.root.focus_get().event_generate("<<Cut>>"),
            underline=0,
        )
        (accel, event) = self.acceventMeta("C")
        menu.add_command(
            label="Copy",
            accelerator=accel,
            command=lambda: self.root.focus_get().event_generate("<<Copy>>"),
            underline=3,
        )
        (accel, event) = self.acceventMeta("V")
        menu.add_command(
            label="Paste",
            accelerator=accel,
            command=lambda: self.root.focus_get().event_generate("<<Paste>>"),
            underline=0,
        )

    def initFileMenu(self):
        menu_file = Menu(self.menubar)
        self.menubar.add_cascade(menu=menu_file, label="File", underline=0)
        (accel, event) = self.acceventMeta("O")
        menu_file.add_command(
            label="Open...",
            accelerator=accel,
            command=lambda: self.textwgt.event_generate("<<openFile>>"),
            underline=0,
        )
        self.keyBind(event, "<<openFile>>")
        (accel, event) = self.acceventMeta("S")
        menu_file.add_command(
            label="Save",
            accelerator=accel,
            command=lambda: self.textwgt.event_generate("<<saveFile>>"),
            underline=0,
        )
        self.keyBind(event, "<<saveFile>>")
        (accel, event) = self.acceventShiftMeta("S")
        menu_file.add_command(
            label="Save As...",
            accelerator=accel,
            command=lambda: self.textwgt.event_generate("<<saveasFile>>"),
            underline=5,
        )
        self.keyBind(event, "<<saveasFile>>")
        menu_file.add_separator()
        global isMac
        (accel, event) = self.acceventMeta("Q") if isMac else ("", "")
        menu_file.add_command(
            label="Quit",
            accelerator=accel,
            command=lambda: self.root.event_generate("<<quitProgram>>"),
            underline=0,
        )
        return menu_file

    def initEditMenu(self):
        menu_edit = Menu(self.menubar)
        self.menubar.add_cascade(menu=menu_edit, label="Edit", underline=0)
        (accel, event) = self.acceventMeta("Z")
        menu_edit.add_command(
            label="Undo",
            accelerator=accel,
            command=lambda: self.root.focus_get().event_generate("<<Undo>>"),
            underline=0,
        )
        global isMac
        (accel, event) = (
            self.acceventShiftMeta("Z") if isMac else self.acceventMeta("Y")
        )
        menu_edit.add_command(
            label="Redo",
            accelerator=accel,
            command=lambda: self.root.focus_get().event_generate("<<Redo>>"),
            underline=0,
        )
        menu_edit.add_separator()
        self.addCutCopyPaste(menu_edit)
        menu_edit.add_separator()
        (accel, event) = self.acceventMeta("A")
        menu_edit.add_command(
            label="Select All",
            accelerator=accel,
            command=lambda: self.root.focus_get().event_generate("<<SelectAll>>"),
            underline=0,
        )
        return menu_edit

    def initHelpMenu(self):
        menu_help = Menu(self.menubar)
        self.menubar.add_cascade(label="Help", menu=menu_help)
        menu_help.add_command(
            label="Guiguts manual",
            command=lambda: self.root.event_generate("<<helpManual>>"),
        )
        menu_help.add_command(
            label="About Guiguts",
            command=lambda: self.root.event_generate("<<helpAbout>>"),
        )
        return menu_help

    def initOSMenu(self):
        # Apple menu
        global isMac
        if isMac:
            menu_app = Menu(self.menubar, name="apple")
            self.menubar.add_cascade(menu=menu_app)
            menu_app.add_command(
                label="About Guiguts",
                command=lambda: self.root.event_generate("<<helpAbout>>"),
            )
            menu_app.add_separator()
            menu_window = Menu(self.menubar, name="window")
            self.menubar.add_cascade(menu=menu_window, label="Window")
        else:
            menu_app = None
        return menu_app

    def initContextMenu(self):
        menu_context = Menu(self.textwgt)
        self.addCutCopyPaste(menu_context)

        # unlike perl, in python we can define functions inside functions and
        # their scope is limited to the function they are defined, but they
        # can make use of any variables where they are defined as well
        def postContextMenu(event):
            menu_context.post(event.x_self.root, event.y_self.root)

        global isMac
        if isMac:
            self.textwgt.bind("<2>", postContextMenu)
            self.textwgt.bind("<Control-1>", postContextMenu)
        else:
            self.textwgt.bind("<3>", postContextMenu)

        return menu_context


# in python, because every python file can be a module (library) we don't
# want to run anything in the global context, but if this is the entrypoint
# we want to treat it as a program, not a module. We use this pythonism
# to achieve this:
if __name__ == "__main__":
    guiguts = Guiguts()
    guiguts.run()
