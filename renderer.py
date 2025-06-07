import pygame
from config import TILE_SIZE, FONT_NAME, FONT_SIZE, COLORS
from abilities import Ability # For type hinting selected_ability

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        try:
            self.font = pygame.font.Font(FONT_NAME, FONT_SIZE)
            self.small_font = pygame.font.Font(FONT_NAME, FONT_SIZE - 4) # For height numbers
        except pygame.error as e:
            print(f"Error loading font: {e}. Using default font.")
            self.font = pygame.font.Font(None, FONT_SIZE + 4) # Pygame default font
            self.small_font = pygame.font.Font(None, FONT_SIZE)

        self.tile_colors = {
            "#": COLORS.get("wall", (100, 100, 100)),
            ".": COLORS.get("floor", (50, 50, 50)),
            "~": COLORS.get("water", (0, 0, 255)),
        }
        self.entity_colors = {
            "player": COLORS.get("player", (0, 255, 0)),
            "enemy": COLORS.get("enemy", (255, 0, 0)),
            "npc_friendly": COLORS.get("npc_friendly", (0, 255, 255)),
            "default": COLORS.get("text_default", (200, 200, 200)),
        }
        self.highlight_colors = {
            "move": COLORS.get("highlight_move", (0, 100, 255, 120)), # Adjusted alpha
            "ability": COLORS.get("highlight_ability", (255, 150, 0, 120)), # New for ability range
            "aoe_effect": COLORS.get("highlight_aoe", (255, 100, 0, 70)), # For AoE preview
            "selected": COLORS.get("highlight_selected", (255, 255, 0, 100)),
            "current_turn": COLORS.get("highlight_current_turn", (200, 200, 200, 80))
        }
        self.map_render_offset_y = 0 # Initialize map_render_offset_y, game.py uses this

    def _get_entity_color(self, entity):
        if entity.behavior == "player_controlled":
            return self.entity_colors["player"]
        # Basic check for enemy (can be improved with factions or specific tags)
        elif entity.behavior in ["move_towards_player", "run_away_from_player"]:
            return self.entity_colors["enemy"]
        # Add more types like "npc_friendly" if behaviors are expanded
        return self.entity_colors["default"]

    def draw_game_state(self, game_engine, selected_entity, highlighted_tiles_move, 
                        highlighted_tiles_ability, action_mode, selected_ability: Ability | None):
        game_map = game_engine.game_map
        entities = game_engine.entities
        current_turn_entity = game_engine.get_current_turn_entity()

        # Calculate map rendering offset if map is larger than screen
        # For now, simple top alignment, but can be expanded for scrolling
        # self.map_render_offset_y = 0 # Assuming no scrolling for now, or set by Game class if needed

        # 1. Draw Map Tiles and Heights
        if not game_map:
            return
        for y, row in enumerate(game_map.tiles):
            for x, tile_char in enumerate(row):
                tile_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE + self.map_render_offset_y, TILE_SIZE, TILE_SIZE)
                map_height = game_map.heightmap[y][x]
                
                # Base tile color
                base_color = self.tile_colors.get(tile_char, COLORS.get("floor_dark", (30,30,30)))
                # Slightly adjust color by height for pseudo-3D effect
                height_color_factor = max(0.7, min(1.3, 1 + (map_height - 2) * 0.1))
                adjusted_color = tuple(min(255, int(c * height_color_factor)) for c in base_color)
                pygame.draw.rect(self.screen, adjusted_color, tile_rect)

                # Render ASCII char for the tile
                char_surface = self.font.render(tile_char, True, COLORS.get("text_light", (180,180,180)))
                char_rect = char_surface.get_rect(center=tile_rect.center)
                self.screen.blit(char_surface, char_rect)

                # Render height number (optional, can be toggled)
                # height_text = self.small_font.render(str(map_height), True, COLORS.get("text_dim",(120,120,120)))
                # self.screen.blit(height_text, (tile_rect.x + 2, tile_rect.y + 2))

        # 2. Draw Highlights (Move, Ability Ranges, AoE)
        highlight_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)

        if action_mode == "move_target" and selected_entity: # Changed from "move"
            highlight_surface.fill(self.highlight_colors["move"])
            for pos_x, pos_y in highlighted_tiles_move:
                self.screen.blit(highlight_surface, (pos_x * TILE_SIZE, pos_y * TILE_SIZE + self.map_render_offset_y))
        
        elif action_mode == "ability_target" and selected_entity and selected_ability:
            # Highlight direct targetable tiles for the ability
            highlight_surface.fill(self.highlight_colors["ability"])
            for pos_x, pos_y in highlighted_tiles_ability:
                self.screen.blit(highlight_surface, (pos_x * TILE_SIZE, pos_y * TILE_SIZE + self.map_render_offset_y))

            # If the ability has an AoE, preview it around the current mouse/hovered tile (if available)
            # This part is more complex as it needs mouse position. 
            # For now, let's assume highlighted_tiles_ability are the centers of potential AoEs.
            # If an ability is selected and has an AoE radius, we can show the AoE for all valid target cells.
            if selected_ability.effect_radius > 0:
                aoe_highlight_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                aoe_highlight_surface.fill(self.highlight_colors["aoe_effect"]) # A different color/alpha for AoE area
                
                for center_x, center_y in highlighted_tiles_ability:
                    # Draw AoE around each potential target center
                    for r_x in range(-selected_ability.effect_radius, selected_ability.effect_radius + 1):
                        for r_y in range(-selected_ability.effect_radius, selected_ability.effect_radius + 1):
                            # Example: square AoE. For circle/diamond, add distance check.
                            # if abs(r_x) + abs(r_y) > selected_ability.effect_radius: continue # Manhattan shape
                            aoe_tile_x, aoe_tile_y = center_x + r_x, center_y + r_y
                            if game_map.is_valid(aoe_tile_x, aoe_tile_y):
                                # Avoid double-highlighting the center tile too much, or use a combined effect
                                if not (aoe_tile_x == center_x and aoe_tile_y == center_y):
                                    self.screen.blit(aoe_highlight_surface, (aoe_tile_x * TILE_SIZE, aoe_tile_y * TILE_SIZE + self.map_render_offset_y))

        # 3. Draw Entities
        for entity in sorted(entities, key=lambda e: e.y): # Draw bottom entities first for overlap
            if entity.hp > 0:
                entity_color = self._get_entity_color(entity)
                char_surface = self.font.render(entity.char, True, entity_color)
                
                entity_map_height = game_map.get_height(entity.x, entity.y)
                height_visual_offset = entity_map_height * 2 
                
                entity_rect_center_x = entity.x * TILE_SIZE + TILE_SIZE // 2
                entity_rect_center_y = entity.y * TILE_SIZE + TILE_SIZE // 2 - height_visual_offset + self.map_render_offset_y
                
                char_rect = char_surface.get_rect(center=(entity_rect_center_x, entity_rect_center_y))

                # Highlight for current turn entity
                if entity == current_turn_entity:
                    turn_highlight_rect = pygame.Rect(entity.x * TILE_SIZE, entity.y * TILE_SIZE + self.map_render_offset_y, TILE_SIZE, TILE_SIZE)
                    s = pygame.Surface((TILE_SIZE,TILE_SIZE), pygame.SRCALPHA)
                    s.fill(self.highlight_colors["current_turn"]) 
                    self.screen.blit(s, turn_highlight_rect.topleft)

                # Highlight for selected entity (different from current turn, e.g. player inspecting)
                if entity == selected_entity:
                    select_highlight_rect = pygame.Rect(entity.x * TILE_SIZE, entity.y * TILE_SIZE + self.map_render_offset_y, TILE_SIZE, TILE_SIZE)
                    s = pygame.Surface((TILE_SIZE,TILE_SIZE), pygame.SRCALPHA)
                    s.fill(self.highlight_colors["selected"]) 
                    self.screen.blit(s, select_highlight_rect.topleft)
                    border_rect = char_rect.inflate(4,4)
                    pygame.draw.rect(self.screen, self.highlight_colors["selected"], border_rect, 1)

                self.screen.blit(char_surface, char_rect)

                # Optional: Draw HP bar or AP count near entity
                # hp_text = self.small_font.render(f"HP:{entity.hp}", True, entity_color)
                # self.screen.blit(hp_text, (char_rect.left, char_rect.bottom + 1))
