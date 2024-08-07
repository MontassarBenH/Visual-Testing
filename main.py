import tkinter as tk
from test_app import TestApp
from data_loader import load_test_data

def main():
    root = tk.Tk()
    app = TestApp(root)
    test_data = load_test_data("test_data.json")
    app.start_test_process(test_data)
    root.mainloop()

if __name__ == "__main__":
    main()