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
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        for key, value in self.default_data.items():
            label = ttk.Label(scrollable_frame, text=key)
            label.pack(fill=tk.X, padx=5, pady=2)
            entry = ttk.Entry(scrollable_frame)
            entry.insert(0, value)
            entry.pack(fill=tk.X, padx=5, pady=2)
            self.entries[key] = entry

        save_button = ttk.Button(scrollable_frame, text="Save", command=self.save_data)
        save_button.pack(pady=10)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def save_data(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}
        self.destroy()