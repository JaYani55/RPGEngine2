# AI Behavior System using Strategy Pattern
from __future__ import annotations
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from engine import GameEngine, Entity
    from abilities import Ability

class Behavior(ABC):
    """Abstract base class for all entity behaviors."""
    
    @abstractmethod
    def choose_action(self, owner: Entity, engine: GameEngine) -> tuple[Ability, tuple[int, int]] | None:
        """
        Decide which action to take.
        Returns a tuple of (ability_to_use, target_position) or None if no action.
        """
        pass

class AggressiveMelee(Behavior):
    """
    A behavior that focuses on attacking the player in melee range.
    Will move closer to the player if not in attack range.
    """
    
    def choose_action(self, owner: Entity, engine: GameEngine) -> tuple[Ability, tuple[int, int]] | None:
        print(f"AI_DEBUG ({owner.name} - AggressiveMelee): choose_action called. Owner AP: {owner.current_ap}") # DEBUG
        player = engine.player
        if not player or player.is_dead:
            print(f"AI_DEBUG ({owner.name} - AggressiveMelee): No player or player is dead. Returning None.") # DEBUG
            return None

        # 1. Try to attack if in range
        print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Checking attack abilities. Abilities: {[ab.id_name for ab in owner.abilities]}") # DEBUG
        for ability in owner.abilities:
            if (ability.damage_amount > 0 and 
                ability.id_name != "move" and 
                owner.current_ap >= ability.ap_cost):
                
                print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Considering attack: {ability.id_name}. Cost: {ability.ap_cost}. In range? Checking...") # DEBUG
                if engine.is_target_in_ability_range(owner, ability, (player.x, player.y)):
                    print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Attack {ability.id_name} IS in range. Returning action.") # DEBUG
                    return (ability, (player.x, player.y))
                else:
                    print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Attack {ability.id_name} NOT in range.") # DEBUG

        # 2. If no attack is possible, try to move closer
        move_ability = owner.get_ability_by_id_name("move")
        print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Checking move. Move ability found: {move_ability is not None}. Owner AP: {owner.current_ap}") # DEBUG
        if move_ability and owner.current_ap > 0: # Original check was > 0, but move itself costs AP. Let's assume move_ability.ap_cost is 1 for path steps.
            path = engine.find_path(owner.x, owner.y, player.x, player.y)
            print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Path to player ({player.x},{player.y}): {path}") # DEBUG
            if path and len(path) > 1:
                # Move as far as possible along the path within AP limits
                # The 'move' ability in abilities.py has range, which is used as max_steps for one move action.
                # AP cost is per step.
                max_ap_for_move = owner.current_ap 
                
                # Max distance for a single "move" action is move_ability.range
                # Number of steps in path is len(path) - 1
                # Actual steps to take is min(max_ap_for_move, len(path)-1, move_ability.range)
                # However, the current move_ability.range is often set to the entity's base AP, which is fine.
                # The AP cost is calculated by path length in Ability.execute for "move"
                
                # We need to find a target tile for the "move" ability.
                # The "move" ability itself will check AP cost against path length.
                # We just need to propose a target tile.
                
                # Let's try to move as far as the 'move' ability's range allows along the path,
                # or fewer steps if AP is insufficient for that full range, or path is shorter.
                
                # The number of steps the NPC *wants* to take along the path.
                # It should not exceed its current AP or the range of its "move" ability.
                # The actual AP cost will be determined by the path length to path[target_step_index].
                
                potential_steps = min(len(path) -1, move_ability.range, owner.current_ap)
                print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Potential steps: {potential_steps} (path_len-1: {len(path)-1}, move_range: {move_ability.range}, current_ap: {owner.current_ap})")


                for step_index in range(potential_steps, 0, -1): # Iterate from furthest possible step backwards
                    target_pos = path[step_index]
                    # Check if this step is valid (walkable and not blocked)
                    if (engine.game_map.is_walkable(target_pos[0], target_pos[1]) and
                        not engine.get_blocking_entity_at(target_pos[0], target_pos[1], exclude_entity=owner)):
                        
                        # Before returning, ensure the AP cost for this specific move is checked.
                        # The `Ability.execute` for "move" does this, but `_execute_action` in engine
                        # skips the initial AP check for "move".
                        # So, the check within `Ability.execute` is the important one.
                        print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Found valid move step. Target: {target_pos}. Path segment length: {step_index}") # DEBUG
                        return (move_ability, target_pos)
                    else:
                        print(f"AI_DEBUG ({owner.name} - AggressiveMelee): Invalid move step to {target_pos}. Walkable: {engine.game_map.is_walkable(target_pos[0], target_pos[1])}, Blocked: {engine.get_blocking_entity_at(target_pos[0], target_pos[1], exclude_entity=owner) is not None}") # DEBUG
        
        print(f"AI_DEBUG ({owner.name} - AggressiveMelee): No action could be taken. Returning None.") # DEBUG
        return None  # No action could be taken

