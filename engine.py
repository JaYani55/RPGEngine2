# Game Engine: Turn-based logic, combat, AI, height/climbing
from utils import manhattan_distance 
from config import MAX_CLIMB_HEIGHT_DIFFERENCE as MAX_CLIMB_HEIGHT_DIFF
from config import MAX_MAP_HEIGHT_LEVEL as MAX_MAP_HEIGHT
from data_manager import load_entity_data
from abilities import get_ability, Ability, TargetType # Added Ability, TargetType

# --- Constants ---
# MAX_CLIMB_HEIGHT_DIFF = 1 # Defined in config now
# MAX_MAP_HEIGHT = 5        # Defined in config now

class Entity:
    def __init__(self, x, y, char, name="Entity", hp=10, ap=3, max_hp=None, max_ap=None, abilities=None, behavior=None, description="", entity_id=None): # Added entity_id
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.hp = hp
        self.max_hp = max_hp if max_hp is not None else hp
        self.ap = ap
        self.max_ap = max_ap if max_ap is not None else ap
        # self.abilities = abilities if abilities else [] # Old: list of strings
        self.abilities: list[Ability] = [] # New: list of Ability objects
        if abilities: # abilities is a list of names from JSON
            for ability_name in abilities:
                ability_obj = get_ability(ability_name)
                if ability_obj:
                    self.abilities.append(ability_obj)
                else:
                    print(f"Warning: Entity '{name}' - ability '{ability_name}' not found in registry.")

        self.behavior = behavior # e.g., "player_controlled", "move_towards_player", "run_away_from_player"
        self.description = description
        self.entity_id = entity_id # Store the original ID from JSON
        self.is_alive = True # New property

    def get_ability_by_name(self, ability_name: str) -> Ability | None:
        for ability in self.abilities:
            if ability.name == ability_name:
                return ability
        return None

    def move(self, dx, dy, game_map):
        new_x, new_y = self.x + dx, self.y + dy

        if not game_map.is_walkable(new_x, new_y):
            # print(f"{self.name} cannot move to blocked tile ({new_x},{new_y})")
            return False

        current_height = game_map.get_height(self.x, self.y)
        target_height = game_map.get_height(new_x, new_y)

        if target_height > MAX_MAP_HEIGHT:
            # print(f"{self.name} cannot move to tile above max height ({new_x},{new_y})")
            return False

        height_diff = target_height - current_height
        if height_diff > MAX_CLIMB_HEIGHT_DIFF:
            # print(f"{self.name} cannot climb from {current_height} to {target_height} at ({new_x},{new_y})")
            return False
        # Can move down any height difference

        self.x = new_x
        self.y = new_y
        # print(f"{self.name} moved to ({self.x},{self.y}) height {target_height}")
        return True

    def take_damage(self, amount):
        if not self.is_alive: return # Already defeated

        self.hp -= amount
        # print(f"{self.name} took {amount} damage, HP is now {self.hp}") # Replaced by log message
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
            self.char = '%' # Change char on death
            # print(f"{self.name} has been defeated!") # Replaced by log message
            return True # Indicates defeat
        return False # Indicates still alive

    def attack(self, target: 'Entity', ability: Ability): # Changed: takes Ability object
        if not self.is_alive: return False, f"{self.name} is defeated and cannot attack."
        if not ability:
            # print(f"{self.name} has no ability to attack with.")
            return False, "No ability specified for attack."

        if ability.target_type not in [TargetType.ENEMY, TargetType.ANY_ENTITY]:
            # print(f"{self.name} cannot use {ability.name} on an entity target like that.")
            return False, f"{ability.name} cannot target entities."

        if self.ap < ability.ap_cost:
            # print(f"{self.name} does not have enough AP to use '{ability.name}' (needs {ability.ap_cost}, has {self.ap}).")
            return False, f"Not enough AP for {ability.name}."

        distance = manhattan_distance((self.x, self.y), (target.x, target.y))
        if distance > ability.range:
            # print(f"{self.name} cannot use {ability.name} on {target.name}: out of range (distance {distance}, range {ability.range}).")
            return False, f"{target.name} is out of range for {ability.name}."
        
        if not target.is_alive:
            return False, f"{target.name} is already defeated."

        self.ap -= ability.ap_cost
        damage = ability.damage_amount
        # print(f"{self.name} uses {ability.name} on {target.name} for {damage} {ability.damage_type} damage!") # Replaced by log
        defeated = target.take_damage(damage)
        message = f"{self.name} used {ability.name} on {target.name} for {damage} {ability.damage_type} damage."
        if defeated:
            message += f" {target.name} was defeated!"
        else:
            message += f" {target.name} HP is now {target.hp}."
        return True, message

    def regenerate_ap(self):
        self.ap = self.max_ap # Full AP regeneration at start of turn for simplicity


