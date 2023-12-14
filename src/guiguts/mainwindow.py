"""Define key components of main window"""


import os.path
from PIL import Image, ImageTk
import re
import sys
import traceback
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror

from guiguts.preferences import preferences
from guiguts.utilities import is_mac, is_x11


TEXTIMAGE_WINDOW_ROW = 0
TEXTIMAGE_WINDOW_COL = 0
SEPARATOR_ROW = 1
SEPARATOR_COL = 0
STATUSBAR_ROW = 2
STATUSBAR_COL = 0
MIN_PANE_WIDTH = 20


class Root(tk.Tk):
    """Inherits from Tk root window"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.geometry("800x400")
        self.option_add("*tearOff", False)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def report_callback_exception(self, exc, val, tb):
        """Override tkinter exception reporting rather just
        writing it to stderr.

        TODO: send this to a full error logging window.
        """
        err = "\n".join(traceback.format_exception(exc, val, tb))
        print(str(err), file=sys.stderr)
        showerror("Caught Tkinter Exception", message=err)


class MainWindow:
    """Handles the construction of the main window with its basic widgets

    These class variables are set in ``__init__`` to store the single instance
    of these main window items. They are exposed externally via convenience
    functions with the same names, e.g. ``root()`` returns ``MainWindow.root``
    """

    root = None
    menubar = None
    maintext = None
    mainimage = None
    statusbar = None

    def __init__(self):
        MainWindow.root = Root()
        MainWindow.menubar = tk.Menu()
        root()["menu"] = menubar()

        MainWindow.statusbar = StatusBar(root())
        statusbar().grid(
            column=STATUSBAR_COL,
            row=STATUSBAR_ROW,
            sticky="NSEW",
        )

        ttk.Separator(root()).grid(
            column=SEPARATOR_COL,
            row=SEPARATOR_ROW,
            sticky="NSEW",
        )

        self.paned_window = tk.PanedWindow(
            root(), orient=tk.HORIZONTAL, sashwidth=4, sashrelief=tk.GROOVE
        )
        self.paned_window.grid(
            column=TEXTIMAGE_WINDOW_COL, row=TEXTIMAGE_WINDOW_ROW, sticky="NSEW"
        )

        MainWindow.maintext = MainText(
            self.paned_window,
            undo=True,
            wrap="none",
            autoseparators=True,
            maxundo=-1,
            highlightthickness=0,
        )
        self.paned_window.add(maintext().frame, minsize=MIN_PANE_WIDTH)

        MainWindow.mainimage = MainImage(self.paned_window)

    def float_image(self, *args):
        """Float the image into a separate window"""
        mainimage().grid_remove()
        if mainimage().is_image_loaded():
            root().wm_manage(mainimage())
            mainimage().lift()
            tk.Wm.protocol(mainimage(), "WM_DELETE_WINDOW", self.dock_image)
        else:
            root().wm_forget(mainimage())
        preferences["ImageWindow"] = "Floated"

    def dock_image(self, *args):
        """Dock the image back into the main window"""
        root().wm_forget(mainimage())
        if mainimage().is_image_loaded():
            self.paned_window.add(mainimage(), minsize=MIN_PANE_WIDTH)
        else:
            try:
                self.paned_window.forget(mainimage())
            except tk.TclError:
                pass  # OK - image wasn't being managed by paned_window
        preferences["ImageWindow"] = "Docked"


class Menu(tk.Menu):
    """Extend ``tk.Menu`` to make adding buttons with accelerators simpler."""

    def __init__(self, parent, label, **kwargs):
        """Initialize menu and add to parent

        Args:
            parent: Parent menu/menubar, or another widget if context menu.
            label: Label string for menu, including tilde for keyboard
              navigation, e.g. "~File".
            **kwargs: Optional additional keywords args for ``tk.Menu``.
        """

        super().__init__(parent, **kwargs)
        command_args = {"menu": self}
        if label:
            (label_tilde, label_txt) = _process_label(label)
            command_args["label"] = (label_txt,)
            if label_tilde >= 0:
                command_args["underline"] = label_tilde
        # Only needs cascade if a child of menu/menubar, not if a context popup menu
        if isinstance(parent, tk.Menu):
            parent.add_cascade(command_args)

    def add_button(self, label, handler, accel=""):
        """Add a button to the menu.

        Args:
            label: Label string for button, including tilde for keyboard
              navigation, e.g. "~Save".
            handler: Callback function or built-in virtual event,
              e.g. "<<Cut>>", in which case button will generate that event.
            accel: String describing optional accelerator key, used when a
              callback function is passed in as ``handler``. Will be displayed
              on the button, and will be bound to the same action as the menu
              button. "Cmd/Ctrl" means `Cmd` key on Mac; `Ctrl` key on
              Windows/Linux.
        """
        (label_tilde, label_txt) = _process_label(label)
        (accel, key_event) = _process_accel(accel)
        if isinstance(handler, str):
            # Handler is built-in virtual event, so no key binding needed,
            # but event needs to be generated by button click
            def command(*args):
                root().focus_get().event_generate(handler)

        else:
            # Handler is function, so may need key binding
            command = handler
            if accel:
                maintext().key_bind(key_event, command)

        command_args = {
            "label": label_txt,
            "command": command,
            "accelerator": accel,
        }
        if label_tilde >= 0:
            command_args["underline"] = label_tilde
        self.add_command(command_args)

    def add_cut_copy_paste(self):
        """Add cut/copy/paste buttons to this menu"""
        self.add_button("Cu~t", "<<Cut>>", "Cmd/Ctrl+X")
        self.add_button("~Copy", "<<Copy>>", "Cmd/Ctrl+C")
        self.add_button("~Paste", "<<Paste>>", "Cmd/Ctrl+V")


def _process_label(label):
    """Given a button label string, e.g. "~Save...", where the optional
    tilde indicates the underline location for keyboard activation,
    return the tilde location (-1 if none), and the string without the tilde.
    """
    return (label.find("~"), label.replace("~", ""))


def _process_accel(accel):
    """Convert accelerator string, e.g. "Ctrl+X" to appropriate keyevent
    string for platform, e.g. "Control-X".

    "Cmd/Ctrl" means use ``Cmd`` key on Mac; ``Ctrl`` key on Windows/Linux.
    """
    if is_mac():
        accel = accel.replace("/Ctrl", "")
    else:
        accel = accel.replace("Cmd/", "")
    keyevent = accel.replace("Ctrl+", "Control-")
    keyevent = keyevent.replace("Shift+", "Shift-")
    keyevent = keyevent.replace("Cmd+", "Meta-")
    return (accel, f"<{keyevent}>")


class MainText(tk.Text):
    """MainText is the main text window, and inherits from ``tk.Text``."""

    def __init__(self, parent, **kwargs):
        """Create a Frame, and put a Text and two Scrollbars in the Frame.
        Layout and linking of the Scrollbars to the Text widget is done here.

        Args:
            parent: Parent widget to contain MainText.
            **kwargs: Optional additional keywords args for ``tk.Text``.
        """

        # Create surrounding Frame
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Create Text itself & place in Frame
        super().__init__(self.frame, **kwargs)
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
        self.bind("<<Modified>>", self.modify_flag_changed_callback)

        self.init_context_menu()

    def grid(self, *args, **kwargs):
        """Override ``grid``, so placing MainText widget actually places surrounding Frame"""
        return self.frame.grid(*args, **kwargs)

    def key_bind(self, keyevent, handler):
        """Bind lower & uppercase versions of ``keyevent`` to ``handler``
        in main text window.

        If this is not done, then use of Caps Lock key causes confusing
        behavior, because pressing ``Ctrl`` and ``s`` sends ``Ctrl+S``.

        Args:
            keyevent: Key event to trigger call to ``handler``.
            handler: Callback function to be bound to ``keyevent``.
        """
        lk = re.sub("[A-Z]>$", lambda m: m.group(0).lower(), keyevent)
        uk = re.sub("[A-Z]>$", lambda m: m.group(0).upper(), keyevent)

        def handler_break(event, func):
            """In order for class binding not to be called after widget
            binding, event handler for widget needs to return "break"
            """
            func(event)
            return "break"

        self.bind(lk, lambda event: handler_break(event, handler))
        self.bind(uk, lambda event: handler_break(event, handler))

    #
    # Handle "modified" flag
    #
    def add_modified_callback(self, func):
        """Add callback function to a list of functions to be called when
        widget's modified flag changes.

        Args:
            func: Callback function to be added to list.
        """
        self.modifiedCallbacks.append(func)

    def modify_flag_changed_callback(self, *args):
        """This method is bound to <<Modified>> event which happens whenever
        the widget's modified flag is changed - not just when changed to True.

        Causes all functions registered via ``add_modified_callback`` to be called.
        """
        for func in self.modifiedCallbacks:
            func()

    def set_modified(self, mod):
        """Manually set widget's modified flag (may trigger call to
        ```modify_flag_changed_callback```).

        Args:
            mod: Boolean setting for widget's modified flag."""
        self.edit_modified(mod)

    def is_modified(self):
        """Return whether widget's text has been modified."""
        return self.edit_modified()

    def do_save(self, fname):
        """Save widget's text to file.

        Args:
            fname: Name of file to save text to.
        """
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(self.get(1.0, tk.END))
            self.set_modified(False)

    def do_open(self, fname):
        """Load text from file into widget.

        Args:
            fname: Name of file to load text from.
        """
        with open(fname, "r", encoding="utf-8") as fh:
            self.delete("1.0", tk.END)
            self.insert(tk.END, fh.read())
            self.set_modified(False)

    def init_context_menu(self):
        """Create a context menu for the main text widget"""

        menu_context = Menu(self, "")
        menu_context.add_cut_copy_paste()

        def post_context_menu(event):
            menu_context.post(event.x_root, event.y_root)

        if is_mac():
            self.bind("<2>", post_context_menu)
            self.bind("<Control-1>", post_context_menu)
        else:
            self.bind("<3>", post_context_menu)

    def get_insert_index(self):
        """Return index of the insert cursor."""
        return self.index(tk.INSERT)

    def set_insert_index(self, index, see=False):
        """Set the position of the insert cursor.

        Args:
            index: String containing index/mark to position cursor.
        """
        self.mark_set(tk.INSERT, index)
        if see:
            self.see(tk.INSERT)
            self.focus_set()


