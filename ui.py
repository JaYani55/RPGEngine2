import pygame
from config import COLORS, FONT_NAME, FONT_SIZE, TILE_SIZE 
from abilities import Ability 
from typing import Optional, Dict

class BaseInterface:
    def __init__(self, screen):
        self.screen = screen
        try:
            self.font_large = pygame.font.Font(FONT_NAME, FONT_SIZE + 6)
            self.font_normal = pygame.font.Font(FONT_NAME, FONT_SIZE)
            self.font_small = pygame.font.Font(FONT_NAME, FONT_SIZE - 2)
            self.tooltip_font = pygame.font.Font(FONT_NAME, FONT_SIZE - 3) # For ability AP cost tooltips
        except pygame.error as e:
            print(f"Error loading font in BaseInterface: {e}. Using pygame default.")
            self.font_large = pygame.font.Font(None, FONT_SIZE + 10)
            self.font_normal = pygame.font.Font(None, FONT_SIZE + 4)
            self.font_small = pygame.font.Font(None, FONT_SIZE + 2)
            self.tooltip_font = pygame.font.Font(None, FONT_SIZE + 1) 
            
    def draw_text(self, text, font, color, x, y, center=True, screen_ref=None):
        scr = screen_ref if screen_ref else self.screen
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        if center:
            text_rect.center = (x, y)
        else:
            text_rect.topleft = (x, y)
        scr.blit(text_surface, text_rect)

