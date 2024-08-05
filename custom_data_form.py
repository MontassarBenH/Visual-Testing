import tkinter as tk
from tkinter import ttk

class CustomDataForm(tk.Toplevel):
    def __init__(self, master, default_data):
        super().__init__(master)
        self.title("Custom Data Input")
        self.default_data = default_data
        self.entries = {}
        self.result = None
        self.create_form()
        self.focus()
        self.grab_set()

    def create_form(self):
        row = 0
        for key, value in self.default_data.items():
            label = tk.Label(self, text=key)
            label.grid(row=row, column=0, padx=10, pady=5, sticky=tk.W)
            entry = tk.Entry(self)
            entry.insert(0, value)
            entry.grid(row=row, column=1, padx=10, pady=5)
            self.entries[key] = entry
            row += 1

        save_button = tk.Button(self, text="Save", command=self.save_data)
        save_button.grid(row=row, column=0, columnspan=2, pady=10)

    def save_data(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}
        self.destroy()