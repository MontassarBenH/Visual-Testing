import json
import logging

def load_test_data(file_path):
    print(f"Attempting to load test data from {file_path}")
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        print("Test data loaded successfully")
        return data
    except FileNotFoundError:
        print(f"Error: Test data file not found at {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in test data file {file_path}")
        return {}
    except Exception as e:
        print(f"Unexpected error loading test data: {e}")
        return {}