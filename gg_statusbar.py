# GGstatusbar - status bar at the bottom of the screen
# Label can be added with optional callback that returns a string
# Callbacks will be called regularly to update labels
# Labels without callbacks will be updated manually by the application using set()

import tkinter as tk


class GGstatusbar(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent, borderwidth=1, relief=tk.SUNKEN)
        self.labels = {}
        self.callbacks = {}
        self._update()

    #
    # Add label to status bar, with optional callback used when updating it
    def add(self, key, callback=None, **kwargs):
        kwargs["borderwidth"] = 1
        kwargs["relief"] = tk.RIDGE
        self.labels[key] = tk.Label(self, kwargs)
        self.callbacks[key] = callback
        self.labels[key].pack(side=tk.LEFT)

    def set(self, key, value):
        self.labels[key].config(text=value)

    def _update(self):
        for key in self.labels:
            if self.callbacks[key]:
                self.set(key, self.callbacks[key]())
        self.after(200, self._update)
