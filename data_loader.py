import json
import logging

def load_test_data(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        logging.info(f"Test data loaded from {filename}")
        return data
    except Exception as e:
        logging.error(f"Error loading test data from {filename}: {str(e)}")
        return None