from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum, auto
import json # Required for type hinting if not already present
from data_manager import load_all_abilities_from_categorized_json # New import

if TYPE_CHECKING:
    from engine import GameEngine, Entity # Forward declaration for type hinting

class TargetType(Enum):
    SELF = "SELF"
    ENEMY = "ENEMY"
    ALLY = "ALLY"
    TILE = "TILE"
    ANY_ENTITY = "ANY_ENTITY"

    @staticmethod
    def from_string(s: str):
        try:
            return TargetType[s.upper()]
        except KeyError:
            print(f"Warning: Invalid TargetType string '{s}'. Defaulting to TILE.")
            return TargetType.TILE

class Ability:
    def __init__(self, id_name: str, name: str, ap_cost: int, range_val: int, 
                 damage_amount: int, damage_type: str | None, target_type: TargetType, 
                 description: str, effect_radius: int = 0):
        self.id_name = id_name # e.g., "pistol_shot"
        self.name = name         # e.g., "Pistol Shot"
        self.ap_cost = ap_cost
        self.range = range_val
        self.damage_amount = damage_amount
        self.damage_type = damage_type
        self.target_type = target_type
        self.description = description
        self.effect_radius = effect_radius

    def execute(self, actor: Entity, target_pos: tuple[int, int], engine: GameEngine) -> tuple[bool, str]:
        """
        Executes the ability.
        This base method handles simple damage and movement.
        More complex abilities might need to be overridden this or be handled by subclasses.
        """
        # --- Movement ---
        if self.id_name == "move":
            path = engine.find_path(actor.x, actor.y, target_pos[0], target_pos[1])
            if not path or len(path) <= 1:
                return False, f"{actor.name} cannot find a path to ({target_pos[0]},{target_pos[1]})."
            
            ap_cost_for_move = len(path) - 1
            if actor.current_ap < ap_cost_for_move:
                return False, f"Not enough AP for {actor.name} to move. Needs {ap_cost_for_move}, has {actor.current_ap}."
            if ap_cost_for_move > self.range: # Check against ability's max range for a single move action
                 return False, f"{actor.name} cannot move that far ({ap_cost_for_move} steps) with {self.name} (Max: {self.range} steps)."

            # Check if the destination is blocked by another entity (unless it's the actor itself, which shouldn't happen here)
            blocking_entity = engine.get_blocking_entity_at(target_pos[0], target_pos[1], exclude_entity=actor)
            if blocking_entity:
                return False, f"Cannot move to ({target_pos[0]},{target_pos[1]}), tile is occupied by {blocking_entity.name}."

            actor.x, actor.y = target_pos[0], target_pos[1]
            actor.current_ap -= ap_cost_for_move # Deduct AP for movement
            return True, f"{actor.name} moves to ({target_pos[0]},{target_pos[1]}) using {ap_cost_for_move} AP. AP left: {actor.current_ap}."

        # --- Damage Application (for non-move abilities) ---
        message_parts = []
        targets_hit = []

        if self.effect_radius == 0: # Single target
            target_entity = engine.get_blocking_entity_at(target_pos[0], target_pos[1])
            if target_entity:
                targets_hit.append(target_entity)
            elif self.target_type not in [TargetType.TILE, TargetType.SELF]: # If targeting entity but none found
                return False, f"No target entity at ({target_pos[0]},{target_pos[1]}) for {self.name}."
        else: # AoE
            for entity_in_list in engine.entities:
                if not entity_in_list.is_dead:
                    # Manhattan distance for AoE
                    dist = abs(entity_in_list.x - target_pos[0]) + abs(entity_in_list.y - target_pos[1]) 
                    if dist <= self.effect_radius:
                        targets_hit.append(entity_in_list)
            if not targets_hit and self.target_type not in [TargetType.TILE, TargetType.SELF]:
                 return False, f"No targets in AoE of {self.name} at ({target_pos[0]},{target_pos[1]})."

        if not targets_hit and self.target_type not in [TargetType.TILE, TargetType.SELF]:
            # If it's an attack ability that requires a target entity but none were hit
             return False, f"{self.name} did not hit any valid targets."

        if self.damage_amount > 0:
            if not targets_hit and self.target_type not in [TargetType.TILE, TargetType.SELF]:
                 return False, f"{self.name} missed or no target found."

            for target_entity in targets_hit:
                # Check faction for ENEMY/ALLY targeting
                if self.target_type == TargetType.ENEMY and target_entity.faction == actor.faction:
                    message_parts.append(f"{target_entity.name} is friendly, not targeted by {self.name}.")
                    continue 
                if self.target_type == TargetType.ALLY and target_entity.faction != actor.faction:
                    message_parts.append(f"{target_entity.name} is not friendly, not targeted by {self.name}.")
                    continue
                
                actual_damage = max(0, self.damage_amount - target_entity.defense)
                damage_message = target_entity.take_damage(actual_damage)
                message_parts.append(f"{actor.name} uses {self.name} on {target_entity.name}. {damage_message}")
                if target_entity.is_dead:
                    engine.add_log_message(f"{target_entity.name} was defeated by {actor.name}.")
        elif self.target_type == TargetType.TILE:
            message_parts.append(f"{actor.name} uses {self.name} on tile ({target_pos[0]},{target_pos[1]}).")
        elif self.target_type == TargetType.SELF:
             message_parts.append(f"{actor.name} uses {self.name} on self.")
        else: # No damage, but ability might have other effects
            message_parts.append(f"{actor.name} uses {self.name}.")
            if not targets_hit and self.target_type not in [TargetType.TILE, TargetType.SELF]:
                 message_parts.append("No targets affected.")

        if not message_parts:
            # This case implies an ability that isn't move, isn't damage, and isn't TILE/SELF, and hit no one.
            # Or a damage ability that hit no one and wasn't TILE/SELF.
            # It might be valid if an ability is purely cosmetic or has other side effects not yet coded.
            # For now, consider it a non-action if nothing descriptive happened.
            if self.damage_amount > 0 or self.target_type not in [TargetType.TILE, TargetType.SELF]:
                 return False, f"{self.name} had no discernible effect or missed all targets."
            else: # E.g. a self-buff with no immediate message, or a tile effect with no message
                 message_parts.append(f"{self.name} was used.") # Generic success message
            
        return True, " ".join(message_parts)

    def __str__(self):
        return f"{self.name} (ID: {self.id_name}, AP: {self.ap_cost}, Range: {self.range}, Dmg: {self.damage_amount})"

