import argparse
import tkinter as tk
from test_app import TestApp
from data_loader import load_test_data

def main():
    parser = argparse.ArgumentParser(description="Run automated tests for web applications.")
    parser.add_argument("--scenario", required=True, help="Name of the test scenario to run")
    parser.add_argument("--website", required=True, help="Website URL to test")
    parser.add_argument("--email", required=True, help="Email address to send the report")
    args = parser.parse_args()

    root = tk.Tk()
    app = TestApp(root)

    test_data = load_test_data("test_data.json")

    scenario_key_map = {
        "register": "user_registration",
        "login": "user_login"
    }

    data_key = scenario_key_map.get(args.scenario, args.scenario)
    data = test_data.get(data_key, {})

    app.run_test(args.scenario, args.website, args.email, data)

    root.mainloop()

if __name__ == "__main__":
    main()