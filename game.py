import pygame
from renderer import Renderer
from engine import GameEngine, GameMap, Entity # Added Entity
from ui import GameUI
from data_manager import load_map_data
from utils import pixel_to_grid # Added pixel_to_grid
from config import TILE_SIZE # Added TILE_SIZE
from abilities import Ability # Added Ability

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.renderer: Renderer | None = None
        self.engine: GameEngine | None = None
        self.ui: GameUI | None = None
        
        self.player: Entity | None = None
        # self.npcs = [] # May not be needed if engine.entities is primary store
        
        self.is_running = False
        self._initialized = False
        self.current_map_name = None
        
        # Game-specific state for player interaction
        self.selected_entity: Entity | None = None
        self.highlighted_tiles_move = []
        self.highlighted_tiles_ability = [] # Renamed from highlighted_tiles_attack
        self.action_mode = None # e.g., "select", "move_target", "ability_target"
        self.selected_ability: Ability | None = None # Store the selected ability object
        self.game_messages = [] # List of dicts: {'text': "message", 'timer': 60}
        self.game_state = "loading" # e.g., loading, player_turn, npc_turn, game_over

    def load_game_state(self, map_file_name):
        self.reset() # Ensure clean state before loading
        self.game_state = "loading"
        self.current_map_name = map_file_name
        print(f"Game: Attempting to load map: {map_file_name}")
        
        map_data = load_map_data(map_file_name)

        if not map_data:
            print(f"Error: Failed to load map data for {map_file_name}")
            self.set_message(f"Error: Could not load map {map_file_name}", 180)
            self._initialized = False
            self.is_running = False
            self.game_state = "load_error"
            return

        try:
            game_map_obj = GameMap(map_data['tiles'], map_data['heightmap']) # Changed 'heights' to 'heightmap'
            self.engine = GameEngine(game_map_obj)
            
            self.engine.initialize_entities_from_map_data(map_data.get('entities_on_map', []))

            self.player = self.engine.get_player()

            if not self.player:
                print("Error: Player entity not found after engine initialization.")
                self.set_message("Error: Player not found in map data.", 180)
                self._initialized = False
                self.is_running = False
                self.game_state = "load_error"
                return

            self.renderer = Renderer(self.screen)
            self.ui = GameUI(self.screen)
            
            self._initialized = True
            self.is_running = True
            self.engine.start_game() 
            self.game_state = self.engine.get_current_game_state() 
            self.set_message(f"Loaded {map_file_name}. {self.player.name}'s turn!", 120)
            # Auto-select player at game start if it's their turn
            if self.game_state == "player_turn":
                self.selected_entity = self.player
                self.action_mode = "select" # Default to select mode
                if self.player:
                    self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
            print(f"Game state loaded successfully for map: {self.current_map_name}. Player: {self.player.name}")

        except Exception as e:
            print(f"Error during game state loading for {map_file_name}: {e}")
            import traceback
            traceback.print_exc()
            self.set_message(f"Critical Error initializing game: {e}", 180)
            self._initialized = False
            self.is_running = False
            self.game_state = "critical_error"
            # Clean up partially initialized components
            self.engine = None
            self.renderer = None
            self.ui = None
            self.player = None

    def handle_input(self, event):
        if not self._initialized or not self.is_running or self.game_state == "loading":
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # If in targeting mode, ESC cancels targeting
                if self.action_mode in ["ability_target", "move_target"]:
                    self.set_message("Action cancelled.", 60)
                    self.action_mode = "select" # Go back to select mode
                    self.selected_ability = None
                    self.highlighted_tiles_ability = []
                    # Keep move highlights if player is selected
                    if self.selected_entity == self.player and self.player:
                         self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                    else:
                        self.highlighted_tiles_move = []
                else: # Otherwise, ESC closes the game screen
                    self.is_running = False 
                    print("Game: ESC pressed, stopping game.")
                return

        # Player turn specific input
        if self.game_state == "player_turn" and self.engine and self.player:
            current_player_entity = self.engine.get_current_turn_entity()
            if current_player_entity != self.player: # Should not happen, but good check
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                grid_x, grid_y = pixel_to_grid(mouse_pos[0], mouse_pos[1] - self.renderer.map_render_offset_y if self.renderer else 0, TILE_SIZE) # Adjust for map offset

                # 1. Check for Ability Button Clicks (only if UI and player exist)
                if self.ui and self.player:
                    clicked_ability = self.ui.get_clicked_ability(mouse_pos)
                    if clicked_ability:
                        if self.player.ap >= clicked_ability.ap_cost:
                            self.selected_ability = clicked_ability
                            self.action_mode = "ability_target"
                            self.highlighted_tiles_move = [] # Clear move highlights
                            self.highlighted_tiles_ability = self.engine.get_ability_range_tiles(self.player, self.selected_ability)
                            self.set_message(f"Selected {clicked_ability.name}. Click target.", 90)
                        else:
                            self.set_message(f"Not enough AP for {clicked_ability.name} (needs {clicked_ability.ap_cost}).", 90)
                        return # Input handled

                # 2. Handle Map Clicks (Selection, Movement, Ability Targeting)
                if self.engine.game_map.is_valid(grid_x, grid_y):
                    if self.action_mode == "ability_target" and self.selected_ability:
                        if (grid_x, grid_y) in self.highlighted_tiles_ability:
                            success, message = self.engine.handle_player_action(
                                action_type="ability", 
                                target_pos=(grid_x, grid_y), 
                                ability_to_use=self.selected_ability
                            )
                            self.set_message(message, 90)
                            if success:
                                # Reset after successful action
                                self.action_mode = "select"
                                self.selected_ability = None
                                self.highlighted_tiles_ability = []
                                if self.player and self.player.hp > 0 and self.engine.get_current_turn_entity() == self.player:
                                    self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                                else:
                                    self.highlighted_tiles_move = [] # Player turn might have ended
                                # Update selected entity if player moved or something changed
                                self.selected_entity = self.player 
                        else:
                            self.set_message("Target out of ability range or invalid.", 60)
                    
                    elif self.action_mode == "move_target": # Or a general "select" mode that implies move
                        if (grid_x, grid_y) in self.highlighted_tiles_move:
                            success, message = self.engine.handle_player_action(action_type="move", target_pos=(grid_x, grid_y))
                            self.set_message(message, 90)
                            if success:
                                self.action_mode = "select" # Back to select after move
                                if self.player and self.player.hp > 0 and self.engine.get_current_turn_entity() == self.player:
                                    self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                                else:
                                     self.highlighted_tiles_move = []
                                self.selected_entity = self.player # Keep player selected
                        else:
                            # Clicked on map but not a valid move tile, try selecting entity instead
                            entities_at_click = self.engine.get_entities_at(grid_x, grid_y)
                            if entities_at_click:
                                self.selected_entity = entities_at_click[0]
                                self.action_mode = "select"
                                self.highlighted_tiles_ability = []
                                self.selected_ability = None
                                if self.selected_entity == self.player and self.player:
                                    self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                                else:
                                    self.highlighted_tiles_move = []
                                self.set_message(f"Selected {self.selected_entity.name}.", 60)
                            else: # Clicked empty tile not in move range
                                self.set_message("Empty tile. Select an action or entity.", 60)
                                self.selected_entity = None # Deselect if clicked empty space
                                self.action_mode = "select"
                                self.highlighted_tiles_move = []
                                self.highlighted_tiles_ability = []

                    elif self.action_mode == "select" or self.action_mode is None:
                        entities_at_click = self.engine.get_entities_at(grid_x, grid_y)
                        if entities_at_click:
                            self.selected_entity = entities_at_click[0]
                            self.set_message(f"Selected {self.selected_entity.name}.", 60)
                            self.highlighted_tiles_ability = [] # Clear ability highlights
                            self.selected_ability = None
                            if self.selected_entity == self.player and self.player and self.engine.get_current_turn_entity() == self.player:
                                self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                                self.action_mode = "move_target" # Implicitly allow moving selected player
                            else:
                                self.highlighted_tiles_move = []
                                self.action_mode = "select" # Just select for non-player or non-turn entities
                        else: # Clicked on empty tile
                            if self.selected_entity == self.player and self.player and (grid_x, grid_y) in self.highlighted_tiles_move:
                                # If player is selected and clicks a valid move tile, move them
                                success, message = self.engine.handle_player_action(action_type="move", target_pos=(grid_x, grid_y))
                                self.set_message(message, 90)
                                if success:
                                    if self.player.hp > 0 and self.engine.get_current_turn_entity() == self.player:
                                        self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                                    else:
                                        self.highlighted_tiles_move = []
                                    # self.selected_entity remains player
                            else:
                                self.selected_entity = None
                                self.action_mode = "select"
                                self.highlighted_tiles_move = []
                                self.highlighted_tiles_ability = []
                                self.selected_ability = None
                                self.set_message("Selected empty tile.", 60)
                else: # Click outside map (potentially on UI elements not handled by buttons yet)
                    pass # Could add general UI click detection here if needed

            # Keyboard shortcuts for actions
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: # End turn
                    self.set_message("Player ends turn.", 60)
                    self.engine.end_player_turn()
                    self.game_state = self.engine.get_current_game_state()
                    self.selected_entity = None 
                    self.action_mode = None
                    self.highlighted_tiles_move = []
                    self.highlighted_tiles_ability = []
                    self.selected_ability = None
                    # If next turn is player (e.g. solo play or bug), re-select player
                    if self.engine.get_current_turn_entity() == self.player and self.player:
                        self.selected_entity = self.player
                        self.action_mode = "select"
                        self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)

                # Example: Press 'M' to explicitly enter Move mode if player selected
                elif event.key == pygame.K_m and self.selected_entity == self.player and self.player:
                    self.action_mode = "move_target"
                    self.selected_ability = None
                    self.highlighted_tiles_ability = []
                    self.highlighted_tiles_move = self.engine.get_valid_moves(self.player)
                    self.set_message("Move mode. Click a highlighted tile to move.", 90)

    def update(self):
        if not self._initialized or not self.is_running:
            return

        # Update game messages timer
        new_messages = []
        for msg in self.game_messages:
            msg['timer'] -= 1
            if msg['timer'] > 0:
                new_messages.append(msg)
        self.game_messages = new_messages

        if self.engine:
            if self.game_state not in ["game_over_player_win", "game_over_player_lose", "load_error", "critical_error"]:
                self.engine.update() # Engine handles its internal state, NPC turns, AP regen etc.
                self.game_state = self.engine.get_current_game_state()

            if self.game_state == "game_over_player_win":
                self.set_message("Victory! All enemies defeated!", -1) # Persistent
                # Potentially stop further updates or allow ESC to exit
            elif self.game_state == "game_over_player_lose":
                self.set_message("Defeat! Player has fallen!", -1) # Persistent
                # Potentially stop further updates or allow ESC to exit
        
        # If game over, is_running might be set to false after a delay or by player action
        if self.game_state in ["game_over_player_win", "game_over_player_lose"] and self.is_running:
            # Could add a timer here before automatically setting self.is_running = False
            # Or wait for ESC
            pass


    def draw(self):
        self.screen.fill((0, 0, 0)) # Clear screen
        if not self.is_initialized():
            # Potentially show a loading screen or message
            return

        # Draw map, entities, etc.
        self.renderer.draw_game_state(
            self.engine,
            self.selected_entity,
            self.highlighted_tiles_move,
            self.highlighted_tiles_ability,
            self.action_mode,
            self.selected_ability
        )

        # Draw UI elements
        # Signature from ui.py:
        # def draw(self, player, current_turn_entity, messages, game_state, selected_entity_in_game, active_ability: Ability | None):
        self.ui.draw(
            self.engine.player,                     # player
            self.engine.get_current_turn_entity(),  # current_turn_entity
            self.engine.game_log,                   # messages (this is game_log, a list of strings)
            self.engine.game_state,                 # game_state
            self.selected_entity,                   # selected_entity_in_game
            self.selected_ability                   # active_ability
        )

        # Draw game messages (temporary on-screen messages like Victory/Defeat)
        # This was previously handled by game_message, but ui.py now handles game_state messages
        # if self.game_message:
        #     text_surface = self.font.render(self.game_message["text"], True, (255, 255, 255))
        #     text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        #     pygame.draw.rect(self.screen, (0,0,0,150), text_rect.inflate(20,20)) # Semi-transparent background
        #     self.screen.blit(text_surface, text_rect)

        pygame.display.flip()

    def reset(self):
        print("Game: Resetting game state.")
        self.renderer = None
        self.engine = None
        self.ui = None
        self.player = None
        # self.npcs = []
        self.is_running = False
        self._initialized = False
        self.current_map_name = None
        self.selected_entity = None
        self.highlighted_tiles_move = []
        self.highlighted_tiles_ability = [] # Use new name
        self.action_mode = None
        self.selected_ability = None # Reset selected ability
        self.game_messages = []
        self.game_state = "uninitialized"

    def is_over(self):
        # This is called by main.py to decide whether to transition away from Game state
        return not self.is_running

    def is_initialized(self):
        return self._initialized

    def set_message(self, text, duration=90): # duration -1 for persistent
        print(f"Game Message: {text} (duration {duration})")
        
        # If the new message is persistent
        if duration == -1:
            # Check if the exact same persistent message is already the last one
            if self.game_messages and self.game_messages[-1]['text'] == text and self.game_messages[-1]['timer'] == -1:
                return # Don't add duplicate persistent message
            # Remove any other non-persistent messages if adding a new persistent one
            # Or, if a different persistent message exists, it will be replaced by this new one if it's added after filtering.
            self.game_messages = [msg for msg in self.game_messages if msg['timer'] == -1 and msg['text'] != text]
        else:
            # If new message is not persistent, clear old non-persistent ones to keep log clean,
            # but keep existing persistent messages.
            # This logic might need refinement based on desired message log behavior.
            # For now, let's just ensure non-persistent messages don't pile up indefinitely if not shown in a log.
            # If a proper log is implemented, this filtering might change.
            pass # Current logic adds to a list, UI will handle display limit

        # Add the new message
        self.game_messages.append({'text': text, 'timer': duration})
        
        # Limit number of messages displayed if necessary (more relevant when UI shows a list)
        max_messages = 10 # Increased for a potential log
        if len(self.game_messages) > max_messages:
            # Keep the most recent messages, prioritizing persistent ones if any are outside the new tail.
            # This simple slice might lose older persistent messages if many non-persistent ones follow.
            # A more robust approach would be needed for a true scrolling log with persistent message retention.
            # For now, this just limits the list size.
            self.game_messages = self.game_messages[-max_messages:]
