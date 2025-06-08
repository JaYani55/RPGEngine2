# Main Systems Documentation - ASCII Tactical RPG

This document outlines the core systems and architecture of the ASCII Tactical RPG engine.

## Table of Contents

1.  [Project Overview](#project-overview)
2.  [Core Architecture](#core-architecture)
    *   [Main Loop (`main.py`)](#main-loop-mainpy)
    *   [Configuration (`config.py`)](#configuration-configpy)
    *   [Utilities (`utils.py`)](#utilities-utilspy)
3.  [Data Management (`data_manager.py`)](#data-management-data_managerpy)
    *   [JSON Storage](#json-storage)
    *   [Entity Data](#entity-data)
    *   [Map Data](#map-data)
4.  [Game Engine (`engine.py`)](#game-engine-enginepy)
    *   [Entity Class](#entity-class)
    *   [GameMap Class](#gamemap-class)
    *   [GameEngine Class](#gameengine-class)
    *   [Combat System](#combat-system)
    *   [Turn Management](#turn-management)
    *   [NPC AI](#npc-ai)
    *   [Height System](#height-system)
5.  [AI System (`ai.py`)](#ai-system-ai.py)
6.  [Renderer (`renderer.py`)](#renderer-rendererpy)
    *   [ASCII Rendering](#ascii-rendering)
    *   [Camera System](#camera-system)
7.  [User Interface (`ui.py`)](#user-interface-uipy)
    *   [Main Menu](#main-menu)
    *   [Map Selection](#map-selection)
    *   [Game UI](#game-ui)
    *   [Editor UI](#editor-ui)
8.  [Game Logic (`game.py`)](#game-logic-gamepy)
    *   [Game States](#game-states)
    *   [Input Handling](#input-handling)
9.  [Map Editor (`editor.py`)](#map-editor-editorpy)
    *   [Tile Drawing](#tile-drawing)
    *   [Heightmap Editing](#heightmap-editing)
    *   [Entity Placement](#entity-placement)
    *   [Saving and Loading Maps](#saving-and-loading-maps)
10. [Interaction Flow](#interaction-flow)
11. [Programmatic Deep Dives](#programmatic-deep-dives)

## 1. Project Overview

This project is an ASCII-based tactical RPG developed in Python using the Pygame library. It features a round-based combat system, a map editor, and data storage via JSON files. The goal is to create a flexible engine that allows for the creation and play of tactical scenarios.

## 2. Core Architecture

The engine is modular, with different Python files handling specific aspects of the game.

### Main Loop (`main.py`)

*   **Purpose**: Serves as the entry point and central controller of the application. It manages the overall game state (main menu, editor, game, map selection) and transitions between them.
*   **Interaction**:
    *   Initializes Pygame and screen settings from `config.py`.
    *   Creates instances of `MainMenu`, `MapSelectionScreen`, `Editor`, `Game`, `Renderer`, and `DataManager`.
    *   Contains the main game loop that processes events, updates game logic based on the current state, and renders the screen.
    *   Handles user input to switch between states (e.g., starting the editor from the main menu, loading a map to play).

### Configuration (`config.py`)

*   **Purpose**: Centralizes all global constants and settings.
*   **Content**:
    *   `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `TILE_SIZE`, `FONT_SIZE`.
    *   `COLORS` dictionary (e.g., `COLOR_WHITE`, `COLOR_BLACK`, `COLOR_RED`).
    *   `FPS` (Frames Per Second).
    *   Map dimensions (`MAP_WIDTH`, `MAP_HEIGHT`).
    *   Maximum height level (`MAX_HEIGHT_LEVEL`).
*   **Interaction**: Imported by most other modules to ensure consistent settings across the application.

### Utilities (`utils.py`)

*   **Purpose**: Contains helper functions used by various parts of the engine.
*   **Content**:
    *   Currently, it might be minimal, but could include functions for distance calculations, coordinate transformations, or other common mathematical operations.
*   **Interaction**: Used by modules like `engine.py` or `editor.py` for common tasks.

## 3. Data Management (`data_manager.py`)

*   **Purpose**: Handles all file I/O operations, specifically for loading and saving game data in JSON format.
*   **Key Class**: `DataManager`.
*   **Interaction**:
    *   Provides methods like `save_map_data`, `load_map_data`, `save_entity_data`, `load_entity_data`.
    *   Ensures data is stored in and retrieved from the correct directories (`data/maps/`, `data/entities/`).
    *   Handles JSON serialization and deserialization.
    *   `engine.py` uses it to load entity definitions.
    *   `editor.py` uses it to save and load map files.
    *   `game.py` uses it to load map and entity data when starting a game.

### JSON Storage

*   All persistent data (maps, entity templates) is stored in JSON files. This format is human-readable and easy to parse.

### Entity Data (`data/entities/`)

*   Each entity template is a JSON file (e.g., `player_char.json`, `goblin_1.json`).
*   **Structure**:
    ```json
    {
        "name": "Player",
        "char": "@",
        "color": "COLOR_WHITE", // String representation, resolved by renderer/engine
        "hp": 100,
        "ap": 10,
        "abilities": ["pistol_shot"],
        "description": "The main character.",
        "ai_behavior": null // or "move_towards_player", "run_away" for NPCs
    }
    ```
*   The `DataManager` loads this data to create `Entity` instances in the `GameEngine`.

### Map Data (`data/maps/`)

*   Each map is a JSON file (e.g., `my_level.json`).
*   **Structure**:
    ```json
    {
        "map_name": "Test Level 1",
        "tiles": [
            ["#", "#", "#"],
            ["#", ".", "#"],
            ["#", "#", "#"]
        ],
        "heightmap": [
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1]
        ],
        "entities_on_map": [
            {
                "id": "player_char",
                "x": 1,
                "y": 1,
                "is_player_start": true,
                "faction": "player"
            },
            {
                "id": "goblin_1",
                "x": 2,
                "y": 1,
                "faction": "enemy",
                "behavior": "aggressive_melee" // Example: specifying AI behavior
            }
        ]
    }
    ```
*   `tiles`: 2D array of characters representing the visual appearance of map cells.
*   `heightmap`: 2D array of integers (0-5) representing the elevation of each tile.
*   `entities_on_map`: A list of dictionaries, each specifying an entity ID (linking to an entity JSON file), its position on the map, its team, and potentially overriding its default AI behavior via the `behavior` key.

## 4. Game Engine (`engine.py`)

*   **Purpose**: Contains the core game logic, including entity management, combat mechanics, AI, and turn handling.
*   **Key Classes**: `Entity`, `GameMap`, `GameEngine`.

### Entity Class (`Entity`)

*   **Purpose**: Represents any character or object in the game that can act or be interacted with (players, NPCs, potentially items).
*   **Attributes**:
    *   `id` (unique identifier, often from the filename like "player_char")
    *   `name`, `x`, `y`, `char`, `color`
    *   `hp`, `max_hp`, `ap`, `current_ap`, `defense`
    *   `abilities_ids`, `abilities` (list of `Ability` objects)
    *   `faction`, `sight_radius`
    *   `is_dead`, `status_effects`
    *   `behavior: Behavior | None` (an instance of an AI behavior strategy, e.g., `AggressiveMelee`, `Cautious`. `None` for player-controlled entities).
    *   `height` (current height level the entity is on, derived from map)
*   **Methods**:
    *   `move(dx, dy, game_map)`: Attempts to move the entity. Consumes AP. Checks for collisions and height differences.
    *   `attack(target_entity, ability_name)`: Performs an attack. Consumes AP. Calculates damage based on ability.
    *   `take_damage(amount)`: Reduces HP.
    *   `is_alive()`: Checks if HP > 0.
    *   `can_climb(current_height, target_height)`: Checks if entity can move between two height levels (max 1 level difference).
    *   `get_path_to(target_pos, game_map)`: Basic pathfinding (e.g., A* or simpler for now).
    *   `can_see(target_pos, game_map)`: Line of Sight (LOS) calculation (future feature).

### GameMap Class (`GameMap`)

*   **Purpose**: Represents the game world's structure.
*   **Attributes**:
    *   `width`, `height` (dimensions in tiles)
    *   `tiles` (2D array of characters for rendering)
    *   `heightmap` (2D array of integers for elevation)
    *   `entities` (list of `Entity` objects currently on this map) - *Correction: This is typically managed by `GameEngine` or `Game` state, `GameMap` primarily holds static terrain data.* The `GameEngine` will hold the list of entities and their positions, and query the `GameMap` for tile properties.
*   **Methods**:
    *   `is_walkable(x, y)`: Checks if a tile is passable (e.g., not a wall).
    *   `get_height(x, y)`: Returns the height of a tile.
    *   `get_tile_char(x, y)`: Returns the character for rendering a tile.
    *   `add_entity(entity, x, y)` / `remove_entity(entity)`: (May be handled by `GameEngine`).
    *   `get_entities_at(x, y)`: Returns entities at a specific tile.

### GameEngine Class (`GameEngine`)

*   **Purpose**: Orchestrates the game simulation. Manages entities, turns, combat resolution, and AI.
*   **Key Methods**:
    *   `initialize_entities_from_map_data()`: Loads entity definitions and map-specific entity data, creating `Entity` instances. Now also instantiates and assigns AI `Behavior` objects to NPCs based on the `behavior` string in map data, using the `create_behavior` factory from `ai.py`.
    *   `_execute_action()`: Handles the logic for an entity performing an action using an ability.
    *   `handle_player_action()`: Processes input for player actions.
    *   `run_npc_turn()`: For NPCs, this method now consults the entity's assigned `behavior` object (e.g., `AggressiveMelee`) to determine the NPC's action for the turn by calling its `choose_action()` method.
    *   `next_turn()`: Advances the game to the next entity's turn.
    *   `find_path()`: Calculates a path between two points.
    *   `is_target_in_ability_range()`: Checks ability range.

## 5. AI System (`ai.py`)

*   **Purpose**: Defines the artificial intelligence for Non-Player Characters (NPCs) using a Strategy design pattern. This allows for different behaviors to be easily assigned to entities.
*   **Core Components**:
    *   `Behavior` (Abstract Base Class): Defines the interface for all AI behaviors, primarily through the `choose_action(owner: Entity, engine: GameEngine)` method. This method is expected to return a tuple containing the `Ability` to use and the `target_position`, or `None` if no action is to be taken.
    *   Concrete Behavior Classes (e.g., `AggressiveMelee`, `Cautious`, `Defensive`):
        *   `AggressiveMelee`: NPCs will try to attack the player if in melee range. If not, they will attempt to move closer to the player.
        *   `Cautious`: NPCs will try to maintain a preferred distance from the player. They may attack if the player is at a medium range but will retreat if the player gets too close.
        *   `Defensive`: NPCs will generally stay in place (around a guard position) and attack the player only if they come within a certain radius. They will move back to their guard position if they stray too far.
    *   `create_behavior(behavior_name: str, **kwargs) -> Behavior`: A factory function that takes a string (e.g., "aggressive_melee", "cautious") and returns an instance of the corresponding behavior class. This is used by the `GameEngine` when initializing entities.
*   **Interaction**:
    *   The `GameEngine` assigns a `Behavior` instance to each NPC `Entity` during initialization, based on data from map files.
    *   During an NPC's turn (`run_npc_turn` in `GameEngine`), the engine calls the `choose_action` method of the NPC's `behavior` object.
    *   The chosen action (ability and target) is then executed by the `GameEngine`.

## 6. Renderer (`renderer.py`)

*   **Purpose**: Handles all drawing to the screen using Pygame.
*   **Key Class**: `Renderer`.
*   **Interaction**:
    *   Takes game state information (map, entities, UI elements) from `Game` or `Editor` and draws it.
    *   `main.py` calls the renderer's main draw method in each frame of the game loop.
*   **Methods**:
    *   `draw_game_state(surface, game_engine, game_ui, camera)`: Renders the game map, entities, and game UI.
    *   `draw_editor_state(surface, editor, editor_ui, camera)`: Renders the map editor interface.
    *   `draw_main_menu(surface, main_menu)`
    *   `draw_map_selection_screen(surface, map_selection_screen)`
    *   `draw_tile(surface, char, color, x, y, height)`: Draws a single map tile, potentially adjusting appearance based on height.
    *   `draw_entity(surface, entity, camera_offset_x, camera_offset_y)`
    *   `draw_ui_elements(surface, ui_elements)`
    *   `render_text(surface, text, position, color, font_size)`

### ASCII Rendering

*   The game uses ASCII characters to represent tiles, entities, and UI.
*   The `Renderer` maps characters and colors (from `config.py` and entity data) to Pygame drawing calls.
*   Font rendering is handled by Pygame's font module.

### Camera System

*   **Purpose**: Allows viewing different parts of a large map if it doesn't fit on the screen.
*   **Attributes (likely in `Editor` and `Game` states, used by `Renderer`):**
    *   `camera_x`, `camera_y`: Top-left coordinates of the camera view in world/map coordinates.
*   **Functionality**:
    *   The `Renderer` uses camera offsets to draw only the visible portion of the map and entities.
    *   Input handling in `Game` and `Editor` updates camera coordinates (e.g., arrow keys to pan).

## 7. User Interface (`ui.py`)

*   **Purpose**: Manages and renders all UI elements for different game states.
*   **Key Classes**: `MainMenu`, `MapSelectionScreen`, `GameUI`, `EditorUI`, `Button`.
*   **Interaction**:
    *   Each UI class holds data for its specific screen (buttons, text, layout).
    *   `main.py` instantiates these UI classes.
    *   The respective game state controllers (`Game`, `Editor`) interact with their UI components to get input or display information.
    *   `Renderer` uses UI objects to draw them.

### Main Menu (`MainMenu`)

*   **Elements**: Buttons for "Start Game" (leads to Map Selection), "Map Editor", "Quit".
*   **Logic**: Handles button clicks to transition game states via `main.py`.

### Map Selection (`MapSelectionScreen`)

*   **Elements**: Lists available maps (loaded by `DataManager`), buttons to select a map and "Play" or "Back".
*   **Logic**: Allows player to choose a map. On "Play", `main.py` transitions to the "game" state, passing the selected map file.

### Game UI (`GameUI`)

*   **Elements**:
    *   Displays player/entity stats (HP, AP).
    *   Current turn indicator.
    *   Action menu (e.g., "Move", "Attack", "End Turn").
    *   Log messages (e.g., combat results).
    *   Potentially a mini-map (future).
    *   Game Over/Victory message display.
*   **Logic**: Updates based on `GameEngine` state. Provides interface for player actions.

### Editor UI (`EditorUI`)

*   **Elements**:
    *   Tile selection palette.
    *   Height adjustment controls (+/-).
    *   Entity placement tools (select entity type, place on map).
    *   Save/Load map buttons.
    *   Current drawing mode indicator (e.g., "Draw Tiles", "Set Height", "Place Entities").
    *   Coordinates display.
*   **Logic**: Provides interface for map editing tools in `Editor`.

## 8. Game Logic (`game.py`)

*   **Purpose**: Manages the "game" state, integrating the `GameEngine`, `GameUI`, and `Renderer`.
*   **Key Class**: `Game`.
*   **Interaction**:
    *   Instantiated by `main.py` when the player starts a game.
    *   Initializes `GameEngine` with a selected map (loaded via `DataManager`).
    *   Contains the game loop specific to active gameplay.
*   **Attributes**:
    *   `game_engine` (instance of `GameEngine`)
    *   `game_ui` (instance of `GameUI`)
    *   `renderer` (passed from `main.py`)
    *   `data_manager` (passed from `main.py`)
    *   `camera_x`, `camera_y`
    *   `selected_map_path`
    *   `player_entity` (reference to the player in `game_engine`)
    *   `game_over_state` (e.g., None, "VICTORY", "DEFEAT")
*   **Methods**:
    *   `load_game_state(map_file_path)`: Loads map data, initializes `GameEngine` and entities.
    *   `handle_input(event)`: Processes player input (keyboard/mouse) for camera movement, selecting actions, targeting, etc. Translates input into commands for `GameEngine`.
    *   `update()`: Advances game logic. If it's player's turn, waits for input. If NPC's turn, calls `game_engine.process_npc_turn()`. Checks for game over conditions.
    *   `render(surface)`: Calls `renderer.draw_game_state()`.
    *   `check_game_over()`: Determines if win/loss conditions are met (e.g., player defeated, all enemies defeated).

### Game States (within `game.py`)

*   While `main.py` manages high-level states, `game.py` might manage sub-states of active gameplay, e.g.:
    *   `PLAYER_TURN_INPUT`: Waiting for player to choose an action.
    *   `PLAYER_TURN_TARGETING`: Player has chosen an attack, now selecting a target.
    *   `NPC_TURN_PROCESSING`: AI is calculating its move.
    *   `GAME_OVER`: Displaying end-game message.

### Input Handling

*   Pygame events are caught in `game.py`'s loop.
*   Mapped to actions:
    *   Arrow keys: Move player (if selected and in move mode), pan camera.
    *   Mouse clicks: Select entities, UI buttons, target locations.
    *   Keyboard shortcuts for actions.

## 9. Map Editor (`editor.py`)

*   **Purpose**: Allows users to create and modify game maps.
*   **Key Class**: `Editor`.
*   **Interaction**:
    *   Instantiated by `main.py` when "Map Editor" is selected.
    *   Manages map data (tiles, heights, entity placements) directly.
    *   Uses `DataManager` to save and load maps.
    *   Uses `Renderer` to display the editor interface and map.
*   **Attributes**:
    *   `map_data` (dictionary holding `tiles`, `heightmap`, `entities_on_map`)
    *   `current_tile_char` (selected for drawing)
    *   `current_height_value` (selected for setting height)
    *   `selected_entity_id` (for placement)
    *   `editor_ui` (instance of `EditorUI`)
    *   `renderer` (passed from `main.py`)
    *   `data_manager` (passed from `main.py`)
    *   `camera_x`, `camera_y`
    *   `edit_mode` ("draw_tiles", "set_height", "place_entities", "erase_entities")
    *   `available_entity_ids` (loaded from `data/entities/` by `DataManager`)
*   **Methods**:
    *   `handle_input(event)`: Processes user input for drawing, changing modes, saving/loading.
    *   `update()`: Updates editor state based on input.
    *   `render(surface)`: Calls `renderer.draw_editor_state()`.
    *   `draw_tile_on_map(mouse_x, mouse_y)`
    *   `set_tile_height(mouse_x, mouse_y)`
    *   `place_entity_on_map(mouse_x, mouse_y)`
    *   `erase_entity_at(mouse_x, mouse_y)`
    *   `save_map(filename)`: Uses `data_manager.save_map_data()`.
    *   `load_map(filename)`: Uses `data_manager.load_map_data()` and populates editor state.
    *   `new_map()`: Creates a blank map structure.

### Tile Drawing

*   User selects a character from a palette in `EditorUI`.
*   Clicking on the map grid places the selected tile character into `map_data['tiles']`.

### Heightmap Editing

*   User selects a height value (0-5) or uses increment/decrement buttons in `EditorUI`.
*   Clicking on a map tile sets its corresponding value in `map_data['heightmap']`.

### Entity Placement

*   User selects an entity type from a list (populated from `data/entities/` files) in `EditorUI`.
*   Clicking on the map places an entry into `map_data['entities_on_map']` with the entity ID and coordinates.
*   The editor should also allow setting the `team` and `ai_behavior` for placed NPCs.
*   The editor allows creation of new entity *definitions* by prompting for stats, abilities, char, etc., and then saving this as a new JSON file in `data/entities/` using `DataManager`. This makes the new entity type available for placement.

### Saving and Loading Maps

*   Uses `DataManager` to interact with JSON files in `data/maps/`.
*   UI provides prompts for filenames.

## 10. Interaction Flow Example (Starting a Game)

1.  **`main.py`**: Starts, displays `MainMenu` (via `ui.py` and `renderer.py`).
2.  User clicks "Start Game".
3.  **`main.py`**: Transitions state to "map_selection". Displays `MapSelectionScreen`.
    *   `MapSelectionScreen` (with `DataManager`) lists maps from `data/maps/`.
4.  User selects a map (e.g., `level1.json`) and clicks "Play".
5.  **`main.py`**: Transitions state to "game". Creates `Game` instance, passing the selected map path (`"data/maps/level1.json"`), `Renderer`, and `DataManager`.
6.  **`game.py` (`Game.load_game_state`)**:
    *   Uses `data_manager.load_map_data("data/maps/level1.json")` to get map structure.
    *   Initializes `GameEngine`.
    *   `game_engine.initialize_map(map_data)` sets up the `GameMap`.
    *   `game_engine.initialize_entities_from_map_data(map_data['entities_on_map'])`:
        *   For each entity in `map_data['entities_on_map']`:
            *   Uses `data_manager.load_entity_data(entity_id)` to get base stats (e.g., from `data/entities/player_char.json`).
            *   Creates an `Entity` instance with these stats and map-specific position/team.
        *   Identifies and stores the player entity.
7.  **`game.py`**: Enters its main loop: `handle_input()`, `update()`, `render()`.
8.  **`game.py` (`update`)**:
    *   Determines current turn (e.g., player).
    *   If player turn, waits for input via `handle_input()`.
    *   Player issues a move command.
    *   `game.py` calls `game_engine.handle_movement(player_entity, dx, dy)`.
9.  **`engine.py` (`GameEngine.handle_movement`)**:
    *   Checks `game_map.is_walkable()`.
    *   Checks `game_map.get_height()` and `player_entity.can_climb()`.
    *   If valid, updates `player_entity.x, player_entity.y`, consumes AP.
10. **`game.py` (`render`)**: Calls `renderer.draw_game_state(surface, game_engine, game_ui, camera)`.
11. **`renderer.py`**: Draws map tiles, entities (using their `char`, `color`, `x`, `y`), and UI elements from `GameUI`.
12. Loop continues, processing turns, actions, and rendering until a game over condition is met or the player quits.

This detailed breakdown should provide a comprehensive understanding of the engine's systems and their interactions.

## 11. Programmatic Deep Dives

This section provides a closer look at the code implementation of key systems.

### 11.1 `config.py` - Configuration Hub

The `config.py` file centralizes static settings for the game, ensuring consistency across modules. It primarily defines constants.

*   **Screen and Display**: `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `FPS`.
*   **Rendering**: `TILE_SIZE`, `FONT_NAME`, `FONT_SIZE`.
*   **Colors**: A comprehensive `COLORS` dictionary is key for styling.
    ```python
    # Example from config.py
    COLORS = {
        "white": (255, 255, 255),
        "black": (0, 0, 0),
        # ... many more colors ...
        "ui_background": (30, 30, 40),
        "highlight_move": (50, 150, 255, 120), # RGBA, A for alpha
    }
    ```
*   **Game Mechanics**: `MAX_CLIMB_HEIGHT_DIFFERENCE`, `MAX_MAP_HEIGHT_LEVEL`.

### 11.2 `utils.py` - Utility Belt

Contains standalone helper functions.

*   **Distance Calculations**:
    ```python
    # Example from utils.py
    import math

    def distance(p1, p2):
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def manhattan_distance(p1, p2):
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
    ```
*   **Value Clamping**: `clamp(value, min_val, max_val)`.
*   **Coordinate Conversion**: `grid_to_pixel(grid_x, grid_y, tile_size)` and `pixel_to_grid(pixel_x, pixel_y, tile_size)`.

### 11.3 `data_manager.py` - Data Persistence

Handles loading and saving game data, primarily in JSON format.

*   **Core JSON Operations**:
    ```python
    # Example from data_manager.py
    import json
    import os

    def save_json(data, filepath):
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            # print(f"Data saved to {filepath}")
        except IOError as e:
            print(f"Error saving data to {filepath}: {e}")

    def load_json(filepath):
        if not os.path.exists(filepath): return None
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading/decoding {filepath}: {e}")
        return None
    ```
*   **Directory Management**: `DATA_DIR`, `MAP_DIR`, `ENTITY_DIR` constants and `ensure_dirs()` to create them upon import.
*   **Specific Data Handlers**:
    *   `save_map_data(map_name, map_data)` and `load_map_data(map_name)`: Construct filepath in `MAP_DIR` and call `save_json`/`load_json`.
    *   `save_entity_data(entity_id, entity_data)` and `load_entity_data(entity_filename_or_id)`: Similar for `ENTITY_DIR`.
        *   `load_entity_data` correctly handles if `entity_filename_or_id` already includes `.json`.
*   **Listing Available Data**: `list_available_maps()` and `list_available_entities()` scan respective directories for `.json` files and return names without the extension.

### 11.4 `engine.py` - Core Game Logic

This is the heart of the gameplay simulation, defining entities, the map structure, and the rules governing their interaction.

#### `Entity` Class

Represents any active game object (player, NPCs).

*   **Attributes**: `x`, `y` (position), `char` (ASCII representation), `name`, `hp`, `max_hp`, `ap` (action points), `max_ap`, `abilities` (list of strings), `behavior` (e.g., "player_controlled", "move_towards_player"), `entity_id` (original ID from JSON).
*   **Movement (`move` method)**:
    ```python
    # Snippet from Entity.move() in engine.py
    # def move(self, dx, dy, game_map):
    #     new_x, new_y = self.x + dx, self.y + dy
    #     if not game_map.is_walkable(new_x, new_y): return False
    #
    #     current_height = game_map.get_height(self.x, self.y)
    #     target_height = game_map.get_height(new_x, new_y)
    #
    #     # Check climb constraints (MAX_CLIMB_HEIGHT_DIFF from config)
    #     height_diff = target_height - current_height
    #     if height_diff > MAX_CLIMB_HEIGHT_DIFF: return False
    #
    #     self.x, self.y = new_x, new_y
    #     return True
    ```
    *   Checks `game_map.is_walkable()` and height difference constraints.
*   **Combat (`attack` method)**:
    *   Implements a basic "pistol_shot" ability: checks AP cost, range (Manhattan distance), then calls `target.take_damage(damage)`.
*   **AP Management**: `regenerate_ap()` restores AP to `max_ap` at the start of an entity's turn. `take_damage(amount)` reduces HP.

#### `GameMap` Class

Stores the static structure of the game world.

*   **Attributes**: `tiles` (2D list of chars), `heightmap` (2D list of ints), `width`, `height`.
*   **Methods**:
    *   `is_valid(x, y)`: Boundary check.
    *   `get_height(x, y)`: Returns height at coordinates.
    *   `get_tile(x,y)`: Returns tile character.
    *   `is_walkable(x, y)`: Checks tile character (e.g., `'#'` is a wall).

#### `GameEngine` Class

Orchestrates entities, turns, and game rules.

*   **Initialization**: Takes a `GameMap` instance. `entities` list, `player` reference, `turn_order`, `current_turn_index`, `game_state` string.
*   **Entity Setup (`initialize_entities_from_map_data`)**:
    ```python
    # Snippet from GameEngine.initialize_entities_from_map_data()
    # for entity_placement_info in entities_on_map_info:
    #     entity_id = entity_placement_info["id"]
    #     data = load_entity_data(entity_id) # From data_manager
    #     if data:
    #         entity = Entity(x=entity_placement_info["x"], y=entity_placement_info["y"],
    #                         char=data["char"], name=data["name"], hp=data["hp"], 
    #                         ap=data["ap"], abilities=data.get("abilities", []),
    #                         behavior=data.get("behavior"), entity_id=entity_id)
    #         self.entities.append(entity)
    #         if data.get("behavior") == "player_controlled" or entity_id == "player_char":
    #             self.player = entity
    ```
*   **Turn Management**:
    *   `_setup_turn_order()`: Populates `self.turn_order` (living entities), player usually first.
    *   `start_game()`: Calls `_setup_turn_order()`, sets initial `game_state` (e.g., "player_turn") and regenerates AP for the first entity.
    *   `next_turn()`: Filters dead entities from `turn_order`. Advances `current_turn_index`. Regenerates AP for the new active entity. Updates `game_state`. Checks for game over if no entities left or player dead.
*   **NPC AI (`run_npc_behavior`)**:
    *   If `npc.behavior == "move_towards_player"`: Calculates simple step (dx, dy) towards player. If in range of "pistol_shot" and has AP, calls `npc.attack()`. Otherwise, if AP available, calls `npc.move()`.
    *   If `npc.behavior == "run_away_from_player"`: Similar logic, but moves away.
*   **Player Actions (`handle_player_action`)**:
    *   Called by `Game` class. Validates it's player's turn.
    *   For "move": calls `self.player.move()`, deducts AP.
    *   For "attack": finds target entity at `target_pos`, calls `self.player.attack()`.
    *   If player runs out of AP, calls `self.end_player_turn()`.
*   **Game State (`get_current_game_state`, `update`)**:
    *   `update()`: If `game_state` is "npc_turn", calls `run_npc_behavior()` for current NPC then `next_turn()`. Checks for win/loss conditions.
    *   `get_current_game_state()`: Returns the current state string, re-evaluating win/loss.
*   **Utility Methods**: `get_valid_moves(entity)`, `get_attack_range(entity, ability_name)` provide data for UI highlighting.

### 11.5 `renderer.py` - Visual Output

Responsible for drawing everything to the screen using Pygame.

#### `Renderer` Class

*   **Initialization**: Takes Pygame `screen`, loads fonts, defines `tile_colors`, `entity_colors`, `highlight_colors` (often from `config.COLORS`).
*   **Entity Coloring (`_get_entity_color`)**: Returns a color based on `entity.behavior`.
*   **Main Drawing Method (`draw_game_state`)**:
    *   **Map Tiles**: Iterates `game_map.tiles` and `game_map.heightmap`.
        ```python
        # Snippet from Renderer.draw_game_state() - Map Tile Rendering
        # base_color = self.tile_colors.get(tile_char, default_color)
        # # Slightly adjust color by height for pseudo-3D effect
        # height_color_factor = max(0.7, min(1.3, 1 + (map_height - 2) * 0.1))
        # adjusted_color = tuple(min(255, int(c * height_color_factor)) for c in base_color)
        # pygame.draw.rect(self.screen, adjusted_color, tile_rect)
        # char_surface = self.font.render(tile_char, True, COLORS.get("text_light"))
        # self.screen.blit(char_surface, char_surface.get_rect(center=tile_rect.center))
        ```
    *   **Highlights**: If `action_mode` is "move" or "attack", draws semi-transparent rectangles on `highlighted_tiles_move` or `highlighted_tiles_attack`.
    *   **Entities**: Iterates `game_engine.entities`. Renders `entity.char` with color from `_get_entity_color()`. Applies a small visual Y-offset based on `game_map.get_height(entity.x, entity.y)`. Highlights `current_turn_entity` and `selected_entity`.

### 11.6 `ui.py` - User Interface Elements

Manages different UI screens (menus, game HUD).

#### `BaseInterface` Class

*   Common functionality: Loads various font sizes. Provides `draw_text` method for rendering text with options for color, position, and centering.

#### `MainMenu` Class (inherits `BaseInterface`)

*   **State**: `options` (list of menu item strings), `selected_option` (index).
*   **Input (`handle_input`)**: `K_UP`/`K_DOWN` change `selected_option`. `K_RETURN` on an option returns a new game state string (e.g., "map_selection", "editor") or posts `pygame.QUIT`.
*   **Drawing (`draw`)**: Fills background, draws title, iterates `self.options` to draw them, highlighting the `selected_option`.

#### `MapSelectionScreen` Class (inherits `BaseInterface`)

*   **State**: `available_maps` (list of map names from `data_manager`), `selected_map_index`.
*   **Input (`handle_input`)**: Similar to `MainMenu`. `K_RETURN` returns `("game", selected_map_name)`. `K_ESCAPE` returns to "main_menu".
*   **Drawing (`draw`)**: Displays title, lists `available_maps` (highlighting selected), or shows "No maps found".

#### `GameUI` Class (inherits `BaseInterface`)

*   **Drawing (`draw`)**:
    *   Renders a UI panel at the bottom.
    *   Displays player HP/AP, current turn entity's name.
    *   Shows recent `messages` (e.g., "Player moved").
    *   If `game_state` indicates game over, displays a large "GAME OVER" or "VICTORY!" message.
    ```python
    # Snippet from GameUI.draw() - Player Stats on Panel
    # panel_rect = pygame.Rect(0, screen_h - self.ui_panel_height, screen_w, self.ui_panel_height)
    # # ... draw panel background ...
    # if player:
    #     self.draw_text(f"HP: {player.hp}/{player.max_hp}", self.font_small, self.hp_color, ...)
    #     self.draw_text(f"AP: {player.ap}/{player.max_ap}", self.font_small, self.ap_color, ...)
    ```

#### `EditorUI` Class (inherits `BaseInterface`)

*   **State**: Similar to before, but now includes `dialog_state` for save/load dialogs.
*   **Drawing (`draw`)**:
    *   Renders the map grid and entities as in the previous version.
    *   Draws UI panels for tile selection, entity placement, and height adjustment.
    *   Displays messages or dialog boxes for actions like saving/loading.

### 11.7 `game.py` - Gameplay Orchestration

Manages the active game session, acting as a bridge between the `GameEngine`, `Renderer`, and `GameUI`.

#### `Game` Class

*   **State**: `is_running`, `_initialized`, `current_map_name`, `engine` (GameEngine instance), `renderer` (Renderer instance), `ui` (GameUI instance), `player` (ref to player Entity), `selected_entity`, `highlighted_tiles_move`, `highlighted_tiles_attack`, `action_mode`, `game_messages` (list of timed messages), `game_state` (mirrors engine's state mostly).
*   **Loading (`load_game_state`)**:
    *   Calls `data_manager.load_map_data(map_file_name)`.
    *   Creates `GameMap` from map data.
    *   Instantiates `self.engine = GameEngine(game_map_obj)`.
    *   Calls `self.engine.initialize_entities_from_map_data(...)`.
    *   Sets `self.player = self.engine.get_player()`.
    *   Instantiates `self.renderer` and `self.ui`.
    *   Calls `self.engine.start_game()` to begin turns and set initial engine game state.
    *   Sets `self.game_state` from `self.engine.get_current_game_state()`.
*   **Input Handling (`handle_input`)**:
    *   Processes Pygame events if `self.game_state == "player_turn"`.
    *   Example: `K_SPACE` to end turn calls `self.engine.end_player_turn()`, then updates `self.game_state`.
    *   (More complex player actions like selecting units, choosing move/attack targets would be handled here, updating `self.action_mode`, `self.selected_entity`, and then calling `self.engine.handle_player_action()` with appropriate arguments.)
*   **Updating (`update`)**:
    *   Manages `self.game_messages` display timers.
    *   Calls `self.engine.update()`. This is where NPC turns are processed if `self.engine.game_state == "npc_turn"`.
    *   Updates `self.game_state` from `self.engine.get_current_game_state()`.
*   **Drawing (`draw`)**:
    *   If not initialized or in an error state, shows a loading/error message.
    *   Otherwise, calls `self.renderer.draw_game_state(...)` with current game data.
    *   Calls `self.ui.draw(...)` to render the game interface.
*   **Messaging (`set_message`)**: Adds messages to `self.game_messages` with a display timer. `duration = -1` for persistent.

### 11.8 `editor.py` - Map Creation Tool

Provides an interface for users to design game maps.

#### `Editor` Class

*   **State**: `map_data` (dict: "name", "tiles", "heightmap", "entities_on_map"), `map_width`, `map_height`, `camera_offset_x/y`, `editing_mode` ("tiles", "heights", "entities", "select"), current selections for tile char/height/entity ID, dialog states (`show_save_dialog`, `save_filename_input`, etc.), `message` and `message_timer`.
*   **Initialization**: Sets up default empty map structure. Calls `load_entity_definitions()` which uses `data_manager` to get available entity types for placement.
*   **Input Handling (`handle_input`)**:
    *   **Mouse Clicks**: Modifies `self.map_data` based on `editing_mode` and mouse grid position (adjusted for camera).
        *   `tiles`: `self.map_data["tiles"][grid_y][grid_x] = selected_char`
        *   `heights`: `self.map_data["heightmap"][grid_y][grid_x] = selected_height`
        *   `entities`: Adds/updates entry in `self.map_data["entities_on_map"]`. Removes existing entity at the same spot before placing a new one. If placing a player start, ensures only one exists.
    *   **Keyboard**:
        *   Mode changes: T (tiles), H (heights), E (entities), X (erase/select).
        *   Selection changes (arrow keys): Cycle through `available_tile_chars`, `current_height_value`, `available_entity_ids`.
        *   Camera pan (arrow keys, if not changing selection).
        *   Ctrl+S/L/N: Trigger save/load dialogs or new map.
        *   R: Reload entity definitions.
    *   Dialog input (`handle_save_dialog_input`, `handle_load_dialog_input`): Manages text input for filenames and selection from a list for loading.
*   **Map Operations**:
    *   `new_map(width, height)`: Resets `self.map_data`.
    *   Save: (In `handle_save_dialog_input`) `data_manager.save_map_data(self.save_filename_input, self.map_data)`.
    *   Load: (In `handle_load_dialog_input`) `self.map_data = data_manager.load_map_data(selected_map_to_load)`. Ensures all necessary keys ("heightmap", "entities_on_map", "name") exist in loaded data.
*   **Drawing (`draw`)**:
    *   Draws the map grid: iterates `self.map_width`, `self.map_height`.
        *   For each cell: draws border, background color shaded by `height_val`, tile character, and height number. All positions adjusted by `self.camera_offset_x/y`.
    *   Calls `self.draw_entities_on_map()`: Renders entity characters from `self.map_data["entities_on_map"]` using their defined char and color (player vs. enemy).
    *   Draws UI text: current mode, selected tool/item, help text.
    *   Draws messages and modal dialogs (`draw_modal_dialog`, `draw_modal_dialog_multiline`).
    ```python
    # Snippet from Editor.draw() - Drawing a map cell with camera offset
    # rect = pygame.Rect(
    #     self.camera_offset_x + x_coord * EDITOR_TILE_SIZE,
    #     self.camera_offset_y + y_coord * EDITOR_TILE_SIZE,
    #     EDITOR_TILE_SIZE, EDITOR_TILE_SIZE
    # )
    # # ... drawing tile background, char, height number within this rect ...
    ```

### 11.9 `main.py` - Application Entry Point

Orchestrates the high-level game states (main menu, map selection, game, editor) and transitions between them.

*   **Main Loop**: Central `while running:` loop.
*   **State Management**: `current_state` string variable. `selected_map_for_game` stores map name chosen for play.
*   **Initialization**: Pygame, screen, clock. Instantiates `MainMenu`, `MapSelectionScreen`, `Game`, `Editor` objects once at the start.
*   **Event Handling**:
    *   Global `pygame.QUIT` event to set `running = False`.
    *   Global `K_ESCAPE` key: If in "game" or "editor" state, sets `current_state = "main_menu"`.
*   **State-Specific Logic (within the main loop)**:
    *   **"main_menu"**: Calls `main_menu.draw()`. Passes events to `main_menu.handle_input()`. If `handle_input` returns a new state, updates `current_state`. Performs setup for new state (e.g., `map_selection_screen.load_available_maps()`, `editor.load_entity_definitions()`).
    *   **"map_selection"**: Similar flow with `map_selection_screen`. If it returns `("game", map_name)`, stores `selected_map_for_game = map_name` and transitions.
    *   **"game"**:
        ```python
        # Snippet from main.py - Game state logic
        # if current_state == "game":
        #     if selected_map_for_game and not game.is_initialized():
        #         game.load_game_state(selected_map_for_game) # Load map data and init engine
        #
        #     if game.is_initialized():
        #         for event in events: game.handle_input(event) # Player input
        #         game.update() # Game logic, engine update (NPC turns)
        #         game.draw()   # Render game state
        #         if game.is_over(): # Check if game ended (win/loss/esc)
        #             current_state = "main_menu"
        #             selected_map_for_game = None 
        #             game.reset() # Clean up game state
        #     else:
        #         # Draw error message if game failed to initialize
        #         # ... (text rendering for error) ...
        ```
    *   **"editor"**: Passes events to `editor.handle_input()`, calls `editor.update()`, `editor.draw()`.
*   **Display Update**: `pygame.display.flip()` and `clock.tick(FPS)` at the end of each main loop iteration.

This concludes the programmatic deep dive into the main systems of the ASCII Tactical RPG.
