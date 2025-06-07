from enum import Enum, auto

class TargetType(Enum):
    SELF = auto()
    ENEMY = auto()
    ALLY = auto()
    TILE = auto()
    ANY_ENTITY = auto()

class Ability:
    def __init__(self, name, ap_cost, range_val, damage_amount, damage_type, target_type, description, effect_radius=0):
        self.name = name
        self.ap_cost = ap_cost
        self.range = range_val  # Range of the ability (e.g., 5 for Pistol Shot, 1 for melee)
        self.damage_amount = damage_amount
        self.damage_type = damage_type # e.g., "physical", "elemental", "healing"
        self.target_type = target_type # TargetType enum
        self.description = description
        self.effect_radius = effect_radius # For AoE abilities, 0 for single target

    def __str__(self):
        return f"{self.name} (AP: {self.ap_cost}, Range: {self.range}, Dmg: {self.damage_amount})"

# --- Predefined Abilities ---

class MoveAbility(Ability):
    def __init__(self):
        super().__init__(
            name="Move",
            ap_cost=1, # Cost per tile moved
            range_val=1, # Effectively, range is dynamic based on AP
            damage_amount=0,
            damage_type=None,
            target_type=TargetType.TILE,
            description="Move to an adjacent valid tile. Cost is per tile."
        )

class PistolShotAbility(Ability):
    def __init__(self):
        super().__init__(
            name="Pistol Shot",
            ap_cost=2,
            range_val=5,
            damage_amount=10,
            damage_type="physical",
            target_type=TargetType.ENEMY,
            description="A standard ranged attack with a pistol. Deals 10 physical damage."
        )

# --- Ability Registry ---
# This allows us to easily fetch ability objects by their name or ID.
# Entity JSON files can then just store a list of ability names.

ABILITIES_REGISTRY = {
    "Move": MoveAbility(),
    "Pistol Shot": PistolShotAbility(),
    # Add more abilities here as they are created
    # e.g., "Melee Attack": MeleeAttackAbility(),
    #       "Heal": HealAbility(),
}

def get_ability(ability_name: str) -> Ability | None:
    """Fetches an ability instance from the registry."""
    return ABILITIES_REGISTRY.get(ability_name)

if __name__ == '__main__':
    move = get_ability("Move")
    pistol_shot = get_ability("Pistol Shot")

    if move:
        print(f"Ability: {move.name}")
        print(f"  Description: {move.description}")
        print(f"  AP Cost: {move.ap_cost}")
        print(f"  Target Type: {move.target_type}")

    if pistol_shot:
        print(f"\nAbility: {pistol_shot.name}")
        print(f"  Description: {pistol_shot.description}")
        print(f"  AP Cost: {pistol_shot.ap_cost}")
        print(f"  Range: {pistol_shot.range}")
        print(f"  Damage: {pistol_shot.damage_amount} {pistol_shot.damage_type}")
        print(f"  Target Type: {pistol_shot.target_type}")

    # Example of how an entity might store its abilities
    player_abilities_names = ["Move", "Pistol Shot", "NonExistentAbility"]
    player_actual_abilities = []
    for name in player_abilities_names:
        ability = get_ability(name)
        if ability:
            player_actual_abilities.append(ability)
        else:
            print(f"Warning: Ability '{name}' not found in registry.")
    
    print("\nPlayer's loaded abilities:")
    for ab in player_actual_abilities:
        print(f" - {ab.name}")

