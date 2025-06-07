# Utility functions for the game

import math

def distance(p1, p2):
    """Calculate Euclidean distance between two points (tuples or lists)."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def manhattan_distance(p1, p2):
    """Calculate Manhattan distance between two points."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def clamp(value, min_val, max_val):
    """Clamp a value between a minimum and maximum."""
    return max(min_val, min(value, max_val))

# Add more utility functions as needed, for example:
# - Pathfinding (A*)
# - Line of sight
# - JSON loading/saving helpers (if not in a dedicated data manager)
# - Grid to pixel coordinate conversion and vice-versa

def grid_to_pixel(grid_x, grid_y, tile_size):
    """Converts grid coordinates to pixel coordinates."""
    return grid_x * tile_size, grid_y * tile_size

def pixel_to_grid(pixel_x, pixel_y, tile_size):
    """Converts pixel coordinates to grid coordinates."""
    return pixel_x // tile_size, pixel_y // tile_size

if __name__ == '__main__':
    # Example usage
    point1 = (0, 0)
    point2 = (3, 4)
    print(f"Euclidean distance between {point1} and {point2}: {distance(point1, point2)}")
    print(f"Manhattan distance between {point1} and {point2}: {manhattan_distance(point1, point2)}")

    val = 15
    min_v = 0
    max_v = 10
    print(f"Clamping {val} between {min_v} and {max_v}: {clamp(val, min_v, max_v)}")
    val = 5
    print(f"Clamping {val} between {min_v} and {max_v}: {clamp(val, min_v, max_v)}")

    tile_s = 20
    grid_coords = (5, 3)
    pixel_coords = grid_to_pixel(grid_coords[0], grid_coords[1], tile_s)
    print(f"Grid {grid_coords} to Pixel: {pixel_coords}")

    back_to_grid = pixel_to_grid(pixel_coords[0], pixel_coords[1], tile_s)
    print(f"Pixel {pixel_coords} to Grid: {back_to_grid}")