class MainMenu(BaseInterface):
    def __init__(self, screen):
        super().__init__(screen)
        self.options = ["Start Game", "Open Editor", "Quit"]
        self.selected_option = 0
        self.title_color = COLORS.get("ui_text_highlight", (255,255,150))
        self.normal_color = COLORS.get("ui_text", (220,220,220))
        self.selected_color = COLORS.get("yellow", (255,255,0))
        self.bg_color = COLORS.get("ui_background", (30,30,40))

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_option = (self.selected_option - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                if self.options[self.selected_option] == "Start Game":
                    return "map_selection", None 
                elif self.options[self.selected_option] == "Open Editor":
                    return "editor", None
                elif self.options[self.selected_option] == "Quit":
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
        return "main_menu", None # Return tuple for consistency

    def draw(self):
        self.screen.fill(self.bg_color)
        self.draw_text("ASCII Tactical RPG", self.font_large, self.title_color, self.screen.get_width() // 2, 150)

        for i, option in enumerate(self.options):
            color = self.selected_color if i == self.selected_option else self.normal_color
            self.draw_text(option, self.font_normal, color, self.screen.get_width() // 2, 300 + i * 70)

class MapSelectionScreen(BaseInterface):
    def __init__(self, screen):
        super().__init__(screen)
        self.available_maps = []
        self.selected_map_index = 0
        self.title_color = COLORS.get("ui_text_highlight", (255,255,150))
        self.normal_color = COLORS.get("ui_text", (220,220,220))
        self.selected_color = COLORS.get("yellow", (255,255,0))
        self.error_color = COLORS.get("red", (255,0,0))
        self.info_color = COLORS.get("light_grey", (200,200,200))
        self.bg_color = COLORS.get("ui_background", (20,20,30)) # Slightly different bg
        self.load_available_maps()

    def load_available_maps(self):
        from data_manager import list_available_maps # Local import
        self.available_maps = list_available_maps()
        if not self.available_maps:
            print("No maps found in data/maps/. Please create one with the editor.")
        self.selected_map_index = 0

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                if self.available_maps:
                    self.selected_map_index = (self.selected_map_index - 1) % len(self.available_maps)
            elif event.key == pygame.K_DOWN:
                if self.available_maps:
                    self.selected_map_index = (self.selected_map_index + 1) % len(self.available_maps)
            elif event.key == pygame.K_RETURN:
                if self.available_maps:
                    return "game", self.available_maps[self.selected_map_index]
                else:
                    return "main_menu", None 
            elif event.key == pygame.K_ESCAPE:
                return "main_menu", None 
        return "map_selection", None 

    def draw(self):
        self.screen.fill(self.bg_color)
        self.draw_text("Select Map", self.font_large, self.title_color, self.screen.get_width() // 2, 100)

        if not self.available_maps:
            self.draw_text("No maps found in data/maps/", self.font_normal, self.error_color, self.screen.get_width() // 2, 250)
            self.draw_text("Create a map using the Editor first.", self.font_small, self.info_color, self.screen.get_width() // 2, 300)
            self.draw_text("Press ESC to return to Main Menu", self.font_small, self.info_color, self.screen.get_width() // 2, 350)
            return

        for i, map_name in enumerate(self.available_maps):
            color = self.selected_color if i == self.selected_map_index else self.normal_color
            self.draw_text(map_name, self.font_normal, color, self.screen.get_width() // 2, 220 + i * 60)
        
        self.draw_text("Up/Down to select, Enter to start, Esc for Main Menu", self.font_small, self.info_color, self.screen.get_width() // 2, self.screen.get_height() - 70)


class GameUI(BaseInterface):
    def __init__(self, screen):
        super().__init__(screen)
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()

        self.log_area_height = 70  
        self.main_info_panel_height = 110 
        self.ability_bar_total_height = 40 
        self.ability_button_height = 30 
        self.ability_button_width = 90 
        self.ability_button_padding = 5

        # Log Area Rect
        self.log_area_rect = pygame.Rect(0, screen_h - self.log_area_height, screen_w, self.log_area_height)

        # Main Info Panel Rect (above log area)
        self.main_info_panel_rect = pygame.Rect(0, screen_h - self.log_area_height - self.main_info_panel_height, 
                                              screen_w, self.main_info_panel_height)

        # Ability Bar Rect (above main info panel)
        self.ability_bar_rect = pygame.Rect(0, self.main_info_panel_rect.top - self.ability_bar_total_height,
                                          screen_w, self.ability_bar_total_height)
        
        self.ability_buttons_rects = [] # To store rects for click detection
        self.ability_buttons_start_x = 10 # Padding from left
        self.ability_buttons_y = self.ability_bar_rect.top + (self.ability_bar_total_height - self.ability_button_height) // 2

        # End Round Button
        self.end_round_button_width = 100 # Adjusted width
        self.end_round_button_height = 30
        # Positioned in the main info panel, to the right
        self.end_round_button_x = screen_w - self.end_round_button_width - 15 # 15px padding from right
        self.end_round_button_y = self.main_info_panel_rect.top + 10 # 10px from top of panel
        self.end_round_button_rect = pygame.Rect(
            self.end_round_button_x, self.end_round_button_y,
            self.end_round_button_width, self.end_round_button_height
        )
        self.end_round_button_text = "End Turn"
        self.button_font = self.font_small 
        self.button_color = COLORS.get("button_normal", (70, 70, 90))
        self.button_hover_color = COLORS.get("button_hover", (100, 100, 120))
        self.button_text_color = COLORS.get("button_text", (230, 230, 230))


    def draw(self, player, current_turn_entity, game_log, game_state, selected_entity_in_game, active_ability: Ability | None, hovered_ability_info: Optional[Dict[str, Ability]] = None):
        # Draw panel backgrounds
        pygame.draw.rect(self.screen, COLORS.get("ui_background", (20,20,30)), self.log_area_rect)
        pygame.draw.rect(self.screen, COLORS.get("ui_background", (25,25,35)), self.main_info_panel_rect) # Slightly different color
        pygame.draw.rect(self.screen, COLORS.get("ui_background", (20,20,30)), self.ability_bar_rect)

        # Borders for panels
        border_color = COLORS.get("ui_border", (80,80,100))
        pygame.draw.rect(self.screen, border_color, self.log_area_rect, 1)
        pygame.draw.rect(self.screen, border_color, self.main_info_panel_rect, 1)
        pygame.draw.rect(self.screen, border_color, self.ability_bar_rect, 1)

        # Draw Game Log (simple example)
        log_start_y = self.log_area_rect.top + 5
        for i, entry in enumerate(game_log[-3:]): # Show last 3 log messages
            self.draw_text(entry['message'], self.font_small, COLORS.get("text_dim"), 5, log_start_y + i * (self.font_small.get_linesize() -2), center=False)

        # Draw Player/Entity Info in Main Panel
        info_x = 10
        info_y_start = self.main_info_panel_rect.top + 10
        line_height = self.font_normal.get_linesize()

        display_entity = selected_entity_in_game if selected_entity_in_game else player # Show player if nothing selected
        if display_entity:
            self.draw_text(f"{display_entity.name}", self.font_normal, COLORS.get("ui_text_highlight"), info_x, info_y_start, center=False)
            self.draw_text(f"HP: {display_entity.hp}/{display_entity.max_hp}", self.font_small, COLORS.get("ui_text"), info_x, info_y_start + line_height, center=False)
            self.draw_text(f"AP: {display_entity.current_ap}/{display_entity.ap}", self.font_small, COLORS.get("ui_text"), info_x, info_y_start + line_height * 2, center=False)
            # Add more info as needed (defense, status, etc.)

        # Draw Current Turn Entity
        if current_turn_entity:
            turn_text = f"Turn: {current_turn_entity.name}"
            self.draw_text(turn_text, self.font_small, COLORS.get("yellow"), self.main_info_panel_rect.centerx, self.main_info_panel_rect.top + 5, center=True)

        # Draw Ability Bar
        self.ability_buttons_rects.clear() # Clear old rects
        if player and player.abilities:
            for i, ability in enumerate(player.abilities):
                button_rect = pygame.Rect(
                    self.ability_buttons_start_x + i * (self.ability_button_width + self.ability_button_padding),
                    self.ability_buttons_y,
                    self.ability_button_width,
                    self.ability_button_height
                )
                self.ability_buttons_rects.append(button_rect)                # Button color based on selection or AP
                btn_color = COLORS.get("button_normal")
                if active_ability and active_ability.id_name == ability.id_name:
                    btn_color = COLORS.get("button_hover") # Highlight if active
                elif player.current_ap < ability.ap_cost:
                    btn_color = COLORS.get("dark_grey") # Grey out if not enough AP
                
                pygame.draw.rect(self.screen, btn_color, button_rect)
                ability_text = f"{ability.name[:10]} ({i+1})" # Show first 10 chars + hotkey
                self.draw_text(ability_text, self.font_small, COLORS.get("button_text"), button_rect.centerx, button_rect.centery, center=True)                # Display AP cost tooltip on hover for abilities
                if hovered_ability_info and hovered_ability_info['ability'].id_name == ability.id_name:
                    ap_cost_text = f"AP: {hovered_ability_info['ap_cost']}"
                    text_surface = self.tooltip_font.render(ap_cost_text, True, COLORS.get("white"), COLORS.get("black"))
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    tooltip_rect = text_surface.get_rect(midleft=(mouse_x + 10, mouse_y - 10))
                    
                    # Ensure tooltip stays on screen
                    if tooltip_rect.right > self.screen.get_width(): tooltip_rect.right = self.screen.get_width() - 5
                    if tooltip_rect.top < 0 : tooltip_rect.top = 5

                    pygame.draw.rect(self.screen, COLORS.get("black"), tooltip_rect.inflate(4,4))
                    self.screen.blit(text_surface, tooltip_rect)


        # Draw End Round Button (only if it's player's turn)
        if game_state == "player_turn":
            mouse_pos = pygame.mouse.get_pos()
            button_c = self.button_hover_color if self.end_round_button_rect.collidepoint(mouse_pos) else self.button_color
            pygame.draw.rect(self.screen, button_c, self.end_round_button_rect)
            self.draw_text(self.end_round_button_text, self.button_font, self.button_text_color,
                           self.end_round_button_rect.centerx, self.end_round_button_rect.centery, center=True)
        
    def wrap_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        lines.append(current_line.strip())
        return lines

    def get_clicked_ability(self, click_pos, player_abilities: list[Ability]) -> Ability | None:
        if not player_abilities: return None
        for i, rect in enumerate(self.ability_buttons_rects):
            if rect.collidepoint(click_pos):
                if i < len(player_abilities):
                    return player_abilities[i]
        return None

    def get_hovered_ability(self, hover_pos, player_abilities: list[Ability]) -> Ability | None:
        """Checks if the mouse is hovering over an ability button."""
        if not player_abilities: return None
        for i, rect in enumerate(self.ability_buttons_rects):
            if rect.collidepoint(hover_pos):
                if i < len(player_abilities):
                    return player_abilities[i]
        return None

    def get_clicked_button(self, click_pos, game_state_is_player_turn) -> str | None:
        if game_state_is_player_turn:
            if self.end_round_button_rect.collidepoint(click_pos):
                return "end_round"
        return None
    
    def handle_log_scroll(self, event, num_log_messages):
        max_scroll = max(0, num_log_messages - ((self.log_area_rect.height - 10) // self.log_line_height))
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.log_area_rect.collidepoint(event.pos):
                if event.button == 4:  # Scroll up
                    self.log_scroll_offset = min(self.log_scroll_offset + 1, max_scroll)
                elif event.button == 5:  # Scroll down
                    self.log_scroll_offset = max(0, self.log_scroll_offset - 1)
