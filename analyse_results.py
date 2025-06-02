# Part 2: Initial file handling

from pygbif import species
import pandas as pd
import json
import requests
import time

# Read and parse the nested JSON data
def parse_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        # Parse the nested JSON strings into dictionaries
        parsed_data = {k: json.loads(v) for k, v in data.items()}
        return pd.DataFrame.from_dict(parsed_data, orient='index')

answer_sheet = parse_json_file("./plant_identification/answer_sheet.json")
plant_id_results = parse_json_file("./plant_identification/plant_id_results.json")

# join answer_sheet and plant_id_results
joined_data = answer_sheet.merge(plant_id_results, left_index=True, right_index=True)