# --- Ability Registry --- 
ABILITIES_REGISTRY: dict[str, Ability] = {}

def load_abilities():
    """Loads all abilities from categorized JSON data into the ABILITIES_REGISTRY."""
    print("Loading abilities from JSON data...")
    raw_abilities_data = load_all_abilities_from_categorized_json()
    
    if not raw_abilities_data:
        print("No ability data found or loaded. ABILITIES_REGISTRY will be empty.")
        ABILITIES_REGISTRY.clear()
        return

    new_registry = {}
    for ability_id, data in raw_abilities_data.items():
        try:
            # Ensure all required fields are present, provide defaults or skip if critical ones missing
            name = data.get("name", ability_id.replace("_", " ").title()) # Default name from id
            ap_cost = int(data.get("ap_cost", 0))
            range_val = int(data.get("range", 0))
            damage_amount = int(data.get("damage_amount", 0))
            damage_type = data.get("damage_type") # Can be None
            target_type_str = data.get("target_type", "TILE") # Default to TILE if missing
            target_type = TargetType.from_string(target_type_str)
            description = data.get("description", "No description provided.")
            effect_radius = int(data.get("effect_radius", 0))

            new_registry[ability_id] = Ability(
                id_name=ability_id,
                name=name,
                ap_cost=ap_cost,
                range_val=range_val,
                damage_amount=damage_amount,
                damage_type=damage_type,
                target_type=target_type,
                description=description,
                effect_radius=effect_radius
            )
            # print(f"Successfully loaded ability: {ability_id}")
        except KeyError as e:
            print(f"Error: Missing key '{e}' in ability data for '{ability_id}'. Skipping.")
        except ValueError as e:
            print(f"Error: Invalid value in ability data for '{ability_id}' ({e}). Skipping.")
        except Exception as e:
            print(f"An unexpected error occurred while loading ability '{ability_id}': {e}. Skipping.")
    
    ABILITIES_REGISTRY.clear()
    ABILITIES_REGISTRY.update(new_registry)
    print(f"Abilities loaded. Registry contains {len(ABILITIES_REGISTRY)} abilities: {list(ABILITIES_REGISTRY.keys())}")

def get_ability(ability_id_name: str) -> Ability | None:
    """Fetches an ability instance from the registry by its ID name."""
    return ABILITIES_REGISTRY.get(ability_id_name)

# Load abilities when the module is imported
load_abilities()

if __name__ == '__main__':
    print("\\n--- Abilities Registry Test ---")
    if not ABILITIES_REGISTRY:
        print("ABILITIES_REGISTRY is empty. Make sure ability JSON files exist and are loaded.")
    else:
        print(f"Available ability IDs: {list(ABILITIES_REGISTRY.keys())}")

    move_ability = get_ability("move")
    if move_ability:
        print(f"\\nAbility: {move_ability.name} (ID: {move_ability.id_name})")
        print(f"  Description: {move_ability.description}")
        print(f"  AP Cost: {move_ability.ap_cost}")
        print(f"  Target Type: {move_ability.target_type.value}") # Use .value for enum string

    pistol_shot_ability = get_ability("pistol_shot")
    if pistol_shot_ability:
        print(f"\\nAbility: {pistol_shot_ability.name} (ID: {pistol_shot_ability.id_name})")
        print(f"  Description: {pistol_shot_ability.description}")
        print(f"  AP Cost: {pistol_shot_ability.ap_cost}")
        print(f"  Range: {pistol_shot_ability.range}")
        print(f"  Damage: {pistol_shot_ability.damage_amount} {pistol_shot_ability.damage_type}")
        print(f"  Target Type: {pistol_shot_ability.target_type.value}")

    fireball_ability = get_ability("fireball") # From example in data_manager
    if fireball_ability:
        print(f"\\nAbility: {fireball_ability.name} (ID: {fireball_ability.id_name})")
        print(f"  Description: {fireball_ability.description}")
        print(f"  AP Cost: {fireball_ability.ap_cost}")
        print(f"  Range: {fireball_ability.range}")
        print(f"  Damage: {fireball_ability.damage_amount} {fireball_ability.damage_type}")
        print(f"  Target Type: {fireball_ability.target_type.value}")
        print(f"  Effect Radius: {fireball_ability.effect_radius}")

    # Example of how an entity might store its abilities (using IDs)
    player_ability_ids = ["move", "pistol_shot", "non_existent_ability"]
    player_actual_abilities = []
    print("\\n--- Player Ability Loading Test (using IDs) ---")
    for id_name in player_ability_ids:
        ability = get_ability(id_name)
        if ability:
            player_actual_abilities.append(ability)
            print(f"Loaded: {ability.name}")
        else:
            print(f"Warning: Ability ID '{id_name}' not found in registry.")
    
    print("\\nPlayer's resolved abilities:")
    for ab in player_actual_abilities:
        print(f" - {ab.name} (AP: {ab.ap_cost})")

