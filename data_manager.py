import json
import os

# DATA_DIR = "../data" # If you had this for the 'assets' structure
DATA_DIR = "data" # Should now work directly
MAP_DIR = os.path.join(DATA_DIR, "maps")
ENTITY_DIR = os.path.join(DATA_DIR, "entities")
ABILITY_DIR = os.path.join(DATA_DIR, "abilities") # Keep for listing or other purposes

def ensure_dirs():
    os.makedirs(MAP_DIR, exist_ok=True)
    os.makedirs(ENTITY_DIR, exist_ok=True)
    os.makedirs(ABILITY_DIR, exist_ok=True) # Ensure ability dir also exists

ensure_dirs()

def save_json(data, filepath):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        # print(f"Data saved to {filepath}")
    except IOError as e:
        print(f"Error saving JSON to {filepath}: {e}")

def load_json(filepath):
    """Loads data from a JSON file."""
    if not os.path.exists(filepath):
        # print(f"File not found: {filepath}")
        return None
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        # print(f"Data loaded from {filepath}")
        return data
    except IOError as e:
        print(f"Error loading JSON from {filepath}: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filepath}: {e}")
    return None

# --- Map Data Functions ---
def save_map_data(map_name, map_data):
    """Saves map data (tiles, heightmap, entities)."""
    filepath = os.path.join(MAP_DIR, f"{map_name}.json")
    save_json(map_data, filepath)

def load_map_data(map_name):
    """Loads map data."""
    filepath = os.path.join(MAP_DIR, f"{map_name}.json")
    return load_json(filepath)

# --- Entity Data Functions ---
def save_entity_data(entity_id, entity_data):
    """Saves entity data (stats, abilities, description)."""
    filepath = os.path.join(ENTITY_DIR, f"{entity_id}.json")
    save_json(entity_data, filepath)

def load_entity_data(entity_filename_or_id):
    """Loads entity data. entity_filename_or_id can be 'player_char' or 'player_char.json'."""
    filename = entity_filename_or_id
    if not entity_filename_or_id.endswith(".json"):
        filename = f"{entity_filename_or_id}.json"
    filepath = os.path.join(ENTITY_DIR, filename)
    data = load_json(filepath)
    if data:
        data['id'] = filename.replace(".json", "") # Ensure id is present
    return data

def list_available_maps():
    """Lists all .json files in the maps directory."""
    if not os.path.exists(MAP_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(MAP_DIR) if f.endswith(".json")]

def list_available_entities():
    """Lists all .json files in the entities directory."""
    if not os.path.exists(ENTITY_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(ENTITY_DIR) if f.endswith(".json")]

# --- Ability Data Functions ---

def load_all_abilities_from_categorized_json():
    """
    Loads all abilities from categorized JSON files (e.g., attacks.json, movement.json)
    in the ABILITY_DIR. Each file contains a dictionary of abilities, where the key
    is the ability_id and the value is the ability's data.
    Returns a single dictionary merging all abilities from all files.
    """
    all_abilities_data = {}
    if not os.path.exists(ABILITY_DIR):
        print(f"Ability directory not found: {ABILITY_DIR}")
        return all_abilities_data

    for filename in os.listdir(ABILITY_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ABILITY_DIR, filename)
            category_data = load_json(filepath)
            if category_data and isinstance(category_data, dict):
                for ability_id, ability_info in category_data.items():
                    if ability_id in all_abilities_data:
                        print(f"Warning: Duplicate ability ID '{ability_id}' found in {filename}. It will be overwritten.")
                    # Store the raw data; Ability object creation will happen in abilities.py
                    all_abilities_data[ability_id] = ability_info
            elif category_data is not None: # File loaded but was not a dict
                 print(f"Warning: Ability file {filename} does not contain a valid dictionary of abilities. Skipping.")

    return all_abilities_data

# The following functions for individual ability files might be deprecated or changed
# if all abilities are stored in categorized files.

# def save_ability_data(ability_id_name, ability_data):
#     """Saves a single ability's data to a JSON file."""
#     # This might need to change if we save to categorized files.
#     # For now, it would save to data/abilities/<ability_id_name>.json
#     filepath = os.path.join(ABILITY_DIR, f"{ability_id_name}.json")
#     save_json({ability_id_name: ability_data}, filepath) # Save it nested like in categorized files for consistency