class GameMap:
    def __init__(self, tiles, heightmap):
        self.tiles = tiles # 2D list of ASCII characters
        self.heightmap = heightmap # 2D list of integers
        self.width = len(tiles[0]) if tiles else 0
        self.height = len(tiles) if tiles else 0

    def is_valid(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get_height(self, x, y):
        if self.is_valid(x, y):
            return self.heightmap[y][x]
        return float('inf') # Impassable if out of bounds

    def get_tile(self, x, y):
        if self.is_valid(x, y):
            return self.tiles[y][x]
        return None # Or some 'out of bounds' tile character

    def is_walkable(self, x, y):
        if not self.is_valid(x, y):
            return False
        # Example: '#' is a wall, others are walkable. Add more non-walkable tiles as needed.
        return self.tiles[y][x] != '#'


class GameEngine:
    def __init__(self, game_map_instance): # Changed: takes a GameMap instance
        self.game_map = game_map_instance # Use the passed GameMap instance
        self.entities: list[Entity] = [] # Type hint for clarity
        self.player: Entity | None = None # Type hint
        self.turn_order: list[Entity] = [] # Type hint
        self.current_turn_index = 0
        self.game_state = "initializing" # e.g., player_turn, npc_turn, game_over_player_win, game_over_player_lose
        self.game_log = [] # New: For storing game event messages
        self.MAX_LOG_MESSAGES = 20 # Max messages in the log

    def add_log_message(self, message: str):
        self.game_log.append(message)
        if len(self.game_log) > self.MAX_LOG_MESSAGES:
            self.game_log.pop(0)
        print(f"LOG: {message}") # Also print to console for debugging

    def initialize_entities_from_map_data(self, entities_on_map_info):
        """
        Initializes entities based on their definitions and placement in map data.
        `entities_on_map_info` is a list of dicts like: {"id": "player_char", "x": 1, "y": 1}
        Entity definitions are loaded from JSON files using `load_entity_data`.
        """
        self.entities = []
        self.player = None
        
        if not entities_on_map_info:
            print("Warning: No entities specified in map data.")
            # Potentially set game state to an error or handle as empty map
            self.game_state = "error_no_entities_in_map"
            return

        for entity_placement_info in entities_on_map_info:
            entity_id = entity_placement_info["id"]
            # Ensure .json is not appended if already present in entity_id
            if entity_id.endswith(".json"):
                entity_def_file = entity_id
            else:
                entity_def_file = f"{entity_id}.json"
            
            data = load_entity_data(entity_def_file) # From data_manager
            
            if data:
                # Abilities are now loaded by the Entity class constructor
                entity = Entity(
                    x=entity_placement_info["x"], y=entity_placement_info["y"],
                    char=data["char"], name=data["name"],
                    hp=data["hp"], max_hp=data.get("max_hp", data["hp"]),
                    ap=data["ap"], max_ap=data.get("max_ap", data["ap"]),
                    abilities=data.get("abilities", []), # Pass ability names
                    behavior=data.get("behavior"),
                    description=data.get("description", ""),
                    entity_id=entity_id # Store the ID
                )
                self.entities.append(entity)
                if data.get("behavior") == "player_controlled" or entity_id == "player_char": # Common ways to ID player
                    if self.player:
                        print(f"Warning: Multiple player-controlled entities found. Using the first one: {self.player.name}")
                    else:
                        self.player = entity
            else:
                print(f"Warning: Entity definition for '{entity_id}' (file: {entity_def_file}) not found or failed to load.")

        if not self.player and self.entities:
            print(f"Warning: No player_controlled entity found. Defaulting to first entity '{self.entities[0].name}' as player.")
            self.player = self.entities[0]
            # It might be better to error out if no player is explicitly defined and required
        elif not self.entities:
            print("Error: No entities were loaded into the engine.")
            self.game_state = "error_no_entities_loaded"
            return # Critical error, cannot proceed

        # Initialize turn order after all entities are loaded
        self._setup_turn_order()
        # self.game_state = "player_turn" # Set by start_game()

    def _setup_turn_order(self):
        self.turn_order = [e for e in self.entities if e.is_alive] # Use is_alive
        # Ensure player is first in turn order if they exist and are alive
        if self.player and self.player.is_alive:
            if self.player in self.turn_order:
                self.turn_order.remove(self.player)
            self.turn_order.insert(0, self.player)
        
        self.current_turn_index = 0
        if self.turn_order:
            current_entity = self.get_current_turn_entity()
            if current_entity:
                 current_entity.regenerate_ap()
        else:
            # This could mean all entities are dead or no entities to begin with
            print("Setup Turn Order: No entities available for turn order.")
            # Game state should reflect this, e.g., if player is dead -> game over
            if self.player and not self.player.is_alive:
                self.game_state = "game_over_player_lose"
            elif not self.player and not self.entities: # No player, no entities
                 self.game_state = "error_no_entities_loaded" # Or some other appropriate state
            # If player exists but all NPCs are dead, could be win condition
            elif self.player and self.player.is_alive and not any(e for e in self.entities if e != self.player and e.is_alive and e.behavior != "player_controlled"):
                self.game_state = "game_over_player_win"


    def start_game(self):
        """Called once after entities are loaded to set initial game state and first turn."""
        if not self.entities:
            print("Engine: Cannot start game, no entities loaded.")
            self.game_state = "error_no_entities_loaded"
            return

        self._setup_turn_order() # Recalculate turn order with current entity states

        if not self.turn_order:
            print("Engine: No entities in turn order. Game cannot start.")
            # Determine if this is a win/loss or an error
            if self.player and not self.player.is_alive:
                self.game_state = "game_over_player_lose"
            elif self.player and self.player.is_alive and not any(e for e in self.entities if e != self.player and e.is_alive and e.behavior != "player_controlled"):
                 self.game_state = "game_over_player_win"
            else: # No player, or other strange state
                 self.game_state = "error_engine_start"
            return

        first_entity = self.get_current_turn_entity()
        if first_entity:
            first_entity.regenerate_ap() # Ensure first entity has AP
            if first_entity == self.player:
                self.game_state = "player_turn"
                self.add_log_message(f"--- {self.player.name}'s Turn (AP: {self.player.ap}) ---")
            else:
                self.game_state = "npc_turn"
                self.add_log_message(f"--- {first_entity.name}'s Turn (AP: {first_entity.ap}) ---")
        else:
            # Should not happen if turn_order is populated
            self.add_log_message("Engine Start: Critical error, no entity for the first turn.")


    def get_current_turn_entity(self): # Renamed from get_current_entity
        if not self.turn_order or self.current_turn_index >= len(self.turn_order):
            return None
        return self.turn_order[self.current_turn_index]

    def next_turn(self):
        # Filter out dead entities before advancing turn
        self.turn_order = [e for e in self.turn_order if e.is_alive]
        
        if not self.turn_order:
            self.add_log_message("No entities left alive in turn order.")
            # Game over logic: check if player is alive
            if self.player and not self.player.is_alive:
                if self.game_state != "game_over_player_lose": self.add_log_message("Player has been defeated! Game Over.")
                self.game_state = "game_over_player_lose"
            elif self.player and self.player.is_alive and not any(e for e in self.entities if e != self.player and e.is_alive and e.behavior != "player_controlled"): # Player alive, no NPCs left
                if self.game_state != "game_over_player_win": self.add_log_message("All enemies defeated! Victory!")
                self.game_state = "game_over_player_win"
            else: # No player, or other unhandled game over scenario
                self.game_state = "game_over_unknown" # Or some error state
            return

        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        current_entity = self.get_current_turn_entity()
        
        if current_entity:
            current_entity.regenerate_ap()
            if current_entity == self.player:
                self.game_state = "player_turn"
                self.add_log_message(f"--- {self.player.name}'s Turn (AP: {self.player.ap}) ---")
            else:
                self.game_state = "npc_turn"
                self.add_log_message(f"--- {current_entity.name}'s Turn (AP: {current_entity.ap}) ---")
        else:
            # This case should ideally be caught by the `if not self.turn_order:` above
            self.add_log_message("Next Turn: Error - No current entity after turn advance.")


    def run_npc_behavior(self, npc: Entity):
        if not self.player or not self.player.is_alive: return 
        if npc.ap == 0 or not npc.is_alive: return 

        # Try to use an attack ability if player is in range
        attack_ability_to_use = None
        for ability in npc.abilities:
            if ability.target_type == TargetType.ENEMY and npc.ap >= ability.ap_cost:
                distance_to_player = manhattan_distance((npc.x, npc.y), (self.player.x, self.player.y))
                if distance_to_player <= ability.range:
                    attack_ability_to_use = ability
                    break
        
        if attack_ability_to_use:
            # print(f"NPC {npc.name} attempting to use {attack_ability_to_use.name} on player.")
            success, message = npc.attack(self.player, attack_ability_to_use)
            self.add_log_message(message) # Log NPC attack message
            if not self.player.is_alive and self.game_state != "game_over_player_lose":
                self.game_state = "game_over_player_lose"
                self.add_log_message("Player has been defeated! Game Over.")
            if npc.ap == 0 or not npc.is_alive: return

        # If no attack was made or possible, or if AP remains, try to move
        if npc.ap > 0:
            move_ability = npc.get_ability_by_name("Move") # NPCs need "Move" ability to move
            if move_ability and npc.ap >= move_ability.ap_cost:
                distance_to_player = manhattan_distance((npc.x, npc.y), (self.player.x, self.player.y)) # Recalculate, AP might have changed

                if npc.behavior == "move_towards_player":
                    if distance_to_player > 1: # Don't move if adjacent
                        dx, dy = 0, 0
                        if npc.x < self.player.x: dx = 1
                        elif npc.x > self.player.x: dx = -1
                        if npc.y < self.player.y: dy = 1
                        elif npc.y > self.player.y: dy = -1

                        moved_in_x = False
                        if dx != 0:
                            # Check if the path is clear before attempting to move
                            potential_x, potential_y = npc.x + dx, npc.y
                            if not self.get_entities_at(potential_x, potential_y): # Check if tile is occupied
                                if npc.move(dx, 0, self.game_map):
                                    npc.ap -= move_ability.ap_cost # Use move ability's AP cost
                                    moved_in_x = True
                                    self.add_log_message(f"{npc.name} moved towards player.")
                                    # print(f"NPC {npc.name} moved towards player (X axis). AP left: {npc.ap}")
                                    if npc.ap < move_ability.ap_cost or not npc.is_alive: return # Check if can move again
                        
                        if dy != 0 and not moved_in_x and npc.ap >= move_ability.ap_cost: 
                            potential_x, potential_y = npc.x, npc.y + dy
                            if not self.get_entities_at(potential_x, potential_y):
                                if npc.move(0, dy, self.game_map):
                                    npc.ap -= move_ability.ap_cost
                                    self.add_log_message(f"{npc.name} moved towards player.")
                                    # print(f"NPC {npc.name} moved towards player (Y axis). AP left: {npc.ap}")
                                    if npc.ap < move_ability.ap_cost or not npc.is_alive: return
                        # Diagonal move logic might be complex if only 1 AP per step is desired.
                        # Current logic: tries X, then Y if X failed or wasn't tried

                elif npc.behavior == "run_away_from_player":
                    # Simplified: only run if somewhat close
                    if distance_to_player < 8 : 
                        dx, dy = 0, 0
                        # Determine direction away from player
                        if npc.x < self.player.x: dx = -1 
                        elif npc.x > self.player.x: dx = 1
                        else: # If same column, try to move horizontally if possible
                            dx = 1 if self.game_map.is_walkable(npc.x + 1, npc.y) and not self.get_entities_at(npc.x + 1, npc.y) else -1
                        
                        if npc.y < self.player.y: dy = -1 
                        elif npc.y > self.player.y: dy = 1
                        else: # If same row, try to move vertically
                            dy = 1 if self.game_map.is_walkable(npc.x, npc.y + 1) and not self.get_entities_at(npc.x, npc.y+1) else -1

                        moved = False
                        # Try moving away on X axis
                        potential_x, potential_y = npc.x + dx, npc.y
                        if dx != 0 and not self.get_entities_at(potential_x, potential_y) and npc.move(dx, 0, self.game_map):
                            npc.ap -= move_ability.ap_cost
                            moved = True
                            self.add_log_message(f"{npc.name} ran away from player.")
                            # print(f"NPC {npc.name} ran away (X axis). AP left: {npc.ap}")
                            if npc.ap < move_ability.ap_cost or not npc.is_alive: return 
                        
                        # Try moving away on Y axis if X failed or not tried, and AP remains
                        if dy != 0 and npc.ap >= move_ability.ap_cost and not moved: 
                            potential_x, potential_y = npc.x, npc.y + dy
                            if not self.get_entities_at(potential_x, potential_y) and npc.move(0, dy, self.game_map):
                                npc.ap -= move_ability.ap_cost
                                self.add_log_message(f"{npc.name} ran away from player.")
                                # print(f"NPC {npc.name} ran away (Y axis). AP left: {npc.ap}")
                                if npc.ap < move_ability.ap_cost or not npc.is_alive: return
        
        # print(f"NPC {npc.name} ends its turn with {npc.ap} AP.")

    def update(self): # Renamed from update_round
        """Main update loop for the engine, called each frame by Game class."""
        if self.game_state in ["game_over_player_win", "game_over_player_lose", "error_no_entities_loaded", "critical_error_next_turn"]:
            return # Game is over or in a critical error state

        current_entity = self.get_current_turn_entity()
        if not current_entity:
            self.add_log_message("Engine Update: No current entity. Advancing turn to check state.")
            # This might happen if all entities die simultaneously or due to an error.
            # Re-evaluate game over conditions.
            self.next_turn() # This will re-evaluate and set game_state if all dead.
            return

        if not current_entity.is_alive: # Use is_alive
            self.add_log_message(f"Engine Update: {current_entity.name} is defeated. Advancing turn.")
            self.next_turn()
            return

        if self.game_state == "npc_turn":
            if current_entity != self.player: # Should always be true for npc_turn state
                # print(f"NPC ({current_entity.name}) taking turn. Initial AP: {current_entity.ap}")
                self.run_npc_behavior(current_entity)
                self.next_turn() 
            else:
                # This is an inconsistent state, player's turn but engine thinks it's NPC turn.
                print(f"Warning: Game state is 'npc_turn' but current entity is Player. Switching to player_turn.")
                self.game_state = "player_turn"
        
        # Player turn is handled by Game class via handle_player_action,
        # which then calls engine.next_turn() or engine.end_player_turn().
        # Check for game over conditions again after actions might have occurred.
        if self.player and not self.player.is_alive and self.game_state != "game_over_player_lose":
            self.add_log_message("Player has been defeated! Game Over.")
            self.game_state = "game_over_player_lose"
        elif self.player and self.player.is_alive and not any(e for e in self.entities if e != self.player and e.is_alive and e.behavior != "player_controlled") and self.game_state != "game_over_player_win":
            self.add_log_message("All enemies defeated! Victory!")
            self.game_state = "game_over_player_win"


    def get_entities_at(self, x, y):
        return [e for e in self.entities if e.x == x and e.y == y and e.is_alive] # Use is_alive

    def handle_player_action(self, action_type: str, target_pos=None, ability_to_use: Ability | None = None): # Changed ability_name to ability_to_use: Ability
        if not self.player or self.get_current_turn_entity() != self.player or self.game_state != "player_turn":
            # self.add_log_message("Not player's turn or invalid state for action.") # Avoid flooding log for simple misclicks
            return False, "Not player's turn or invalid state."
        
        if not self.player.is_alive: 
            self.add_log_message("Player is defeated and cannot take actions.")
            return False, "Player is defeated."

        action_taken = False
        message = ""

        if action_type == "move":
            move_ability = self.player.get_ability_by_name("Move")
            if not move_ability:
                return False, "Player does not have the 'Move' ability."

            if self.player.ap >= move_ability.ap_cost: 
                dx, dy = target_pos[0] - self.player.x, target_pos[1] - self.player.y
                if abs(dx) + abs(dy) == 1: # Manhattan distance of 1
                    if self.player.move(dx, dy, self.game_map):
                        self.player.ap -= move_ability.ap_cost 
                        action_taken = True
                        message = f"{self.player.name} moved to ({target_pos[0]},{target_pos[1]})."
                    else:
                        message = "Invalid move target or path blocked."
                else:
                    message = "Move target is not adjacent." 
            else:
                message = f"Player has not enough AP to move (needs {move_ability.ap_cost})."

        elif action_type == "ability": 
            if target_pos and ability_to_use:
                if self.player.ap < ability_to_use.ap_cost:
                    return False, f"Not enough AP for {ability_to_use.name} (needs {ability_to_use.ap_cost})."

                if ability_to_use.target_type == TargetType.TILE:
                    if ability_to_use.name == "Move": 
                         message = "'Move' ability should be handled via 'move' action type."
                         action_taken = False
                    else:
                        self.player.ap -= ability_to_use.ap_cost
                        action_taken = True
                        message = f"{self.player.name} used {ability_to_use.name} on tile {target_pos}."
                
                elif ability_to_use.target_type in [TargetType.ENEMY, TargetType.ALLY, TargetType.ANY_ENTITY]:
                    targets_at_pos = self.get_entities_at(target_pos[0], target_pos[1])
                    target_entity = None
                    if ability_to_use.target_type == TargetType.ENEMY:
                        target_entity = next((t for t in targets_at_pos if t != self.player), None) 
                    elif ability_to_use.target_type == TargetType.ALLY:
                         target_entity = next((t for t in targets_at_pos if t == self.player), None) 
                         # TODO: Add proper faction check for allies
                    elif ability_to_use.target_type == TargetType.ANY_ENTITY:
                        target_entity = next((t for t in targets_at_pos), None)

                    if target_entity:
                        if ability_to_use.damage_amount > 0 :
                            success, attack_message = self.player.attack(target_entity, ability_to_use)
                            if success:
                                action_taken = True
                                message = attack_message # Already contains defeat info if applicable
                                # if not target_entity.is_alive: # Redundant, attack message handles this
                                #     message += f" {target_entity.name} defeated!"
                                
                                # Check for win condition immediately after a kill by player
                                if not any(e for e in self.entities if e != self.player and e.is_alive and e.behavior != "player_controlled"):
                                    if self.game_state != "game_over_player_win": self.add_log_message("All enemies defeated! Victory!")
                                    self.game_state = "game_over_player_win"
                                elif not self.player.is_alive: # Check if player died (e.g. reflect damage, though not implemented)
                                     if self.game_state != "game_over_player_lose": self.add_log_message("Player has been defeated! Game Over.")
                                     self.game_state = "game_over_player_lose"
                        else:
                            self.player.ap -= ability_to_use.ap_cost
                            action_taken = True
                            message = f"{self.player.name} used {ability_to_use.name} on {target_entity.name}."
                    else:
                        message = f"No valid target for {ability_to_use.name} at that position."
                
                elif ability_to_use.target_type == TargetType.SELF:
                    self.player.ap -= ability_to_use.ap_cost
                    action_taken = True
                    message = f"{self.player.name} used {ability_to_use.name} on self."
                else:
                    message = f"Unsupported target type for {ability_to_use.name}."
            else:
                message = "Ability action requires target position and ability object."
        
        if action_taken:
            self.add_log_message(message) # Log successful player action message
            if self.player.ap == 0 and self.game_state == "player_turn" and self.player.is_alive:
                self.add_log_message(f"{self.player.name} is out of AP. Ending turn.")
                self.end_player_turn()
            return True, message
        
        return False, message
        
    def end_player_turn(self):
        if self.game_state == "player_turn":
            if self.player and self.player.is_alive:
                 self.add_log_message(f"{self.player.name} ends turn.")
            self.next_turn()
        else:
            print("Warning: Tried to end player turn when it wasn't player's turn.")


    def get_valid_moves(self, entity):
        # ... existing code ...
        if not entity or entity.ap < 1: 
            return []
        
        possible_moves = []
        # Check N, S, E, W tiles
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]: # Cardinal
        # for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1,-1), (-1,1), (1,-1), (1,1)]: # Cardinal + Diagonal
            nx, ny = entity.x + dx, entity.y + dy
            if self.game_map.is_walkable(nx, ny):
                current_height = self.game_map.get_height(entity.x, entity.y)
                target_height = self.game_map.get_height(nx, ny)
                if target_height <= MAX_MAP_HEIGHT and (target_height - current_height) <= MAX_CLIMB_HEIGHT_DIFF:
                    # Check if tile is occupied by another ALIVE entity
                    is_occupied = False
                    for e_other in self.entities:
                        if e_other.is_alive and e_other.x == nx and e_other.y == ny:
                            is_occupied = True
                            break
                    if not is_occupied:
                        possible_moves.append((nx, ny))
        return possible_moves

    def get_ability_range_tiles(self, entity: Entity, ability: Ability) -> list[tuple[int,int]]:
        """Gets all tiles within an ability's range for a given entity."""
        if not entity or not ability or entity.ap < ability.ap_cost:
            return []

        range_val = ability.range
        in_range_tiles = []

        # If target type is SELF, range is usually 0 or 1 (affecting only self tile)
        if ability.target_type == TargetType.SELF:
            # For self-target, often the "range" means it just applies to the entity's current tile.
            # If it has an effect_radius > 0, it might emanate from self.
            # For simplicity, if range is 0 or 1 for SELF, it's just the entity's tile.
            # If actual range highlighting is needed for self-centered AoE, this needs adjustment.
            if ability.effect_radius == 0: # Single target self
                 return [(entity.x, entity.y)] # Or empty if it doesn't highlight
            else: # Self-centered AoE
                # Calculate AoE tiles around entity based on effect_radius
                for r_x in range(-ability.effect_radius, ability.effect_radius + 1):
                    for r_y in range(-ability.effect_radius, ability.effect_radius + 1):
                        # Optional: use effect_radius as Manhattan or Chebyshev distance for shape
                        # if abs(r_x) + abs(r_y) > ability.effect_radius: continue # Manhattan shape
                        tile_x, tile_y = entity.x + r_x, entity.y + r_y
                        if self.game_map.is_valid(tile_x, tile_y):
                            in_range_tiles.append((tile_x, tile_y))
                return list(set(in_range_tiles)) # Remove duplicates

        # For other target types, calculate based on ability.range
        for y_coord in range(self.game_map.height):
            for x_coord in range(self.game_map.width):
                # Do not include the entity's own tile for most targeted abilities unless explicitly allowed
                # (e.g. an AoE centered on self but can hit others, or a point-blank AoE)
                # Current Pistol Shot example should not target self tile.
                if ability.target_type != TargetType.TILE and (x_coord, y_coord) == (entity.x, entity.y) and ability.effect_radius == 0:
                    continue
                
                dist = manhattan_distance((entity.x, entity.y), (x_coord, y_coord))
                if dist <= range_val:
                    # TODO: Add Line of Sight check here if necessary for the ability
                    # For now, all tiles in range are considered valid targets.
                    in_range_tiles.append((x_coord, y_coord))
        
        # If the ability has an Area of Effect (AoE) centered on the target tile:
        # The `in_range_tiles` currently are potential *centers* of an AoE.
        # The actual highlighted area would be these tiles + their AoE if effect_radius > 0.
        # This function is for "where can I click to START the ability".
        # The renderer will need to know the effect_radius if it's to draw the AoE preview.
        return list(set(in_range_tiles)) # Remove duplicates

    # Old get_attack_range - to be replaced or refactored by get_ability_range_tiles
    # def get_attack_range(self, entity, ability_name): # Changed: takes ability_name
    #     # ... (previous implementation) ...


    def get_player(self) -> Entity | None: # Type hint
        return self.player

    def get_current_game_state(self) -> str: # Type hint
        return self.game_state


# Remove the __main__ example block as it's for testing and not part of the library code.
# if __name__ == '__main__':
#     ... (old example code) ...
