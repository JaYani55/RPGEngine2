'''
Defines TileTypes for the game map.
'''
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TileType:
    char: str
    name: str
    walkable: bool
    movement_cost_modifier: int = 0  # Additional AP cost to enter
    statuses_granted: List[str] = field(default_factory=list)
    description: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = f"{self.name} ({self.char})"

# Define all available tile types
TILE_TYPES = {
    ".": TileType(char=".", name="Floor", walkable=True, description="Standard floor tile."),
    "#": TileType(char="#", name="Bush", walkable=True, movement_cost_modifier=1, statuses_granted=["stealth_bonus"], description="Slows movement, grants stealth."),
    "w": TileType(char="w", name="Wall", walkable=False, statuses_granted=["cover"], description="Impassable wall, provides cover."),
    "~": TileType(char="~", name="Water", walkable=True, statuses_granted=["swimming", "wet"], description="Water, requires swimming and makes entities wet."),
    "T": TileType(char="T", name="Tree", walkable=False, statuses_granted=["cover"], description="Impassable tree, provides cover."),
    "L": TileType(char="L", name="Container", walkable=True, statuses_granted=["container"], description="Passable container or loot spot."),
    ",": TileType(char=",", name="Tall Grass", walkable=True, statuses_granted=["stealth_bonus"], description="Tall grass, grants stealth."),
    "M": TileType(char="M", name="Medium Cover", walkable=True, statuses_granted=["cover"], description="Provides medium cover.")
}

DEFAULT_TILE_CHAR = "."

def get_tile_type(char: str) -> Optional[TileType]:
    return TILE_TYPES.get(char)

def get_default_tile_type() -> TileType:
    return TILE_TYPES[DEFAULT_TILE_CHAR]

def get_available_tile_chars() -> List[str]:
    return list(TILE_TYPES.keys())

def get_available_tile_types() -> List[TileType]:
    return list(TILE_TYPES.values())

if __name__ == '__main__':
    print("Available Tile Types:")
    for char, tile_type in TILE_TYPES.items():
        print(f"  {tile_type.char} ({tile_type.name}): Walkable={tile_type.walkable}, CostMod={tile_type.movement_cost_modifier}, Statuses={tile_type.statuses_granted}")
    
    print(f"\nDefault tile: {get_default_tile_type().name}")
    bush = get_tile_type("#")
    if bush:
        print(f"Bush details: {bush}")