class MainImage(tk.Frame):
    """MainImage is a Frame, containing a Canvas which can display a png/jpeg file.

    Also contains scrollbars, and can be scrolled with mousewheel (vertically),
    Shift-mousewheel (horizontally) and zoomed with Control-mousewheel.

    MainImage can be docked or floating. Floating is not supported with ttk.Frame,
    hence inherits from tk.Frame.

    Adapted from https://stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan
    and https://stackoverflow.com/questions/56043767/show-large-image-using-scrollbar-in-python

    Attributes:
        hbar: Horizontal scrollbar.
        vbar: Vertical scrollbar.
        canvas: Canvas widget.
        image: Whole loaded image (or None)
        image_scale: Zoom scale at which image should be drawn.
        scale_delta: Ratio to multiply/divide scale when Control-scrolling mouse wheel.
    """

    def __init__(self, parent):
        """Initialize the MainImage to contain an empty Canvas with scrollbars"""
        tk.Frame.__init__(self, parent)

        self.hbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.hbar.grid(row=1, column=0, sticky="EW")
        self.hbar.configure(command=self.scroll_x)
        self.vbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.vbar.grid(row=0, column=1, sticky="NS")
        self.vbar.configure(command=self.scroll_y)

        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            xscrollcommand=self.hbar.set,
            yscrollcommand=self.vbar.set,
        )
        self.canvas.grid(row=0, column=0, sticky="NSEW")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", self.show_image)
        self.canvas.bind("<ButtonPress-1>", self.move_from)
        self.canvas.bind("<B1-Motion>", self.move_to)
        if is_x11():
            self.canvas.bind("<Control-Button-5>", self.wheel_zoom)
            self.canvas.bind("<Control-Button-4>", self.wheel_zoom)
            self.canvas.bind("<Button-5>", self.wheel_scroll)
            self.canvas.bind("<Button-4>", self.wheel_scroll)
        else:
            self.canvas.bind("<Control-MouseWheel>", self.wheel_zoom)
            self.canvas.bind("<MouseWheel>", self.wheel_scroll)

        self.image_scale = 1.0
        self.scale_delta = 1.3
        self.image = None
        self.imageid = None
        self.container = None

    def scroll_y(self, *args, **kwargs):
        """Scroll canvas vertically and redraw the image"""
        self.canvas.yview(*args, **kwargs)
        self.show_image()

    def scroll_x(self, *args, **kwargs):
        """Scroll canvas horizontally and redraw the image."""
        self.canvas.xview(*args, **kwargs)
        self.show_image()

    def move_from(self, event):
        """Remember previous coordinates for dragging with the mouse."""
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """Drag canvas to the new position."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()

    def wheel_zoom(self, event):
        """Zoom with mouse wheel."""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        bbox_scroll = self.canvas.bbox(self.container)  # get image area
        if not (
            bbox_scroll[0] < x < bbox_scroll[2] and bbox_scroll[1] < y < bbox_scroll[3]
        ):
            return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows/MacOS (event.delta) wheel event
        if event.num == 5 or event.delta < 0:
            min_dimension = min(self.width, self.height)
            if int(min_dimension * self.image_scale) < 30:
                return  # image too small
            self.image_scale /= self.scale_delta
            scale /= self.scale_delta
        if event.num == 4 or event.delta > 0:
            min_dimension = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            if min_dimension < self.image_scale:
                return  # image too large
            self.image_scale *= self.scale_delta
            scale *= self.scale_delta
        self.canvas.scale("all", x, y, scale, scale)  # rescale all canvas objects
        self.show_image()

    def show_image(self, event=None):
        """Show image on the Canvas"""
        # get image area & remove 1 pixel shift
        bbox_image = self.canvas.bbox(self.container)
        bbox_image = (
            bbox_image[0] + 1,
            bbox_image[1] + 1,
            bbox_image[2] - 1,
            bbox_image[3] - 1,
        )
        # get visible area of the canvas
        bbox_visible = (
            self.canvas.canvasx(0),
            self.canvas.canvasy(0),
            self.canvas.canvasx(self.canvas.winfo_width()),
            self.canvas.canvasy(self.canvas.winfo_height()),
        )
        # get scroll region box
        bbox_scroll = [
            min(bbox_image[0], bbox_visible[0]),
            min(bbox_image[1], bbox_visible[1]),
            max(bbox_image[2], bbox_visible[2]),
            max(bbox_image[3], bbox_visible[3]),
        ]
        # whole image width in the visible area
        if bbox_scroll[0] == bbox_visible[0] and bbox_scroll[2] == bbox_visible[2]:
            bbox_scroll[0] = bbox_image[0]
            bbox_scroll[2] = bbox_image[2]
        # whole image height in the visible area
        if bbox_scroll[1] == bbox_visible[1] and bbox_scroll[3] == bbox_visible[3]:
            bbox_scroll[1] = bbox_image[1]
            bbox_scroll[3] = bbox_image[3]
        self.canvas.configure(scrollregion=bbox_scroll)

        # get coordinates (x1,y1,x2,y2) of the image tile
        x1 = max(bbox_visible[0] - bbox_image[0], 0)
        y1 = max(bbox_visible[1] - bbox_image[1], 0)
        x2 = min(bbox_visible[2], bbox_image[2]) - bbox_image[0]
        y2 = min(bbox_visible[3], bbox_image[3]) - bbox_image[1]
        # show image if it is in the visible area
        xm1 = min(int(x1 / self.image_scale), self.width)
        ym1 = min(int(y1 / self.image_scale), self.height)
        xm2 = min(int(x2 / self.image_scale), self.width)
        ym2 = min(int(y2 / self.image_scale), self.height)
        if int(xm2 - xm1) > 0 and int(ym2 - ym1) > 0:
            image = self.image.crop((xm1, ym1, xm2, ym2))
            self.canvas.imagetk = ImageTk.PhotoImage(
                image.resize(
                    (
                        int(self.image_scale * image.width),
                        int(self.image_scale * image.height),
                    )
                )
            )
            if self.imageid:
                self.canvas.delete(self.imageid)
            self.imageid = self.canvas.create_image(
                max(bbox_visible[0], bbox_image[0]),
                max(bbox_visible[1], bbox_image[1]),
                anchor="nw",
                image=self.canvas.imagetk,
            )

    def wheel_scroll(self, evt):
        """Scroll image up/down using mouse wheel"""
        if evt.state == 0:
            if is_mac():
                self.canvas.yview_scroll(-1 * (evt.delta), "units")
            else:
                self.canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
        if evt.state == 1:
            if is_mac():
                self.canvas.xview_scroll(-1 * (evt.delta), "units")
            else:
                self.canvas.xview_scroll(int(-1 * (evt.delta / 120)), "units")
        self.show_image()

    def load_image(self, filename=None):
        """Load or clear the given image file.

        Args:
            filename: Optional name of image file. If none given, clear image.
        """
        if os.path.isfile(filename):
            self.image = Image.open(filename)
            self.width, self.height = self.image.size
            if self.container:
                self.canvas.delete(self.container)
            self.container = self.canvas.create_rectangle(
                0, 0, self.width, self.height, width=0
            )
            self.canvas.config(scrollregion=self.canvas.bbox(self.container))
            self.canvas.yview_moveto(0)
            self.canvas.xview_moveto(0)
            self.show_image()
        else:
            self.image = None

    def is_image_loaded(self):
        """Return if an image is currently loaded"""
        return self.image is not None


class StatusBar(ttk.Frame):
    """Statusbar at the bottom of the screen.

    Fields in statusbar can be automatically or manually updated.
    """

    def __init__(self, parent):
        """Initialize statusbar within given frame.

        Args:
            parent: Frame to contain status bar.
        """
        super().__init__(parent)
        self.fields = {}
        self.callbacks = {}
        self._update()

    def add(self, key, update=None, **kwargs):
        """Add field to status bar

        Args:
            key: Key to use to refer to field.
            update: Optional callback function that returns a string.
              If supplied, field will be regularly updated automatically with
              the string returned by ``update()``. If argument not given,
              application is responsible for updating, using ``set(key)``.
        """
        self.fields[key] = ttk.Button(self, takefocus=0, **kwargs)
        self.callbacks[key] = update
        self.fields[key].grid(column=len(self.fields), row=0)

    def set(self, key, value):
        """Set field in statusbar to given value.

        Args:
            key: Key to refer to field.
            value: String to use to update field.
        """
        self.fields[key].config(text=value)

    def _update(self):
        """Update fields in statusbar that have callbacks. Updates every
        200 milliseconds.
        """
        for key in self.fields:
            if self.callbacks[key]:
                self.set(key, self.callbacks[key]())
        self.after(200, self._update)

    def add_binding(self, key, event, callback):
        """Add an action to be executed when the given event occurs

        Args:
            key: Key to refer to field.
            callback: Function to be called when event occurs.
            event: Event to trigger action. Use button release to avoid
              clash with button activate appearance behavior.
        """
        mouse_bind(self.fields[key], event, lambda *args: callback())


def mouse_bind(widget, event, callback):
    """Bind mouse button callback to event on widget.

    If binding is to mouse button 2 or 3, also bind the other button
    to support all platforms and 2-button mice.

    Args:
        widget: Widget to bind to
        event: Event string to trigger callback
        callback: Function to be called when event occurs
    """
    widget.bind(event, callback)

    if match := re.match(r"(<.*Button.*)([23])(>)", event):
        other_button = "2" if match.group(2) == "3" else "3"
        other_event = match.group(1) + other_button + match.group(3)
        widget.bind(other_event, callback)


def sound_bell():
    """Sound warning bell audibly and/or visually.

    Audible uses the default system bell sound.
    Visible flashes the first statusbar button (must be ttk.Button)
    Preference "Bell" contains "Audible", "Visible", both or neither
    """
    bell_pref = preferences["Bell"]
    if "Audible" in bell_pref:
        root().bell()
    if "Visible" in bell_pref:
        bell_button = statusbar().fields["rowcol"]
        # Belt & suspenders: uses the "disabled" state of button in temporary style,
        # but also restores setting in temporary style, and restores default style.
        style = ttk.Style()
        # Set temporary style's disabled bg to red, inherting
        style.map("W.TButton", foreground=[("disabled", "red")])
        # Save current disabled bg default for buttons
        save_bg = style.lookup("TButton", "background", state=[("disabled")])
        # Save style currently used by button
        cur_style = statusbar().fields["rowcol"]["style"]
        # Set button to use temporary style
        bell_button.configure(style="W.TButton")
        # Flash 3 times
        for state in ("disabled", "normal", "disabled", "normal", "disabled", "normal"):
            bell_button["state"] = state
            bell_button.update()
            bell_button.after(50)
        # Set button to use its previous style again
        bell_button.configure(style=cur_style)
        # Just in case, set the temporary style back to the default
        style.map("W.TButton", background=[("disabled", save_bg)])


def root():
    """Return the single instance of Root"""
    return MainWindow.root


def mainimage():
    """Return the single MainImage widget"""
    return MainWindow.mainimage


def maintext():
    """Return the single MainText widget"""
    return MainWindow.maintext


def menubar():
    """Return the single Menu widget used as the menubar"""
    return MainWindow.menubar


def statusbar():
    """Return the single StatusBar widget"""
    return MainWindow.statusbar
