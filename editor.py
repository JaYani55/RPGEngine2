import pygame
import json
import os
from config import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, FONT_SIZE, COLORS
from data_manager import save_map_data, load_map_data, list_available_entities, load_entity_data, save_entity_data, DATA_DIR, MAP_DIR # Added save_entity_data
from utils import pixel_to_grid, grid_to_pixel
from abilities import ABILITIES_REGISTRY, get_ability # Added abilities import

# Editor specific constants
EDITOR_TILE_SIZE = TILE_SIZE + 4 # Slightly larger for better clicking
GRID_COLOR = COLORS.get("grey", (100, 100, 100))
HIGHLIGHT_COLOR = COLORS.get("yellow", (255, 255, 0))
TEXT_COLOR = COLORS.get("white", (255, 255, 255))
INPUT_BOX_COLOR = COLORS.get("dark_grey", (50, 50, 50))
INPUT_TEXT_COLOR = COLORS.get("white", (255, 255, 255))
ENTITY_PLAYER_COLOR = COLORS.get("player", (0, 255, 0)) # Example for player start
ENTITY_ENEMY_COLOR = COLORS.get("enemy", (255, 0, 0))   # Example for other entities

class Editor:
    def __init__(self, screen):
        self.screen = screen
        try:
            self.font = pygame.font.Font(None, FONT_SIZE)
            self.font_small = pygame.font.Font(None, FONT_SIZE - 4)
            self.font_large = pygame.font.Font(None, FONT_SIZE + 10)
        except pygame.error as e:
            print(f"Editor Font Error: {e}. Using default.")
            self.font = pygame.font.Font(None, 24)
            self.font_small = pygame.font.Font(None, 20)
            self.font_large = pygame.font.Font(None, 34)

        self.map_data = {
            "name": "untitled_map",
            "tiles": [], # ASCII characters
            "heightmap": [], # Integers 0-5
            "entities_on_map": [] # List of {"id": "entity_name", "x": 0, "y": 0, "is_player_start": True/False}
        }
        self.map_width = 30  # Default map dimensions
        self.map_height = 20
        self.new_map(self.map_width, self.map_height) # Initialize with a blank map

        self.camera_offset_x = 0
        self.camera_offset_y = 0
        self.zoom_level = 1.0 # Not implemented yet

        self.editing_mode = "tiles"  # "tiles", "heights", "entities", "select"
        self.available_tile_chars = ["." , "#", "w", "~", "T"] # Floor, Wall, Water, Tree
        self.current_tile_char_index = 0
        self.current_height_value = 0 # 0 to 5
        
        self.available_entity_definitions = {} # {"id": data}
        self.available_entity_ids = [] # ["player_char", "goblin_1"]
        self.current_entity_id_index = 0
        self.load_entity_definitions()

        self.editing_entity_definition_id = None # ID of the entity definition being edited
        self.selected_ability_for_toggle_idx = 0 # For UI navigation of abilities list

        self.show_save_dialog = False
        self.save_filename_input = "my_map"
        self.show_load_dialog = False
        self.available_map_files = []
        self.selected_map_to_load_index = 0
        
        self.message = "" # For displaying feedback to the user
        self.message_timer = 0

        # Simple UI state
        self.active_input_box = None # "save_filename" or "load_filename"

    def set_message(self, text, duration=120): # duration in frames
        self.message = text
        self.message_timer = duration

    def new_map(self, width, height):
        self.map_width = width
        self.map_height = height
        self.map_data["tiles"] = [["." for _ in range(width)] for _ in range(height)]
        self.map_data["heightmap"] = [[0 for _ in range(width)] for _ in range(height)]
        self.map_data["entities_on_map"] = []
        self.map_data["name"] = "untitled_map"
        self.set_message(f"New {width}x{height} map created.", 180)

    def load_entity_definitions(self):
        self.available_entity_ids = list_available_entities()
        self.available_entity_definitions = {}
        for entity_id in self.available_entity_ids:
            data = load_entity_data(entity_id)
            if data:
                # Ensure 'abilities' key exists and is a list
                if 'abilities' not in data or not isinstance(data['abilities'], list):
                    data['abilities'] = [] 
                self.available_entity_definitions[entity_id] = data
        if not self.available_entity_ids:
            self.set_message("No entity definitions found in data/entities.", 180)
        else:
            self.set_message(f"Loaded {len(self.available_entity_ids)} entity types.", 120)
        self.current_entity_id_index = 0
        self.editing_entity_definition_id = None # Reset when reloading

    def get_grid_coords_from_mouse(self, mouse_pos):
        # Adjust for camera
        world_x = mouse_pos[0] - self.camera_offset_x
        world_y = mouse_pos[1] - self.camera_offset_y
        grid_x = world_x // EDITOR_TILE_SIZE
        grid_y = world_y // EDITOR_TILE_SIZE
        return int(grid_x), int(grid_y)

    def handle_input(self, event):
        if self.editing_entity_definition_id:
            self.handle_entity_ability_editor_input(event)
            return
        if self.show_save_dialog:
            self.handle_save_dialog_input(event)
            return
        if self.show_load_dialog:
            self.handle_load_dialog_input(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            grid_x, grid_y = self.get_grid_coords_from_mouse(event.pos)

            if 0 <= grid_x < self.map_width and 0 <= grid_y < self.map_height:
                if self.editing_mode == "tiles":
                    self.map_data["tiles"][grid_y][grid_x] = self.available_tile_chars[self.current_tile_char_index]
                elif self.editing_mode == "heights":
                    self.map_data["heightmap"][grid_y][grid_x] = self.current_height_value
                elif self.editing_mode == "entities":
                    if self.available_entity_ids:
                        entity_id_to_place = self.available_entity_ids[self.current_entity_id_index]
                        # Check if player start already exists if placing player
                        is_player = self.available_entity_definitions.get(entity_id_to_place, {}).get("behavior") == "player_controlled"
                        
                        # Remove any existing entity at this exact spot first
                        self.map_data["entities_on_map"] = [
                            e for e in self.map_data["entities_on_map"] if not (e["x"] == grid_x and e["y"] == grid_y)
                        ]

                        if is_player:
                            # Remove other player starts if this is a player
                            self.map_data["entities_on_map"] = [e for e in self.map_data["entities_on_map"] if not e.get("is_player_start")]
                            self.map_data["entities_on_map"].append({"id": entity_id_to_place, "x": grid_x, "y": grid_y, "is_player_start": True})
                            self.set_message(f"Placed player start ({entity_id_to_place}) at ({grid_x},{grid_y})", 120)
                        else:
                            self.map_data["entities_on_map"].append({"id": entity_id_to_place, "x": grid_x, "y": grid_y, "is_player_start": False})
                            self.set_message(f"Placed entity ({entity_id_to_place}) at ({grid_x},{grid_y})", 120)
                    else:
                        self.set_message("No entity types available to place.", 120)
                elif self.editing_mode == "select": # Eraser/selector
                     # Remove tile (set to default), height (set to 0), and entity
                    self.map_data["tiles"][grid_y][grid_x] = "."
                    self.map_data["heightmap"][grid_y][grid_x] = 0
                    self.map_data["entities_on_map"] = [
                        e for e in self.map_data["entities_on_map"] if not (e["x"] == grid_x and e["y"] == grid_y)
                    ]
                    self.set_message(f"Cleared tile ({grid_x},{grid_y})", 120)


        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.show_save_dialog = True
                self.active_input_box = "save_filename"
                self.save_filename_input = self.map_data.get("name", "my_map")
            elif event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.show_load_dialog = True
                self.available_map_files = [f.replace(".json", "") for f in os.listdir(MAP_DIR) if f.endswith(".json")]
                self.selected_map_to_load_index = 0
            elif event.key == pygame.K_n and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.new_map(self.map_width, self.map_height) # Or prompt for size

            elif event.key == pygame.K_t: self.editing_mode = "tiles"; self.set_message("Mode: Edit Tiles", 60)
            elif event.key == pygame.K_h: self.editing_mode = "heights"; self.set_message("Mode: Edit Heights", 60)
            elif event.key == pygame.K_e: 
                self.editing_mode = "entities"
                self.set_message("Mode: Place Entities. Press 'A' to edit selected entity type's abilities.", 60)
            elif event.key == pygame.K_x: self.editing_mode = "select"; self.set_message("Mode: Erase/Select", 60)

            elif event.key == pygame.K_a and self.editing_mode == "entities": # 'A' for Abilities
                if self.available_entity_ids:
                    self.editing_entity_definition_id = self.available_entity_ids[self.current_entity_id_index]
                    self.selected_ability_for_toggle_idx = 0 
                    self.set_message(f"Editing abilities for {self.editing_entity_definition_id}. Use Up/Down, Enter to toggle, S to Save, Esc to exit.", 0) # Persistent message
                else:
                    self.set_message("No entity type selected to edit abilities.", 120)
            elif event.key == pygame.K_LEFT:
                if self.editing_mode == "tiles": self.current_tile_char_index = (self.current_tile_char_index - 1) % len(self.available_tile_chars)
                elif self.editing_mode == "entities" and self.available_entity_ids: self.current_entity_id_index = (self.current_entity_id_index - 1) % len(self.available_entity_ids)
                else: self.camera_offset_x += EDITOR_TILE_SIZE # Camera pan
            elif event.key == pygame.K_RIGHT:
                if self.editing_mode == "tiles": self.current_tile_char_index = (self.current_tile_char_index + 1) % len(self.available_tile_chars)
                elif self.editing_mode == "entities" and self.available_entity_ids: self.current_entity_id_index = (self.current_entity_id_index + 1) % len(self.available_entity_ids)
                else: self.camera_offset_x -= EDITOR_TILE_SIZE # Camera pan
            elif event.key == pygame.K_UP:
                if self.editing_mode == "heights": self.current_height_value = min(5, self.current_height_value + 1)
                else: self.camera_offset_y += EDITOR_TILE_SIZE # Camera pan
            elif event.key == pygame.K_DOWN:
                if self.editing_mode == "heights": self.current_height_value = max(0, self.current_height_value - 1)
                else: self.camera_offset_y -= EDITOR_TILE_SIZE # Camera pan
            
            elif event.key == pygame.K_r: # Reload entity definitions
                self.load_entity_definitions()
                self.set_message("Entity definitions reloaded.", 120)


    def handle_save_dialog_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.map_data["name"] = self.save_filename_input
                save_map_data(self.save_filename_input, self.map_data)
                self.set_message(f"Map '{self.save_filename_input}' saved.", 180)
                self.show_save_dialog = False
                self.active_input_box = None
            elif event.key == pygame.K_ESCAPE:
                self.show_save_dialog = False
                self.active_input_box = None
                self.set_message("Save cancelled.", 120)
            elif event.key == pygame.K_BACKSPACE:
                self.save_filename_input = self.save_filename_input[:-1]
            else:
                self.save_filename_input += event.unicode
    
    def handle_load_dialog_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.available_map_files:
                    map_to_load = self.available_map_files[self.selected_map_to_load_index]
                    loaded_data = load_map_data(map_to_load)
                    if loaded_data:
                        self.map_data = loaded_data
                        self.map_width = len(self.map_data["tiles"][0]) if self.map_data["tiles"] else 0
                        self.map_height = len(self.map_data["tiles"]) if self.map_data["tiles"] else 0
                        # Ensure all keys exist
                        if "heightmap" not in self.map_data: self.map_data["heightmap"] = [[0 for _ in range(self.map_width)] for _ in range(self.map_height)]
                        if "entities_on_map" not in self.map_data: self.map_data["entities_on_map"] = []
                        if "name" not in self.map_data: self.map_data["name"] = map_to_load
                        
                        self.set_message(f"Map '{map_to_load}' loaded.", 180)
                    else:
                        self.set_message(f"Failed to load map '{map_to_load}'.", 180)
                self.show_load_dialog = False
            elif event.key == pygame.K_ESCAPE:
                self.show_load_dialog = False
                self.set_message("Load cancelled.", 120)
            elif event.key == pygame.K_UP:
                self.selected_map_to_load_index = (self.selected_map_to_load_index - 1) % len(self.available_map_files) if self.available_map_files else 0
            elif event.key == pygame.K_DOWN:
                self.selected_map_to_load_index = (self.selected_map_to_load_index + 1) % len(self.available_map_files) if self.available_map_files else 0


    def update(self):
        if self.message_timer > 0:
            self.message_timer -= 1
        else:
            self.message = ""
        # Keep camera in sensible bounds (optional)
        # self.camera_offset_x = max(min(0, self.camera_offset_x), SCREEN_WIDTH - self.map_width * EDITOR_TILE_SIZE)
        # self.camera_offset_y = max(min(0, self.camera_offset_y), SCREEN_HEIGHT - self.map_height * EDITOR_TILE_SIZE - 100) # 100 for UI space

    def draw_text(self, text, position, font, color=TEXT_COLOR, center=False):
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = position
        else:
            rect.topleft = position
        self.screen.blit(surface, rect)

    def draw_entities_on_map(self):
        for entity_info in self.map_data["entities_on_map"]:
            entity_id = entity_info["id"]
            ex, ey = entity_info["x"], entity_info["y"]
            char_to_draw = "?" # Default if not found
            # Determine color based on entity type (e.g. player vs NPC)
            entity_def = self.available_entity_definitions.get(entity_id)
            color = ENTITY_ENEMY_COLOR # Default to enemy color
            if entity_def and entity_def.get("behavior") == "player_controlled":
                color = ENTITY_PLAYER_COLOR
            elif entity_info.get("is_player_start"): # Fallback if behavior not present but flag is
                color = ENTITY_PLAYER_COLOR

            if entity_def:
                char_to_draw = entity_def.get("char", "?")
            
            rect = pygame.Rect(
                self.camera_offset_x + ex * EDITOR_TILE_SIZE,
                self.camera_offset_y + ey * EDITOR_TILE_SIZE,
                EDITOR_TILE_SIZE, EDITOR_TILE_SIZE
            )
            entity_char_surf = self.font_large.render(char_to_draw, True, color)
            self.screen.blit(entity_char_surf, entity_char_surf.get_rect(center=rect.center))

    def draw(self):
        self.screen.fill(COLORS.get("dark_grey", (30,30,30))) 

        if self.editing_entity_definition_id:
            self.draw_entity_ability_editor()
            # Draw Message (ensure it's visible over the editor)
            if self.message:
                self.draw_text(self.message, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20), self.font_small, color=COLORS.get("yellow", (255,255,0)), center=True)
            pygame.display.flip() # Update screen and return to skip rest of draw
            return
        
        # Draw grid and map
        for y_coord in range(self.map_height):
            for x_coord in range(self.map_width):
                rect = pygame.Rect(
                    self.camera_offset_x + x_coord * EDITOR_TILE_SIZE,
                    self.camera_offset_y + y_coord * EDITOR_TILE_SIZE,
                    EDITOR_TILE_SIZE, EDITOR_TILE_SIZE
                )
                pygame.draw.rect(self.screen, GRID_COLOR, rect, 1)

                tile_char = self.map_data["tiles"][y_coord][x_coord]
                height_val = self.map_data["heightmap"][y_coord][x_coord]
                
                base_col_val = 60 + height_val * 20 
                tile_bg_color = (base_col_val, base_col_val, base_col_val)
                pygame.draw.rect(self.screen, tile_bg_color, rect.inflate(-2,-2))

                char_surf = self.font.render(tile_char, True, TEXT_COLOR)
                self.screen.blit(char_surf, char_surf.get_rect(center=rect.center))
                
                height_surf = self.font_small.render(str(height_val), True, COLORS.get("light_grey",(180,180,180)))
                self.screen.blit(height_surf, (rect.x + 2, rect.y + 2))

        self.draw_entities_on_map() # Call the new method here

        # Draw UI
        ui_y_start = 10
        self.draw_text(f"Mode: {self.editing_mode.upper()} (T/H/E/X to change)", (10, ui_y_start), self.font, color=TEXT_COLOR)
        ui_y_start += 30
        if self.editing_mode == "tiles":
            selected_char = self.available_tile_chars[self.current_tile_char_index]
            self.draw_text(f"Selected Tile: '{selected_char}' (Arrows to change)", (10, ui_y_start), self.font, color=TEXT_COLOR)
        elif self.editing_mode == "heights":
            self.draw_text(f"Selected Height: {self.current_height_value} (Arrows to change)", (10, ui_y_start), self.font, color=TEXT_COLOR)
        elif self.editing_mode == "entities":
            if self.available_entity_ids:
                entity_id = self.available_entity_ids[self.current_entity_id_index]
                entity_char = self.available_entity_definitions.get(entity_id,{}).get("char", "?")
                self.draw_text(f"Selected Entity: {entity_id} ('{entity_char}') (Arrows to change, R to reload, 'A' to edit abilities)", (10, ui_y_start), self.font, color=TEXT_COLOR) # Updated help text
            else:
                self.draw_text("No entities loaded. Create JSON in data/entities. (R to reload defs)", (10, ui_y_start), self.font_small, color=COLORS.get("yellow", (255,255,0)))
        
        ui_y_start += 30
        self.draw_text("Ctrl+S: Save | Ctrl+L: Load | Ctrl+N: New Map", (10, ui_y_start), self.font_small, color=TEXT_COLOR)
        ui_y_start += 20
        self.draw_text("Pan: Arrow keys (when not changing selection)",(10, ui_y_start), self.font_small, color=TEXT_COLOR)

        # Draw Message
        if self.message and not self.editing_entity_definition_id: # Don't draw if ability editor is open and has its own message
            self.draw_text(self.message, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30), self.font, color=COLORS.get("yellow", (255,255,0)), center=True)

        # Draw Save Dialog
        if self.show_save_dialog:
            self.draw_modal_dialog("Save Map As:", self.save_filename_input, ["Press Enter to Save, Esc to Cancel"])
        
        # Draw Load Dialog
        if self.show_load_dialog:
            lines = ["Select Map to Load:"]
            if not self.available_map_files:
                lines.append("(No maps found in data/maps/)")
            for i, map_name in enumerate(self.available_map_files):
                prefix = "> " if i == self.selected_map_to_load_index else "  "
                lines.append(prefix + map_name)
            lines.append("")
            lines.append("Up/Down to select, Enter to Load, Esc to Cancel")
            self.draw_modal_dialog_multiline(lines)

    def draw_modal_dialog(self, title, input_text, help_lines):
        dialog_width = 400
        dialog_height = 150 + len(help_lines) * 20
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2
        
        pygame.draw.rect(self.screen, COLORS.get("ui_background", (40,40,40)), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(self.screen, COLORS.get("white", (255,255,255)), (dialog_x, dialog_y, dialog_width, dialog_height), 2)

        self.draw_text(title, (dialog_x + 10, dialog_y + 10), self.font, color=TEXT_COLOR)
        
        input_box_rect = pygame.Rect(dialog_x + 10, dialog_y + 40, dialog_width - 20, 30)
        pygame.draw.rect(self.screen, INPUT_BOX_COLOR, input_box_rect)
        self.draw_text(input_text, (input_box_rect.x + 5, input_box_rect.y + 5), self.font, color=INPUT_TEXT_COLOR, center=False)
        
        current_y = dialog_y + 80
        for line in help_lines:
            self.draw_text(line, (dialog_x + 10, current_y), self.font_small, color=TEXT_COLOR)
            current_y += 20
            
    def draw_modal_dialog_multiline(self, lines):
        max_line_width = max(self.font.size(line)[0] for line in lines) if lines else 200
        dialog_width = max(300, max_line_width + 40)
        dialog_height = 40 + len(lines) * (self.font.get_linesize())
        dialog_x = (SCREEN_WIDTH - dialog_width) // 2
        dialog_y = (SCREEN_HEIGHT - dialog_height) // 2

        pygame.draw.rect(self.screen, COLORS.get("ui_background", (40,40,40)), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(self.screen, COLORS.get("white", (255,255,255)), (dialog_x, dialog_y, dialog_width, dialog_height), 2)
        
        current_y = dialog_y + 10
        for line_text in lines: # Renamed line to line_text to avoid conflict with pygame.draw.line
            self.draw_text(line_text, (dialog_x + 20, current_y), self.font, color=TEXT_COLOR, center=False)
            current_y += self.font.get_linesize()


    def is_done(self): # Method to signal exit from editor (e.g., to main menu)
        # For now, editor is exited by changing state in main.py (e.g. pressing ESC)
        return False

    def draw_entity_ability_editor(self):
        if not self.editing_entity_definition_id:
            return

        entity_def = self.available_entity_definitions.get(self.editing_entity_definition_id)
        if not entity_def:
            return # Should not happen

        editor_panel_x = 50
        editor_panel_y = 50
        editor_panel_width = SCREEN_WIDTH - 100
        editor_panel_height = SCREEN_HEIGHT - 100
        
        pygame.draw.rect(self.screen, COLORS.get("ui_background", (40,40,40)), 
                         (editor_panel_x, editor_panel_y, editor_panel_width, editor_panel_height))
        pygame.draw.rect(self.screen, COLORS.get("white", (255,255,255)), 
                         (editor_panel_x, editor_panel_y, editor_panel_width, editor_panel_height), 2)

        title_text = f"Editing Abilities for: {self.editing_entity_definition_id}"
        self.draw_text(title_text, (editor_panel_x + 20, editor_panel_y + 20), self.font_large, color=TEXT_COLOR)

        current_y = editor_panel_y + 70
        help_text = "Up/Down: Select | Enter: Toggle | S: Save Entity File | Esc: Exit"
        self.draw_text(help_text, (editor_panel_x + 20, current_y), self.font_small, color=COLORS.get("light_grey", (180,180,180)))
        current_y += 30

        all_ability_names = sorted(list(ABILITIES_REGISTRY.keys()))
        entity_current_abilities = entity_def.get("abilities", [])

        col1_x = editor_panel_x + 30
        # col2_x = editor_panel_x + editor_panel_width // 2 # For descriptions if needed

        for idx, ability_name in enumerate(all_ability_names):
            if current_y > editor_panel_y + editor_panel_height - 40: # Stop if too many abilities
                self.draw_text("...", (col1_x, current_y), self.font, color=TEXT_COLOR)
                break

            prefix = "> " if idx == self.selected_ability_for_toggle_idx else "  "
            color = COLORS.get("yellow", (255,255,0)) if idx == self.selected_ability_for_toggle_idx else TEXT_COLOR
            
            status_char = "[X]" if ability_name in entity_current_abilities else "[ ]"
            if ability_name == "Move" and "Move" not in entity_current_abilities: # Should always be there
                 status_char = "[X]" # Visually enforce it, logic should handle actual presence
            elif ability_name == "Move": # If it is "Move", make it non-toggleable visually too
                status_char = "[X]"


            ability_display_name = f"{prefix}{status_char} {ability_name}"
            self.draw_text(ability_display_name, (col1_x, current_y), self.font, color=color)
            
            ability_obj = get_ability(ability_name)
            if ability_obj:
                desc_text = f"AP:{ability_obj.ap_cost}, Rng:{ability_obj.range}, Dmg:{ability_obj.damage_amount}"
                if ability_name == "Move":
                    desc_text = f"AP:{ability_obj.ap_cost} per tile"
                self.draw_text(desc_text, (col1_x + 250, current_y), self.font_small, color=COLORS.get("light_grey", (180,180,180)))

            current_y += self.font.get_linesize() + 2


# Example of running the editor standalone for testing (optional)
if __name__ == '__main__':
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Map Editor Standalone Test")
    clock = pygame.time.Clock()
    
    # Ensure data directories exist
    from data_manager import ensure_dirs
    ensure_dirs()

    # Create dummy entity files if they don't exist for testing
    player_def_path = os.path.join(DATA_DIR, "entities", "player_char.json")
    if not os.path.exists(player_def_path):
        with open(player_def_path, "w") as f:
            json.dump({
                "id": "player_char", "name": "Player", "char": "@", "hp": 100, "max_hp": 100, 
                "ap": 5, "max_ap": 5, "abilities": ["Move", "Pistol Shot"], "behavior": "player_controlled", # Ensure Move is here
                "description": "The main character."
            }, f, indent=4)
            print(f"Created dummy entity: {player_def_path}")

    goblin_def_path = os.path.join(DATA_DIR, "entities", "goblin_1.json")
    if not os.path.exists(goblin_def_path):
        with open(goblin_def_path, "w") as f:
            json.dump({
                "id": "goblin_1", "name": "Goblin", "char": "g", "hp": 30, "max_hp": 30, 
                "ap": 3, "max_ap": 3, "abilities": ["Move", "Pistol Shot"], "behavior": "move_towards_player", # Ensure Move is here
                "description": "A pesky goblin."
            }, f, indent=4)
            print(f"Created dummy entity: {goblin_def_path}")


    editor = Editor(screen)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            editor.handle_input(event)

        editor.update()
        editor.draw()
        
        pygame.display.flip()
        clock.tick(30) # FPS

    pygame.quit()
