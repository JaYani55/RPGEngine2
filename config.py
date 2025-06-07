# Configuration settings for the game

# Screen dimensions
SCREEN_WIDTH = 1024 # Increased for more space
SCREEN_HEIGHT = 768

# Game speed
FPS = 30

# Tile and Font settings for ASCII rendering
TILE_SIZE = 20  # Pixel size of each ASCII character cell (width and height for mono)
FONT_NAME = None  # None for pygame default, or path to a .ttf mono font like 'cour.ttf'
FONT_SIZE = 18    # Size of the font, adjusted for TILE_SIZE

# Colors (can be expanded)
COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "grey": (128, 128, 128),
    "light_grey": (200, 200, 200),
    "dark_grey": (50, 50, 50),

    # UI specific
    "ui_background": (30, 30, 40),
    "ui_text": (220, 220, 220),
    "ui_text_highlight": (255, 255, 150),
    "ui_border": (80, 80, 100),
    "button_normal": (70, 70, 90),
    "button_hover": (100, 100, 120),
    "button_text": (230, 230, 230),

    # Game rendering specific
    "wall": (130, 110, 90),
    "floor": (70, 60, 50),
    "floor_dark": (40, 30, 20), # For deeper areas or variation
    "water": (60, 80, 150),
    "player": (60, 180, 255),      # Light Blue
    "enemy": (255, 80, 60),        # Light Red
    "npc_friendly": (80, 220, 150), # Light Green/Cyan
    "text_default": (200, 200, 200),
    "text_light": (230, 230, 230),
    "text_dim": (150, 150, 150),

    # Highlights
    "highlight_move": (50, 150, 255, 120),      # Semi-transparent Blue
    "highlight_attack": (255, 80, 50, 120),     # Semi-transparent Red
    "highlight_selected": (255, 220, 50, 100), # Semi-transparent Yellow
    "highlight_current_turn": (200, 200, 200, 70) # Semi-transparent White/Grey
}

# Editor specific settings
EDITOR_GRID_COLOR = COLORS["dark_grey"]
EDITOR_HIGHLIGHT_COLOR = COLORS["yellow"]

# Data paths (already in data_manager.py, but can be centralized or referenced)
# DATA_PATH = "data"
# MAP_DATA_PATH = f"{DATA_PATH}/maps/"
# ENTITY_DATA_PATH = f"{DATA_PATH}/entities/"

# Game mechanics
DEFAULT_PLAYER_HP = 100
DEFAULT_PLAYER_AP = 5
# Ability specific stats might be better in JSON definitions for abilities
# PISTOL_RANGE = 5
# PISTOL_AP_COST = 2
# PISTOL_DAMAGE = 10

MAX_CLIMB_HEIGHT_DIFFERENCE = 1
MAX_MAP_HEIGHT_LEVEL = 5
