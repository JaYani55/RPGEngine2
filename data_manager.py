import json
import os

DATA_DIR = "data"
MAP_DIR = os.path.join(DATA_DIR, "maps")
ENTITY_DIR = os.path.join(DATA_DIR, "entities")

def ensure_dirs():
    os.makedirs(MAP_DIR, exist_ok=True)
    os.makedirs(ENTITY_DIR, exist_ok=True)

ensure_dirs() # Ensure directories exist when this module is imported

def save_json(data, filepath):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data saved to {filepath}")
    except IOError as e:
        print(f"Error saving data to {filepath}: {e}")

def load_json(filepath):
    """Loads data from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return None
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        print(f"Data loaded from {filepath}")
        return data
    except IOError as e:
        print(f"Error loading data from {filepath}: {e}")
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
    if entity_filename_or_id.endswith(".json"):
        filename = entity_filename_or_id
    else:
        filename = f"{entity_filename_or_id}.json"
    filepath = os.path.join(ENTITY_DIR, filename)
    data = load_json(filepath)
    if data:
        # Could potentially instantiate an Entity object here if classes are defined
        return data
    return None

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

if __name__ == '__main__':
    # Example Usage:
    ensure_dirs()

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
        "abilities": ["pistol_shot"],
        "behavior": "player_controlled"
    }
    save_entity_data("player_char", player_entity)

    # Create a sample NPC entity
    goblin_entity = {
        "id": "goblin_1",
        "name": "Goblin Grunt",
        "char": "g", # Changed from E to avoid conflict with renderer default
        "description": "A weak but feisty goblin.",
        "hp": 30,
        "max_hp": 30,
        "ap": 3,
        "max_ap": 3,
        "abilities": ["pistol_shot"], # Goblins with pistols!
        "behavior": "move_towards_player" # or "run_away_from_player"
    }
    save_entity_data("goblin_1", goblin_entity)

    loaded_player = load_entity_data("player_char")
    # print("Loaded Player:", loaded_player)

    print("Available maps:", list_available_maps())
    print("Available entities:", list_available_entities())

    # Example of creating a new entity in the editor (conceptual)
    new_npc_data = {
        "id": "orc_brute",
        "name": "Orc Brute",
        "char": "O",
        "description": "A hulking orc.",
        "hp": 80, "max_hp": 80,
        "ap": 4, "max_ap": 4,
        "abilities": ["basic_attack"], # A different ability
        "behavior": "move_towards_player"
    }
    # In editor: user inputs this, then calls:
    # save_entity_data(new_npc_data["id"], new_npc_data)
