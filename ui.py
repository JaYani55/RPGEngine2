import pygame
from config import COLORS, FONT_NAME, FONT_SIZE, TILE_SIZE # Added TILE_SIZE
from abilities import Ability # Added Ability

class BaseInterface:
    def __init__(self, screen):
        self.screen = screen
        try:
            self.font_large = pygame.font.Font(FONT_NAME, FONT_SIZE + 28) # e.g. 36+28 = 64
            self.font_medium = pygame.font.Font(FONT_NAME, FONT_SIZE + 12) # e.g. 36+12 = 48
            self.font_small = pygame.font.Font(FONT_NAME, FONT_SIZE)      # e.g. 36
            self.font_tiny = pygame.font.Font(FONT_NAME, FONT_SIZE - 6)   # e.g. 30
        except pygame.error as e:
            print(f"Error loading font {FONT_NAME}: {e}. Using pygame default font.")
            self.font_large = pygame.font.Font(None, 74)
            self.font_medium = pygame.font.Font(None, 50)
            self.font_small = pygame.font.Font(None, 36)
            self.font_tiny = pygame.font.Font(None, 24)

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
            self.draw_text(option, self.font_medium, color, self.screen.get_width() // 2, 300 + i * 70)

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
            self.draw_text("No maps found in data/maps/", self.font_medium, self.error_color, self.screen.get_width() // 2, 250)
            self.draw_text("Create a map using the Editor first.", self.font_small, self.info_color, self.screen.get_width() // 2, 300)
            self.draw_text("Press ESC to return to Main Menu", self.font_small, self.info_color, self.screen.get_width() // 2, 350)
            return

        for i, map_name in enumerate(self.available_maps):
            color = self.selected_color if i == self.selected_map_index else self.normal_color
            self.draw_text(map_name, self.font_medium, color, self.screen.get_width() // 2, 220 + i * 60)
        
        self.draw_text("Up/Down to select, Enter to start, Esc for Main Menu", self.font_small, self.info_color, self.screen.get_width() // 2, self.screen.get_height() - 70)


class GameUI(BaseInterface):
    def __init__(self, screen):
        super().__init__(screen)
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()

        # Define heights for different sections from bottom up
        self.log_area_height = 70  # For game log, e.g. 3-4 lines
        self.main_info_panel_height = 110 # For player stats, selected entity
        self.ability_bar_total_height = 40 # Includes button height + padding for the bar area
        self.ability_button_height = 30 # Actual button height
        self.ability_button_width = 90 # Width of ability buttons

        # 1. Log Area (at the very bottom of the screen)
        self.log_area_rect = pygame.Rect(
            0, screen_h - self.log_area_height,
            screen_w, self.log_area_height
        )

        # 2. Main Info Panel (sits above the log area)
        self.main_info_panel_rect = pygame.Rect(
            0, self.log_area_rect.top - self.main_info_panel_height,
            screen_w, self.main_info_panel_height
        )

        # 3. Ability Bar (sits above the main info panel)
        # Y position for the top of the ability bar area
        self.ability_bar_y_position = self.main_info_panel_rect.top - self.ability_bar_total_height
        
        # Colors
        self.main_panel_bg_color = COLORS.get("ui_background", (40,40,50, 220)) # For main info panel
        self.log_panel_bg_color = COLORS.get("log_area_bg", (25,25,35, 230)) # Darker for log panel
        self.ability_bar_bg_color = COLORS.get("ability_bar_bg", (30,30,40, 210)) # BG for ability bar area

        self.text_color = COLORS.get("ui_text", (220,220,220))
        self.selected_text_color = COLORS.get("yellow", (255,255,0))
        self.hp_color = COLORS.get("green", (0,255,0))
        self.ap_color = COLORS.get("blue", (100,100,255))
        self.turn_color = COLORS.get("yellow", (255,255,0))
        self.description_color = COLORS.get("cyan", (0, 200, 200))
        self.ability_button_color = COLORS.get("ui_button", (70,70,90))
        self.ability_button_hover_color = COLORS.get("ui_button_hover", (100,100,120))
        self.ability_button_text_color = COLORS.get("ui_text", (220,220,220))
        self.border_color = COLORS.get("ui_border", (80,80,100))

        self.ability_buttons = [] # List of tuples: (pygame.Rect, Ability)
        self.log_scroll_offset = 0
        self.log_line_height = self.font_tiny.get_height() + 4

    def draw(self, player, current_turn_entity, game_log, game_state, selected_entity_in_game, active_ability: Ability | None):
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height() # Define screen_h here

        # --- 1. Log Area (Bottom) ---
        log_panel_surface = pygame.Surface(self.log_area_rect.size, pygame.SRCALPHA)
        log_panel_surface.fill(self.log_panel_bg_color)
        self.screen.blit(log_panel_surface, self.log_area_rect.topleft)
        pygame.draw.line(self.screen, self.border_color, self.log_area_rect.topleft, self.log_area_rect.topright, 2)

        log_render_start_x = self.log_area_rect.left + 10
        log_render_start_y = self.log_area_rect.top + 8
        max_lines_in_log_view = (self.log_area_rect.height - 16) // self.log_line_height # Padding top/bottom
        
        start_index = max(0, len(game_log) - max_lines_in_log_view - self.log_scroll_offset)
        end_index = max(0, len(game_log) - self.log_scroll_offset)
        visible_log_messages = game_log[start_index:end_index]

        current_log_y = log_render_start_y
        for message in visible_log_messages: # Display oldest of visible messages at top
            if current_log_y + self.log_line_height <= self.log_area_rect.bottom - 8:
                self.draw_text(message, self.font_tiny, self.text_color, log_render_start_x, current_log_y, center=False)
                current_log_y += self.log_line_height
            else:
                break

        # --- 2. Main Info Panel (Middle) ---
        info_panel_surface = pygame.Surface(self.main_info_panel_rect.size, pygame.SRCALPHA)
        info_panel_surface.fill(self.main_panel_bg_color)
        self.screen.blit(info_panel_surface, self.main_info_panel_rect.topleft)
        pygame.draw.line(self.screen, self.border_color, self.main_info_panel_rect.topleft, self.main_info_panel_rect.topright, 2)

        info_base_y = self.main_info_panel_rect.top + 10
        line_height_info = self.font_small.get_height() + 3 # Based on font_small
        padding_x = 20

        # Player Stats (Left side)
        if player:
            self.draw_text(f"{player.name}", self.font_small, self.text_color, padding_x, info_base_y, center=False)
            self.draw_text(f"HP: {player.hp}/{player.max_hp}", self.font_small, self.hp_color, padding_x, info_base_y + line_height_info, center=False)
            self.draw_text(f"AP: {player.ap}/{player.max_ap}", self.font_small, self.ap_color, padding_x, info_base_y + line_height_info * 2, center=False)

        # Current Turn Entity (Center-ish)
        turn_text_x = screen_w // 3 + 20
        if current_turn_entity:
            turn_display_text = f"Turn: {current_turn_entity.name}"
            if current_turn_entity == player:
                turn_display_text += " (YOU)"
            self.draw_text(turn_display_text, self.font_small, self.turn_color, turn_text_x, info_base_y, center=False)

        # Selected Entity Info (Right side)
        selected_info_x_start = screen_w // 2 + 60
        if selected_entity_in_game:
            self.draw_text(f"Selected: {selected_entity_in_game.name}", self.font_small, self.selected_text_color, selected_info_x_start, info_base_y, center=False)
            self.draw_text(f"HP: {selected_entity_in_game.hp}/{selected_entity_in_game.max_hp}", self.font_small, self.hp_color, selected_info_x_start, info_base_y + line_height_info, center=False)
            self.draw_text(f"AP: {selected_entity_in_game.ap}/{selected_entity_in_game.max_ap}", self.font_small, self.ap_color, selected_info_x_start + 130, info_base_y + line_height_info, center=False)
            
            if selected_entity_in_game.description:
                desc_text = f"Desc: {selected_entity_in_game.description}"
                max_desc_width = screen_w - selected_info_x_start - 15 
                desc_y_start = info_base_y + line_height_info * 2
                
                wrapped_lines = self.wrap_text(desc_text, self.font_tiny, max_desc_width)
                for i, line in enumerate(wrapped_lines):
                    if desc_y_start + (i * (self.font_tiny.get_height() + 2)) < self.main_info_panel_rect.bottom - 5:
                         self.draw_text(line, self.font_tiny, self.description_color, selected_info_x_start, desc_y_start + (i * (self.font_tiny.get_height() + 2)), center=False)
                    else:
                        break # Stop if text overflows panel

        # --- 3. Ability Bar (Top of UI elements, below game map) ---
        self.ability_buttons.clear()
        if game_state == "player_turn" and player and current_turn_entity == player:
            # Draw ability bar background
            ability_bar_rect = pygame.Rect(0, self.ability_bar_y_position, screen_w, self.ability_bar_total_height)
            ability_bar_surface = pygame.Surface(ability_bar_rect.size, pygame.SRCALPHA)
            ability_bar_surface.fill(self.ability_bar_bg_color)
            self.screen.blit(ability_bar_surface, ability_bar_rect.topleft)
            pygame.draw.line(self.screen, self.border_color, ability_bar_rect.topleft, ability_bar_rect.topright, 2)

            mouse_pos = pygame.mouse.get_pos()
            ability_start_x = 20
            button_padding = 10
            # Center buttons vertically within the ability_bar_total_height
            button_y_pos = self.ability_bar_y_position + (self.ability_bar_total_height - self.ability_button_height) / 2

            for i, ability in enumerate(player.abilities):
                if ability.name == "Move": continue
                
                button_rect = pygame.Rect(
                    ability_start_x + i * (self.ability_button_width + button_padding),
                    button_y_pos,
                    self.ability_button_width,
                    self.ability_button_height
                )
                self.ability_buttons.append((button_rect, ability))

                color = self.ability_button_hover_color if button_rect.collidepoint(mouse_pos) else self.ability_button_color
                if active_ability and active_ability.name == ability.name:
                    color = self.selected_text_color 
                
                pygame.draw.rect(self.screen, color, button_rect, border_radius=5)
                # Draw ability name and AP cost on button
                ability_text_surface = self.font_tiny.render(f"{ability.name} ({ability.ap_cost}AP)", True, self.ability_button_text_color)
                ability_text_rect = ability_text_surface.get_rect(center=button_rect.center)
                self.screen.blit(ability_text_surface, ability_text_rect)

        # Game Over / Victory Message (drawn on top of everything else)
        if game_state == "game_over_player_lose":
            self.draw_text("GAME OVER", self.font_large, COLORS.get("red", (255,50,50)), screen_w // 2, screen_h // 2 - 50)
            self.draw_text("Press ESC to return to menu", self.font_small, self.text_color, screen_w // 2, screen_h // 2 + 20)
        elif game_state == "game_over_player_win":
            self.draw_text("VICTORY!", self.font_large, COLORS.get("green", (50,255,50)), screen_w // 2, screen_h // 2 - 50)
            self.draw_text("Press ESC to return to menu", self.font_small, self.text_color, screen_w // 2, screen_h // 2 + 20)

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

    def get_clicked_ability(self, click_pos) -> Ability | None:
        """Checks if a click position collides with any ability button."""
        for rect, ability in self.ability_buttons:
            if rect.collidepoint(click_pos):
                return ability
        return None

    def handle_log_scroll(self, event, num_log_messages):
        max_scroll = max(0, num_log_messages - ((self.log_area_rect.height - 10) // self.log_line_height))
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.log_area_rect.collidepoint(event.pos):
                if event.button == 4:  # Scroll up
                    self.log_scroll_offset = min(self.log_scroll_offset + 1, max_scroll)
                elif event.button == 5:  # Scroll down
                    self.log_scroll_offset = max(0, self.log_scroll_offset - 1)
