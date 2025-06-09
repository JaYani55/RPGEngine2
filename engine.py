# Game Engine: Turn-based logic, combat, AI, height/climbing
from utils import manhattan_distance 
from config import MAX_CLIMB_HEIGHT_DIFFERENCE as MAX_CLIMB_HEIGHT_DIFF
from config import MAX_MAP_HEIGHT_LEVEL as MAX_MAP_HEIGHT
from data_manager import load_entity_data, list_available_ability_ids
from abilities import get_ability, Ability, TargetType
from ai import Behavior, create_behavior  # Import AI behavior system
import collections
import asyncio # Add asyncio import

class GameMap:
    def __init__(self, tiles, heightmap):
        self.tiles = tiles
        self.width = len(tiles[0]) if tiles and len(tiles) > 0 else 0
        self.height = len(tiles) if tiles else 0
        self.heightmap = heightmap
        # Define walkable characters. This could also come from config or map properties.
        self.walkable_chars = [".", "+", ","] # Example: floor, open door, grass

    def is_valid(self, x, y):
        """Check if the coordinates are within map boundaries."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile_char(self, x, y):
        """Get the character of the tile at (x,y)."""
        if self.is_valid(x, y):
            return self.tiles[y][x]
        return None

    def is_walkable(self, x, y):
        """Check if a tile is walkable (within bounds and not a blocking tile type)."""
        if not self.is_valid(x, y):
            return False
        tile_char = self.tiles[y][x]
        return tile_char in self.walkable_chars

    def get_height(self, x, y):
        """Get the height of the tile at (x,y)."""
        if self.is_valid(x, y) and self.heightmap and \
           y < len(self.heightmap) and x < len(self.heightmap[y]):
            return self.heightmap[y][x]
        return 0 # Default height if out of bounds or no heightmap data


class Entity:
    def __init__(self, id, name, x, y, char, color, hp, ap, defense, 
                 abilities_ids=None, faction="neutral", sight_radius=5, 
                 max_hp=None, behavior: Behavior | None = None):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.hp = hp
        self.max_hp = max_hp if max_hp is not None else hp
        self.ap = ap # max_ap
        self.current_ap = ap # current AP for turn-based consumption
        self.defense = defense
        self.abilities_ids = abilities_ids if abilities_ids is not None else []
        self.abilities: list[Ability] = []
        self.faction = faction
        self.sight_radius = sight_radius
        self.is_dead = False
        self.status_effects = []
        self.behavior = behavior  # AI behavior strategy

    def get_ability_by_id_name(self, ability_id_name: str) -> Ability | None:
        for ability in self.abilities:
            if ability.id_name == ability_id_name:
                return ability
        return None

    def move(self, dx, dy, game_map):
        new_x, new_y = self.x + dx, self.y + dy

        if not game_map.is_walkable(new_x, new_y):
            return False

        current_height = game_map.get_height(self.x, self.y)
        target_height = game_map.get_height(new_x, new_y)

        if target_height > MAX_MAP_HEIGHT:
            return False

        height_diff = target_height - current_height
        if height_diff > MAX_CLIMB_HEIGHT_DIFF:
            return False

        self.x = new_x
        self.y = new_y
        return True

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_dead = True
            self.char = '%'
            self.color = (128, 128, 128)
            return f"{self.name} dies."
        return f"{self.name} takes {amount} damage."

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        return f"{self.name} heals for {amount} HP."

    def restore_ap(self, amount):
        self.current_ap = min(self.ap, self.current_ap + amount)


class GameEngine:
    # Class constants
    MAX_LOG_MESSAGES = 20
    
    def __init__(self, game_map: GameMap):        
        self.game_map = game_map
        self.entities: list[Entity] = []
        self.player: Entity | None = None
        self.current_turn_index = 0
        self.turn_order: list[Entity] = []
        self.game_state = "loading"
        self.game_log: list[dict] = []
        self.current_game_turn = 0

    def add_log_message(self, message: str):
        if len(self.game_log) >= self.MAX_LOG_MESSAGES:
            self.game_log.pop(0)
        self.game_log.append({'message': message, 'turn': self.current_game_turn})
        print(f"ENGINE_LOG (Turn {self.current_game_turn}): {message}")

    def _start_entity_turn(self, entity: Entity):
        """Resets AP for the entity whose turn is starting and sets game state."""
        entity.current_ap = entity.ap
        self.add_log_message(f"{entity.name}'s turn begins (AP: {entity.current_ap}).")
        if entity == self.player:
            self.game_state = "player_turn"
        else:
            self.game_state = "npc_turn"

    def initialize_entities_from_map_data(self, entities_data: list[dict]):
        self.entities.clear()
        for map_entity_data in entities_data:
            entity_id = map_entity_data.get("id")
            if not entity_id:
                print(f"Warning: Entity data missing 'id', skipping: {map_entity_data.get('name', 'Unknown')}")
                continue

            # Load full entity definition from entity files
            entity_definition = load_entity_data(entity_id)
            if not entity_definition:
                print(f"Warning: Could not load entity definition for '{entity_id}', skipping.")
                self.add_log_message(f"Warning: Entity definition '{entity_id}' not found.")
                continue

            # Merge map position data with entity definition data
            merged_data = entity_definition.copy()
            merged_data.update({
                "x": map_entity_data.get("x", 0),
                "y": map_entity_data.get("y", 0),
                "is_player_start": map_entity_data.get("is_player_start", False)
            })

            # Resolve abilities from IDs
            resolved_abilities = []
            ability_ids = merged_data.get("abilities", [])
            if ability_ids:
                for ab_id in ability_ids:
                    ability = get_ability(ab_id)
                    if ability:
                        resolved_abilities.append(ability)
                    else:
                        self.add_log_message(f"Warning: Ability ID '{ab_id}' not found for entity '{entity_id}'.")
            
            # Create behavior from behavior name
            behavior_name = merged_data.get("behavior", "aggressive_melee")
            entity_behavior = create_behavior(behavior_name)
            
            try:
                entity = Entity(
                    id=entity_id,
                    name=merged_data.get("name", "Unnamed Entity"),
                    x=merged_data.get("x", 0),
                    y=merged_data.get("y", 0),
                    char=merged_data.get("char", "?"),
                    color=merged_data.get("color", (200, 200, 200)),
                    hp=merged_data.get("hp", 10),
                    max_hp=merged_data.get("max_hp"),
                    ap=merged_data.get("ap", 3),
                    defense=merged_data.get("defense", 0),
                    abilities_ids=ability_ids,
                    faction=merged_data.get("faction", "neutral"),
                    sight_radius=merged_data.get("sight_radius", 5),
                    behavior=entity_behavior
                )
                entity.abilities = resolved_abilities

                self.entities.append(entity)
                if merged_data.get("is_player_start", False):
                    self.player = entity
                    entity.faction = "player"
                    entity.behavior = None  # Player doesn't need AI behavior
                    self.add_log_message(f"Player entity '{entity.name}' initialized.")
            except (TypeError, Exception) as e:
                self.add_log_message(f"Error creating entity '{entity_id}': {e}")
                print(f"Error creating entity '{entity_id}': {e}")

        if not self.player and self.entities:
            self.add_log_message("Warning: No entity explicitly marked as 'is_player_start' in map data.")
        
        self._setup_turn_order()
        self.add_log_message(f"Entities initialized. Count: {len(self.entities)}. Player: {self.player.name if self.player else 'None'}")

    def get_player(self) -> Entity | None:
        """Returns the player entity."""
        return self.player

    def find_player_index(self) -> int:
        """Finds the index of the player in the current turn order."""
        if not self.player or not self.turn_order:
            return -1
        try:
            return self.turn_order.index(self.player)
        except ValueError:
            return -1

    def _setup_turn_order(self):
        self.turn_order = [e for e in self.entities if not e.is_dead]
        # Ensure player is first if present
        if self.player and self.player in self.turn_order:
            self.turn_order.remove(self.player)
            self.turn_order.insert(0, self.player)
        self.current_turn_index = 0
        if not self.turn_order:
            self.add_log_message("Warning: Turn order is empty after setup.")
            self.game_state = "game_over_player_lose"
        else:
            self.add_log_message(f"Turn order set: {[e.name for e in self.turn_order]}")

    def start_game(self):
        if not self.turn_order:
            self.add_log_message("Cannot start game: No entities in turn order.")
            self.game_state = "no_entities"
            return

        player_idx = self.find_player_index()

        if player_idx != -1:
            self.current_turn_index = player_idx
            self._start_entity_turn(self.turn_order[self.current_turn_index])
        elif self.turn_order:
            self.current_turn_index = 0
            self._start_entity_turn(self.turn_order[self.current_turn_index])
        else:
            self.add_log_message("Cannot start game: Turn order became empty unexpectedly.")
            self.game_state = "no_entities"
            return
            
        self.add_log_message("Game started.")

    def get_current_turn_entity(self) -> Entity | None:
        """Returns the entity whose current turn it is."""
        if not self.turn_order or self.current_turn_index < 0 or self.current_turn_index >= len(self.turn_order):
            return None
        return self.turn_order[self.current_turn_index]

    def check_game_over_conditions(self):
        """Check if the game should end and set the appropriate game state."""
        if self.player and self.player.is_dead:
            self.game_state = "game_over_player_lose"
            self.add_log_message(f"Game Over: {self.player.name} has been defeated.")
            return
        
        if self.player and not self.player.is_dead:
            non_player_entities_alive = any(e for e in self.entities if not e.is_dead and e != self.player and e.faction != "player")
            if not non_player_entities_alive:
                self.game_state = "game_over_player_win"
                self.add_log_message(f"Game Over: {self.player.name} is victorious!")
                return

    def next_turn(self):
        if not self.turn_order:
            self.add_log_message("Attempted next_turn with empty turn order.")
            if self.player and self.player.is_dead:
                self.game_state = "game_over_player_lose"
            else:
                self.game_state = "game_over_player_win"
            return

        current_entity = self.get_current_turn_entity()
        if current_entity:
            self.add_log_message(f"Ending turn for {current_entity.name}.")

        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        next_entity = self.turn_order[self.current_turn_index]

        # Skip dead entities
        attempts = 0
        while next_entity.is_dead and attempts < len(self.turn_order):
            self.add_log_message(f"Skipping dead entity {next_entity.name} in turn order.")
            self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
            next_entity = self.turn_order[self.current_turn_index]
            attempts += 1

        if attempts >= len(self.turn_order):
            self.add_log_message("All entities in turn order are dead.")
            self.game_state = "game_over_player_lose"
            return

        self._start_entity_turn(next_entity)
        self.check_game_over_conditions()

    def get_valid_moves(self, entity: Entity, ability: Ability | None = None) -> list[tuple[int, int]]:
        """Get all valid move positions for an entity within their AP range."""
        if not ability or ability.id_name != "move":
            return []

        valid_moves = []
        max_range = min(entity.current_ap, ability.range)

        for dx in range(-max_range, max_range + 1):
            for dy in range(-max_range, max_range + 1):
                manhattan_dist = abs(dx) + abs(dy)
                if manhattan_dist == 0 or manhattan_dist > max_range:
                    continue

                new_x, new_y = entity.x + dx, entity.y + dy
                if (self.game_map.is_walkable(new_x, new_y) and 
                    not self.get_blocking_entity_at(new_x, new_y, exclude_entity=entity)):
                    
                    # Check if path exists and is within AP cost
                    path = self.find_path(entity.x, entity.y, new_x, new_y)
                    if path and len(path) - 1 <= entity.current_ap:
                        valid_moves.append((new_x, new_y))

        return valid_moves

    def get_reachable_tiles_with_ap_cost(self, entity: Entity) -> list[tuple[tuple[int, int], int]]:
        """Get all reachable tiles with their AP costs for an entity."""
        reachable = []
        max_ap = entity.current_ap

        for dx in range(-max_ap, max_ap + 1):
            for dy in range(-max_ap, max_ap + 1):
                manhattan_dist = abs(dx) + abs(dy)
                if manhattan_dist == 0 or manhattan_dist > max_ap:
                    continue

                new_x, new_y = entity.x + dx, entity.y + dy
                if (self.game_map.is_walkable(new_x, new_y) and 
                    not self.get_blocking_entity_at(new_x, new_y, exclude_entity=entity)):
                    
                    path = self.find_path(entity.x, entity.y, new_x, new_y)
                    if path:
                        ap_cost = len(path) - 1
                        if ap_cost <= max_ap:
                            reachable.append(((new_x, new_y), ap_cost))

        return reachable

    def get_valid_targets_for_ability(self, entity: Entity, ability: Ability | None = None) -> list[tuple[int, int]]:
        """Get all valid target tiles for an ability."""
        if not ability:
            return []

        in_range_tiles = []
        range_val = ability.range

        if ability.id_name == "move":
            return self.get_valid_moves(entity, ability)

        if ability.target_type == TargetType.SELF:
            return [(entity.x, entity.y)]

        if ability.effect_radius > 0:
            # For AoE abilities, return tiles where the effect can be centered
            for r_x in range(-ability.effect_radius, ability.effect_radius + 1):
                for r_y in range(-ability.effect_radius, ability.effect_radius + 1):
                    if abs(r_x) + abs(r_y) <= range_val:
                        tile_x, tile_y = entity.x + r_x, entity.y + r_y
                        if self.game_map.is_valid(tile_x, tile_y):
                            in_range_tiles.append((tile_x, tile_y))
            return list(set(in_range_tiles))

        # For other target types, calculate based on ability.range
        for y_coord in range(self.game_map.height):
            for x_coord in range(self.game_map.width):
                if ability.target_type != TargetType.TILE and (x_coord, y_coord) == (entity.x, entity.y) and ability.effect_radius == 0:
                    continue
                
                dist = manhattan_distance((entity.x, entity.y), (x_coord, y_coord))
                if dist <= range_val:
                    in_range_tiles.append((x_coord, y_coord))
        
        return list(set(in_range_tiles))

    def get_blocking_entity_at(self, x: int, y: int, exclude_entity: Entity | None = None) -> Entity | None:
        """Returns the entity at the given coordinates if it blocks movement, otherwise None."""
        for entity in self.entities:
            if entity.x == x and entity.y == y and not entity.is_dead and entity != exclude_entity:
                return entity
        return None

    def _execute_action(self, actor: Entity, ability: Ability, target_pos: tuple[int, int]) -> tuple[bool, str]:
        """
        A generic method to execute an action for any entity.
        
        Args:
            actor: The entity performing the action
            ability: The ability being used
            target_pos: Target position (x, y)
            
        Returns:
            tuple[bool, str]: (success, message)
        """
        # 1. Check AP cost (for non-move abilities, move AP is checked in Ability.execute)
        if ability.id_name != "move" and actor.current_ap < ability.ap_cost:
            return False, f"Not enough AP for {ability.name}."

        # 2. Check Range
        if not self.is_target_in_ability_range(actor, ability, target_pos):
            return False, f"Target is out of range for {ability.name}."
        
        # 3. Execute the ability's own logic
        success, message = ability.execute(actor, target_pos, self)

        # 4. Deduct AP for non-move abilities if successful
        #    AP for "move" is now handled within Ability.execute itself.
        if success and ability.id_name != "move":
            actor.current_ap -= ability.ap_cost
            # Append AP cost to message only if not already handled by ability.execute (e.g. for moves)
            if "AP left" not in message: 
                message += f" AP left: {actor.current_ap}."
        
        return success, message

    def handle_player_action(self, action_type: str, target_pos: tuple[int, int] | None = None, ability_to_use: Ability | None = None) -> tuple[bool, str]:
        if not self.player or self.player.is_dead:
            return False, "Player is not available."
        if self.game_state != "player_turn" or self.get_current_turn_entity() != self.player:
            return False, "Not player's turn."

        success = False
        message = ""

        if action_type == "ability" and ability_to_use and target_pos:
            success, message = self._execute_action(self.player, ability_to_use, target_pos)
            self.add_log_message(message)
        elif action_type == "end_turn":
            self.end_player_turn()
            success = True
            message = "Player ends turn."
        else:
            message = "Invalid action."
            success = False

        # Auto-end turn if AP reaches 0
        if success and self.player.current_ap <= 0 and self.game_state == "player_turn":
            self.add_log_message(f"{self.player.name} has 0 AP. Ending turn automatically.")
            self.end_player_turn()
        
        self.check_game_over_conditions()
        return success, message

    async def run_npc_turn(self, npc: Entity):
        """
        Execute an NPC's turn using their behavior strategy.
        This replaces the old run_npc_behavior method.
        """
        print(f"ENGINE_DEBUG: run_npc_turn called for {npc.name}. Is dead: {npc.is_dead}. Current turn entity: {self.get_current_turn_entity().name if self.get_current_turn_entity() else 'None'}") # DEBUG
        if npc.is_dead or self.get_current_turn_entity() != npc:
            print(f"ENGINE_DEBUG: run_npc_turn returning early for {npc.name}. Condition: is_dead={npc.is_dead}, current_turn_entity_is_npc={self.get_current_turn_entity() == npc}") # DEBUG
            return

        self.add_log_message(f"--- {npc.name}'s turn (AP: {npc.current_ap}) ---")

        # Safety counter to prevent infinite loops
        actions_taken = 0
        max_actions = 10

        while npc.current_ap > 0 and actions_taken < max_actions:
            if not npc.behavior:
                self.add_log_message(f"{npc.name} has no behavior defined. Ending turn.")
                print(f"ENGINE_DEBUG: {npc.name} has no behavior. Ending turn.") # DEBUG
                break

            # Ask the behavior strategy for an action
            print(f"ENGINE_DEBUG: {npc.name} calling behavior.choose_action. Behavior type: {type(npc.behavior)}") # DEBUG
            action = npc.behavior.choose_action(npc, self)
            print(f"ENGINE_DEBUG: {npc.name} behavior.choose_action returned: {action}") # DEBUG
            
            if action:
                ability, target_pos = action
                success, message = self._execute_action(npc, ability, target_pos)
                self.add_log_message(message)
                
                if not success:
                    # If action failed, stop trying
                    break
                    
                actions_taken += 1
                # Add a small delay for pacing NPC actions if desired
                await asyncio.sleep(0.05) # Example: 50ms delay between NPC actions
            else:
                # Behavior decided to do nothing
                self.add_log_message(f"{npc.name} chooses to wait.")
                break
            
            # Check for game over after each action
            if self.player and self.player.is_dead:
                self.check_game_over_conditions()
                return
            
            # Yield control briefly if many actions are possible in a single turn
            if actions_taken % 3 == 0: # Example: yield every 3 actions
                 await asyncio.sleep(0)


        self.add_log_message(f"--- {npc.name}'s turn ends ---")
        self.next_turn() # next_turn itself is synchronous

    def find_path(self, start_x: int, start_y: int, end_x: int, end_y: int) -> list[tuple[int, int]] | None:
        """
        Simple pathfinding using breadth-first search (BFS).
        Returns a list of (x, y) coordinates representing the path from start to end.
        Returns None if no path is found.
        """
        if start_x == end_x and start_y == end_y:
            return [(start_x, start_y)]
        
        if not self.game_map.is_valid(end_x, end_y) or not self.game_map.is_walkable(end_x, end_y):
            return None
        
        from collections import deque
        queue = deque([(start_x, start_y, [(start_x, start_y)])])
        visited = {(start_x, start_y)}
        
        while queue:
            x, y, path = queue.popleft()
            
            # Check all 4 cardinal directions
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                
                if (nx, ny) in visited:
                    continue
                
                if not self.game_map.is_valid(nx, ny) or not self.game_map.is_walkable(nx, ny):
                    continue
                
                # Check for blocking entities (but allow movement to the target even if player is there)
                blocking_entity = self.get_blocking_entity_at(nx, ny)
                if blocking_entity and (nx, ny) != (end_x, end_y):
                    continue
                
                # Check height difference for climbing
                current_height = self.game_map.get_height(x, y)
                target_height = self.game_map.get_height(nx, ny)
                if target_height - current_height > MAX_CLIMB_HEIGHT_DIFF:
                    continue
                
                new_path = path + [(nx, ny)]
                
                if nx == end_x and ny == end_y:
                    return new_path
                
                visited.add((nx, ny))
                queue.append((nx, ny, new_path))
        
        return None

    def is_target_in_ability_range(self, entity: Entity, ability: Ability, target_pos: tuple[int, int]) -> bool:
        """Check if a target position is within the range of an ability for the given entity."""
        if not ability:
            return False
        
        entity_pos = (entity.x, entity.y)
        distance = manhattan_distance(entity_pos, target_pos)
        return distance <= ability.range

    def log_message(self, message: str):
        """
        Compatibility method that delegates to add_log_message.
        """
        self.add_log_message(message)

    def end_player_turn(self):
        """End the player's turn and advance to the next entity."""
        if self.player:
            self.add_log_message(f"{self.player.name}'s turn ends. AP remaining: {self.player.current_ap}")
        self.next_turn()
