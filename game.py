import pygame 
import asyncio # Add asyncio import
from renderer import Renderer
from engine import GameEngine, GameMap, Entity 
from ui import GameUI
from data_manager import load_map_data
from utils import pixel_to_grid 
from config import TILE_SIZE, FONT_NAME, FONT_SIZE, COLORS # Added FONT_NAME, FONT_SIZE, COLORS
from abilities import Ability

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.renderer: Renderer | None = None
        self.engine: GameEngine | None = None
        self.ui: GameUI | None = None
        
        self.player: Entity | None = None
        
        self.is_running = False
        self._initialized = False
        self.current_map_name = None
        
        self.selected_entity: Entity | None = None
        self.highlighted_tiles_move = []
        self.highlighted_tiles_ability = [] 
        self.action_mode = None # e.g., "select", "move_target", "ability_target"
        self.selected_ability: Ability | None = None # Store the selected ability object
        self.game_messages = [] # List of dicts: {'text': "message", 'timer': 60}
        self.game_state = "loading" # e.g., loading, player_turn, npc_turn, game_over

        self.mouse_pos = (0, 0) # For hover effects and clicks
        self.hovered_tile_info = None # For displaying AP cost on move hover
        self.hovered_ability_info = None # Stores {'ability': Ability, 'ap_cost': int}


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
                print("Error: Player entity not found after engine initialization. Map might be missing a player entity or the 'is_player':true flag on an entity.")
                self.set_message("CRITICAL: No player in map data!", 240)
                self._initialized = False
                self.is_running = False
                self.game_state = "critical_error_no_player" # Specific error state
                # Clean up renderer and ui as they might not be fully set up or expect a player
                self.renderer = None
                self.ui = None
                return # IMPORTANT: Stop further initialization if no player

            self.renderer = Renderer(self.screen)
            self.ui = GameUI(self.screen) # Ensure UI is initialized
            
            self._initialized = True
            self.is_running = True
            self.engine.start_game() 
            self.game_state = self.engine.game_state # Use direct attribute
            self.set_message(f"Loaded {map_file_name}. {self.player.name}'s turn!", 120)
            # Auto-select player at game start if it's their turn
            if self.game_state == "player_turn":
                self.selected_entity = self.player
                self.action_mode = "select" # Default to select mode
                if self.player and self.engine: # Ensure engine is available
                    reachable_tiles_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                    self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_tiles_data] # Corrected line
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

    def _end_player_turn(self):
        if self.engine:
            self.engine.next_turn()
            self.game_state = self.engine.game_state
            current_turn_entity = self.engine.get_current_turn_entity()
            self.set_message(f"{current_turn_entity.name}'s turn." if current_turn_entity else "Turn ended.", 60)
            
            self.selected_entity = None 
            self.action_mode = None
            self.highlighted_tiles_move = []
            self.highlighted_tiles_ability = []
            self.selected_ability = None
            self.hovered_tile_info = None
            self.hovered_ability_info = None

            if self.game_state == "player_turn" and self.player:
                self.selected_entity = self.player
                self.action_mode = "select"
                # Refresh player's available moves
                if self.engine:
                    reachable_tiles_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                    self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_tiles_data]


    def handle_input(self, event):
        if not self._initialized or not self.is_running or self.game_state == "loading":
            return

        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self.hovered_tile_info = None # Reset hover info
            self.hovered_ability_info = None # Reset ability hover info

            if self.engine and self.ui:                # Tile hover for movement
                if self.action_mode in ["select", "move_target"] and self.selected_entity and self.selected_entity == self.player:
                    gx, gy = pixel_to_grid(self.mouse_pos[0], self.mouse_pos[1] - self.renderer.map_render_offset_y, TILE_SIZE)
                    if self.engine.game_map.is_valid(gx, gy):
                        reachable_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                        if (gx, gy) in reachable_data:
                            cost = reachable_data[(gx,gy)]
                            # Pathfinding for display can be added here if desired
                            # For now, just cost and position
                            self.hovered_tile_info = {'pos': (gx, gy), 'cost': cost, 'path': []} # Path is placeholder

                # Ability hover for AP cost
                hovered_ability_obj = self.ui.get_hovered_ability(self.mouse_pos, self.player.abilities if self.player else [])
                if hovered_ability_obj:
                    self.hovered_ability_info = {'ability': hovered_ability_obj, 'ap_cost': hovered_ability_obj.ap_cost}


        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                # UI Clicks (e.g., End Round button)
                if self.ui and self.game_state == "player_turn":
                    clicked_button_action = self.ui.get_clicked_button(event.pos, self.game_state == "player_turn")
                    if clicked_button_action == "end_round":
                        self._end_player_turn()
                        return # Action handled
                
                # Ability selection from UI
                if self.ui and self.player and self.game_state == "player_turn":
                    clicked_ability = self.ui.get_clicked_ability(event.pos, self.player.abilities)
                    if clicked_ability:
                        if self.player.current_ap >= clicked_ability.ap_cost:
                            self.selected_ability = clicked_ability
                            self.action_mode = "ability_target"
                            self.highlighted_tiles_move = [] # Clear move highlights
                            if self.engine:
                                self.highlighted_tiles_ability = self.engine.get_valid_targets_for_ability(self.player, self.selected_ability)
                        else:
                            self.set_message(f"Not enough AP for {clicked_ability.name}.", 60)
                        return # Action handled

                # Map clicks (movement or ability targeting)
                if self.engine and self.selected_entity and self.game_state == "player_turn":
                    gx, gy = pixel_to_grid(event.pos[0], event.pos[1] - self.renderer.map_render_offset_y, TILE_SIZE)

                    if self.action_mode == "move_target" or (self.action_mode == "select" and self.selected_entity == self.player):
                        if (gx, gy) in self.highlighted_tiles_move:
                            success, message = self.engine.handle_player_action("move", target_pos=(gx, gy))
                            self.set_message(message, 60)
                            if success:
                                # Refresh highlights after move
                                reachable_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                                self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_data] # Corrected line
                                if not self.highlighted_tiles_move or self.player.current_ap == 0:
                                    self.action_mode = "select" # Or end turn if no AP
                            # If player has no more AP, or no valid moves, consider changing action_mode or prompting End Turn
                            if self.player.current_ap == 0:
                                self.set_message("Out of AP. End your turn.", 90)
                                self.action_mode = "select" # Prevent further move attempts
                                self.highlighted_tiles_move = []


                    elif self.action_mode == "ability_target" and self.selected_ability:
                        if (gx, gy) in self.highlighted_tiles_ability:
                            success, message = self.engine.handle_player_action("ability", target_pos=(gx, gy), ability_to_use=self.selected_ability)
                            self.set_message(message, 60)
                            if success:
                                self.selected_ability = None
                                self.action_mode = "select"
                                self.highlighted_tiles_ability = []
                                # Refresh move highlights as AP might have changed
                                reachable_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                                self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_data] # Corrected line
                                if self.player.current_ap == 0:
                                    self.set_message("Out of AP. End your turn.", 90)
                                    self.highlighted_tiles_move = []


        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: 
                if self.action_mode in ["move_target", "ability_target"]:
                    self.action_mode = "select"
                    self.selected_ability = None
                    self.highlighted_tiles_ability = []
                    if self.selected_entity and self.selected_entity == self.player and self.engine:
                         reachable_tiles_data = self.engine.get_reachable_tiles_with_ap_cost(self.selected_entity)
                         self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_tiles_data] # Corrected line
                    else:
                        self.highlighted_tiles_move = []
                    self.hovered_tile_info = None
                    return
                elif self.action_mode == "select" and self.selected_entity:
                    # self.selected_entity = None # Keep player selected
                    # self.highlighted_tiles_move = []
                    self.hovered_tile_info = None
                    return
            
            # Hotkeys for abilities (e.g., 1, 2, 3)
            if self.game_state == "player_turn" and self.player and self.ui:
                key_to_ability_index = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3, pygame.K_5: 4} # Max 5 for now
                if event.key in key_to_ability_index:
                    ability_index = key_to_ability_index[event.key]
                    if 0 <= ability_index < len(self.player.abilities):
                        ability_to_select = self.player.abilities[ability_index]
                        if self.player.current_ap >= ability_to_select.ap_cost:
                            self.selected_ability = ability_to_select
                            self.action_mode = "ability_target"
                            self.highlighted_tiles_move = []
                            if self.engine:
                                self.highlighted_tiles_ability = self.engine.get_valid_targets_for_ability(self.player, self.selected_ability)
                        else:
                            self.set_message(f"Not enough AP for {ability_to_select.name}.", 60)
                        return


    async def update(self): # <--- CHANGED to async def
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
            if self.engine.game_state in ["game_over_player_win", "game_over_player_lose"]:
                self.game_state = self.engine.game_state

            if self.game_state != "player_turn" and self.engine.game_state == self.game_state: 
                current_npc = self.engine.get_current_turn_entity()
                print(f"GAME_DEBUG: Update loop - NPC turn. Current NPC: {current_npc.name if current_npc else 'None'}. Game state: {self.game_state}") 
                if current_npc and not current_npc.is_dead:
                    print(f"GAME_DEBUG: Calling engine.run_npc_turn for {current_npc.name}") 
                    await self.engine.run_npc_turn(current_npc) # <--- CHANGED to await
                    
                    self.game_state = self.engine.game_state 

                    if self.game_state == "player_turn" and self.player:
                         self.selected_entity = self.player 
                         self.action_mode = "select"
                         if self.engine:
                            reachable_tiles_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                            self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_tiles_data] 
            
            elif self.game_state == "player_turn" and self.engine.game_state == "player_turn":
                if self.selected_entity != self.player : 
                    self.selected_entity = self.player
                    self.action_mode = "select"
                    if self.engine:
                        reachable_tiles_data = self.engine.get_reachable_tiles_with_ap_cost(self.player)
                        self.highlighted_tiles_move = [tile_data[0] for tile_data in reachable_tiles_data] 

        if self.game_state in ["game_over_player_win", "game_over_player_lose"] and self.is_running:
            # Game over logic handled by main loop checking is_over()
            pass


    def draw(self):
        self.screen.fill(COLORS.get("black", (0,0,0))) # Clear screen
        if not self.is_initialized() or not self.renderer or not self.engine or not self.ui:
            # Draw loading/error message if not initialized
            if not self._initialized and (self.game_state == "load_error" or self.game_state == "critical_error"):
                msg_font = pygame.font.Font(FONT_NAME, FONT_SIZE + 4)
                last_message = self.game_messages[-1]['text'] if self.game_messages else "Error initializing game."
                text_surface = msg_font.render(last_message, True, COLORS.get("red", (255,0,0)))
                text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
                self.screen.blit(text_surface, text_rect)
            return

        self.renderer.draw_game_state(
            self.engine,
            self.selected_entity,
            self.highlighted_tiles_move,
            self.highlighted_tiles_ability,
            self.action_mode,
            self.selected_ability,
            self.hovered_tile_info 
        )

        self.ui.draw(
            self.engine.player,
            self.engine.get_current_turn_entity(),
            self.engine.game_log, 
            self.game_state, 
            self.selected_entity,
            self.selected_ability,
            self.hovered_ability_info # Pass hovered ability info to UI
        )
        
        if self.game_messages:
            msg_font = pygame.font.Font(FONT_NAME, FONT_SIZE) 
            base_y = 20 # Starting Y position for messages
            for i, msg_data in enumerate(self.game_messages):
                text_surface = msg_font.render(msg_data['text'], True, COLORS.get("white", (255,255,255)))
                text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, base_y + i * (FONT_SIZE + 2)))
                self.screen.blit(text_surface, text_rect)


    def reset(self):
        # ... (fields from init) ...
        self.renderer = None
        self.engine = None
        self.ui = None
        self.player = None
        self._initialized = False
        self.is_running = False
        self.current_map_name = None
        self.selected_entity = None
        self.highlighted_tiles_move = []
        self.highlighted_tiles_ability = []
        self.action_mode = None
        self.selected_ability = None
        self.game_messages = []
        self.game_state = "loading"
        self.mouse_pos = (0,0)
        self.hovered_tile_info = None
        self.hovered_ability_info = None
        print("Game state reset.")

    def is_over(self):
        return self.game_state in ["game_over_player_win", "game_over_player_lose"]

    def is_initialized(self):
        return self._initialized

    def set_message(self, text, duration=90): 
        MAX_LOG_MESSAGES_ON_SCREEN = 3
        if len(self.game_messages) >= MAX_LOG_MESSAGES_ON_SCREEN:
            self.game_messages.pop(0)
        self.game_messages.append({'text': text, 'timer': duration})
        # Also add to engine's persistent log if appropriate
        if self.engine:
             self.engine.add_log_message(f"GAME: {text}") # Distinguish from engine-internal logs if needed
        print(f"GAME_MESSAGE: {text}")