class Cautious(Behavior):
    """
    A behavior that tries to maintain distance from the player.
    Will attack if the player is at medium range, but will retreat if too close.
    """
    
    def __init__(self, preferred_distance: int = 3):
        self.preferred_distance = preferred_distance
    
    def choose_action(self, owner: Entity, engine: GameEngine) -> tuple[Ability, tuple[int, int]] | None:
        player = engine.player
        if not player or player.is_dead:
            return None
        
        from utils import manhattan_distance
        distance_to_player = manhattan_distance((owner.x, owner.y), (player.x, player.y))
        
        # 1. If too close, try to move away
        if distance_to_player < self.preferred_distance:
            move_ability = owner.get_ability_by_id_name("move")
            if move_ability and owner.current_ap > 0:
                # Find a position that increases distance from player
                best_position = None
                best_distance = distance_to_player
                
                # Check positions within movement range
                for dx in range(-owner.current_ap, owner.current_ap + 1):
                    for dy in range(-owner.current_ap, owner.current_ap + 1):
                        if abs(dx) + abs(dy) > owner.current_ap:  # Manhattan distance check
                            continue
                        
                        new_x, new_y = owner.x + dx, owner.y + dy
                        if (engine.game_map.is_walkable(new_x, new_y) and 
                            not engine.get_blocking_entity_at(new_x, new_y, exclude_entity=owner)):
                            
                            new_distance = manhattan_distance((new_x, new_y), (player.x, player.y))
                            if new_distance > best_distance:
                                best_distance = new_distance
                                best_position = (new_x, new_y)
                
                if best_position:
                    return (move_ability, best_position)
        
        # 2. If at good distance, try to attack
        elif distance_to_player <= self.preferred_distance + 1:
            for ability in owner.abilities:
                if (ability.damage_amount > 0 and 
                    ability.id_name != "move" and 
                    owner.current_ap >= ability.ap_cost):
                    
                    if engine.is_target_in_ability_range(owner, ability, (player.x, player.y)):
                        return (ability, (player.x, player.y))
        
        return None

class Defensive(Behavior):
    """
    A behavior that stays in place and only attacks when the player comes close.
    Good for guards or territorial enemies.
    """
    
    def __init__(self, guard_position: tuple[int, int] | None = None, guard_radius: int = 2):
        self.guard_position = guard_position  # Will be set to initial position if None
        self.guard_radius = guard_radius
    
    def choose_action(self, owner: Entity, engine: GameEngine) -> tuple[Ability, tuple[int, int]] | None:
        player = engine.player
        if not player or player.is_dead:
            return None
        
        # Set guard position to current position if not already set
        if self.guard_position is None:
            self.guard_position = (owner.x, owner.y)
        
        from utils import manhattan_distance
        distance_to_player = manhattan_distance((owner.x, owner.y), (player.x, player.y))
        distance_from_guard_pos = manhattan_distance((owner.x, owner.y), self.guard_position)
        
        # 1. If player is close, try to attack
        for ability in owner.abilities:
            if (ability.damage_amount > 0 and 
                ability.id_name != "move" and 
                owner.current_ap >= ability.ap_cost):
                
                if engine.is_target_in_ability_range(owner, ability, (player.x, player.y)):
                    return (ability, (player.x, player.y))
        
        # 2. If too far from guard position, move back
        if distance_from_guard_pos > self.guard_radius:
            move_ability = owner.get_ability_by_id_name("move")
            if move_ability and owner.current_ap > 0:
                path = engine.find_path(owner.x, owner.y, self.guard_position[0], self.guard_position[1])
                if path and len(path) > 1:
                    # Move towards guard position
                    max_steps = min(owner.current_ap, len(path) - 1)
                    target_pos = path[min(max_steps, len(path) - 1)]
                    
                    if (engine.game_map.is_walkable(target_pos[0], target_pos[1]) and 
                        not engine.get_blocking_entity_at(target_pos[0], target_pos[1], exclude_entity=owner)):
                        return (move_ability, target_pos)
        
        return None  # Stay put and wait

# Behavior factory function for easy creation from strings
def create_behavior(behavior_name: str, **kwargs) -> Behavior:
    """
    Factory function to create behavior instances from string names.
    
    Args:
        behavior_name: Name of the behavior to create
        **kwargs: Additional parameters for the behavior
    
    Returns:
        Behavior instance
    """
    behavior_map = {
        "aggressive_melee": AggressiveMelee,
        "aggressive": AggressiveMelee,  # Alias
        "cautious": Cautious,
        "defensive": Defensive,
        "guard": Defensive,  # Alias
    }
    
    behavior_class = behavior_map.get(behavior_name.lower())
    if behavior_class:
        return behavior_class(**kwargs)
    else:
        print(f"Warning: Unknown behavior '{behavior_name}'. Defaulting to AggressiveMelee.")
        return AggressiveMelee()
