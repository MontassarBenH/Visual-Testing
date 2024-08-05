import json

def load_test_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Test data file '{file_path}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in test data file '{file_path}'.")
        return {}