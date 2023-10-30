#
# GGmainimage is a frame, containing a label which can display a png/jpeg file
# NOTE: requires `pip install Pillow`

import os.path
from PIL import Image, ImageTk
import tkinter as tk


class GGmainimage(tk.Frame):  # Can't use ttk.Frame or it's not un/dockable
    def __init__(self, parent):
        tk.Frame.__init__(
            self, parent, borderwidth=2, relief=tk.SUNKEN, name="*Image Viewer*"
        )

        self.label = tk.Label(self, text="No image")
        self.label.grid(column=0, row=0)
        self.photo = None

    #
    # Load the given image file, or display"No image" label
    def loadImage(self, filename=None):
        if os.path.isfile(filename):
            image = Image.open(filename)
            width = 300
            scale = width / image.width
            height = image.height * scale
            image = image.resize((int(width), int(height)))

            self.photo = ImageTk.PhotoImage(image)
            self.label.config(image=self.photo)
        else:
            self.label.config(image="")
