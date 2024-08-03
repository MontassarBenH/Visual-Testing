import json

def load_test_data(filepath):
    with open(filepath, 'r') as file:
        data = json.load(file)
    print("Loaded Test Data: ", data)  # Debugging line
    return data
