# Part 3: Analysis of Plant Identification Data

import pandas as pd
import requests
from pygbif import species
import time

# Load Data
input_csv = 'plant_identification/processed_plant_data.csv'
df = pd.read_csv(input_csv)

# Collect Unique Names
name_columns = ['Correct Answer', 'Guess 1', 'Guess 2', 'Guess 3']
all_names = set(df[name_columns].values.flatten())

# 3. Standardize Names (TNRS) - stub implementation
# TODO: Replace with real TNRS API call if desired
# I noticed the AI tends to use correct scientific names, so we can assume they work for this example.
name_to_accepted = {name: name for name in all_names}

# Retrieve Lineages (GBIF)
def get_gbif_lineage(scientific_name):
    try:
        data = species.name_backbone(name=scientific_name, rank="species", kingdom="Plantae")
        if not data or 'usageKey' not in data:
            return None
        lineage = {
            'kingdom': data.get('kingdom'),
            'phylum': data.get('phylum'),
            'class': data.get('class'),
            'order': data.get('order'),
            'family': data.get('family'),
            'genus': data.get('genus'),
            'species': data.get('species') or (data.get('scientificName').split()[-1] if data.get('scientificName') else None)
        }
        return lineage
    except Exception as e:
        print(f"Error retrieving lineage for {scientific_name}: {e}")
        return None

accepted_names = set(name_to_accepted.values())
accepted_to_lineage = {}
for name in accepted_names:
    lineage = get_gbif_lineage(name)
    accepted_to_lineage[name] = lineage
    time.sleep(0.2)  # Be polite to the API

# Calculate "Taxonomic Distance"
def taxonomic_distance(lin1, lin2):
    # Compare from kingdom to species; return the number of ranks at which they differ
    ranks = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
    for i, rank in enumerate(ranks):
        if lin1.get(rank) != lin2.get(rank):
            return len(ranks) - i  # Distance is number of remaining ranks
    return 0  # would be 100% correct match

# Calculate distances for each guess
dist_cols = []
for i in range(1, 4):
    col = f'Distance_{i}'
    dist_cols.append(col)
    distances = []
    for idx, row in df.iterrows():
        correct = name_to_accepted[row['Correct Answer']]
        guess = name_to_accepted[row[f'Guess {i}']]
        lin1 = accepted_to_lineage.get(correct)
        lin2 = accepted_to_lineage.get(guess)
        if lin1 is None or lin2 is None:
            distances.append(None)
        else:
            distances.append(taxonomic_distance(lin1, lin2))
    df[col] = distances

# Analyse Results
print(df)
print("\nAverage distances:")
print(df[dist_cols].mean())
print("\nDistance frequency:")
for col in dist_cols:
    print(f"{col} value counts:")
    print(df[col].value_counts())
    print()

# Save results
df.to_csv('plant_identification/plant_id_distance_results.csv', index=False)

# TODO: Implement real TNRS name standardization if needed (see comments above)