# def load_ability_data(ability_id_name):
#     """Loads a single ability's data from its JSON file."""
#     filepath = os.path.join(ABILITY_DIR, f"{ability_id_name}.json")
#     data = load_json(filepath)
#     # Expects the file to contain { "ability_id_name": { ...details... } } or just { ...details... }
#     if data:
#         if ability_id_name in data: # If nested
#             return data[ability_id_name]
#         return data # If not nested (older single files)
#     return None

def list_available_ability_ids():
    """
    Lists all available ability IDs by scanning the categorized JSON files.
    This replaces the old list_available_abilities which listed filenames.
    """
    all_ids = []
    if not os.path.exists(ABILITY_DIR):
        return all_ids
    
    for filename in os.listdir(ABILITY_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ABILITY_DIR, filename)
            category_data = load_json(filepath)
            if category_data and isinstance(category_data, dict):
                all_ids.extend(category_data.keys())
    return sorted(list(set(all_ids))) # Return unique, sorted list


if __name__ == '__main__':
    # Example Usage:
    ensure_dirs()

    # Create sample categorized ability files (if they don't exist)
    sample_movement_abilities = {
        "move": {
            "name": "Move", "ap_cost": 1, "range": 1, "damage_amount": 0, 
            "damage_type": None, "target_type": "TILE", 
            "description": "Move to an adjacent valid tile.", "effect_radius": 0
        }
    }
    save_json(sample_movement_abilities, os.path.join(ABILITY_DIR, "movement.json"))

    sample_attack_abilities = {
        "pistol_shot": {
            "name": "Pistol Shot", "ap_cost": 2, "range": 5, "damage_amount": 10,
            "damage_type": "physical", "target_type": "ENEMY",
            "description": "Ranged attack.", "effect_radius": 0
        },
        "fireball": {
            "name": "Fireball", "ap_cost": 4, "range": 6, "damage_amount": 25,
            "damage_type": "fire", "target_type": "ENEMY", "effect_radius": 1,
            "description": "Explosive fire attack."
        }
    }
    save_json(sample_attack_abilities, os.path.join(ABILITY_DIR, "attacks.json"))

    # Test loading all abilities
    print("\n--- Testing load_all_abilities_from_categorized_json ---")
    loaded_abilities_data = load_all_abilities_from_categorized_json()
    if loaded_abilities_data:
        for ab_id, ab_data in loaded_abilities_data.items():
            print(f"ID: {ab_id}, Name: {ab_data.get('name')}, AP: {ab_data.get('ap_cost')}")
    else:
        print("No abilities loaded.")

    print("\n--- Testing list_available_ability_ids ---")
    available_ids = list_available_ability_ids()
    print(f"Available ability IDs: {available_ids}")


    # ... (rest of the original __main__ for maps and entities) ...
    # Create a sample map
    sample_map = {
        "name": "Test Arena",
        "tiles": [
            ["#", "#", "#", "#", "#"],
            ["#", ".", ".", ".", "#"],
            ["#", ".", "@", ".", "#"],
            ["#", ".", "E", ".", "#"],
            ["#", "#", "#", "#", "#"]
        ],
        "heightmap": [
            [1, 1, 1, 1, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1]
        ],
        "entities_on_map": [
            {"id": "player_char", "x": 2, "y": 2},
            {"id": "goblin_1", "x": 2, "y": 3}
        ]
    }
    save_map_data("test_arena", sample_map)
    loaded_map = load_map_data("test_arena")
    # print("Loaded Map:", loaded_map)

    # Create a sample entity (player)
    player_entity = {
        "id": "player_char",
        "name": "Hero",
        "char": "@",
        "description": "The protagonist.",
        "hp": 100,
        "max_hp": 100,
        "ap": 5,
        "max_ap": 5,
        "abilities": ["move", "pistol_shot"], # Use new IDs
        "behavior": "player_controlled"
    }
    save_entity_data("player_char", player_entity)

    # Create a sample NPC entity
    goblin_entity = {
        "id": "goblin_1",
        "name": "Goblin Grunt",
        "char": "g",
        "description": "A weak but feisty goblin.",
        "hp": 30,
        "max_hp": 30,
        "ap": 3,
        "max_ap": 3,
        "abilities": ["move", "pistol_shot"], # Use new IDs
        "behavior": "move_towards_player"
    }
    save_entity_data("goblin_1", goblin_entity)

    loaded_player = load_entity_data("player_char")
    # print("Loaded Player:", loaded_player)

    print("\nAvailable maps:", list_available_maps())
    print("Available entities:", list_available_entities())
