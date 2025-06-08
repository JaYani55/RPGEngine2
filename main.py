import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from game import Game
from editor import Editor
from ui import MainMenu, MapSelectionScreen # Added MapSelectionScreen

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("ASCII RPG")
    clock = pygame.time.Clock()

    current_state = "main_menu" # "main_menu", "map_selection", "game", "editor"
    selected_map_for_game = None

    main_menu = MainMenu(screen)
    map_selection_screen = MapSelectionScreen(screen) # Initialize map selection
    game = Game(screen)
    editor = Editor(screen)

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            
            # Global keybinds, e.g., ESC to go to main menu
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if current_state == "game" or current_state == "editor":
                        current_state = "main_menu"
                        pygame.display.set_caption("ASCII RPG - Main Menu")


        screen.fill((0, 0, 0))

        if current_state == "main_menu":
            main_menu.draw()
            for event in events: # Pass events specifically to the active state's handler
                new_state_info = main_menu.handle_input(event)
                # new_state_info could be just a string or a tuple
                if isinstance(new_state_info, tuple):
                    new_state, data = new_state_info
                else:
                    new_state, data = new_state_info, None

                if new_state != "main_menu":
                    current_state = new_state
                    if current_state == "map_selection":
                        map_selection_screen.load_available_maps() # Refresh map list
                        pygame.display.set_caption("ASCII RPG - Select Map")
                    elif current_state == "game":
                        # This case might be deprecated if game is always started from map_selection
                        # game.load_game_data("default_map.json") # Example
                        pygame.display.set_caption("ASCII RPG - Game")
                    elif current_state == "editor":
                        editor.load_entity_definitions() 
                        pygame.display.set_caption("ASCII RPG - Editor")
                    break 
        
        elif current_state == "map_selection":
            map_selection_screen.draw()
            for event in events:
                new_state_info = map_selection_screen.handle_input(event)
                if isinstance(new_state_info, tuple):
                    new_state, data = new_state_info
                else:
                    new_state, data = new_state_info, None

                if new_state != "map_selection":
                    current_state = new_state
                    if current_state == "game":
                        if data: # data here is the map_name
                            selected_map_for_game = data
                            # Reset game state before attempting to load a new map
                            game.reset()
                            game.game_state = "loading" # Explicitly set to loading
                            pygame.display.set_caption(f"ASCII RPG - Loading ({selected_map_for_game})...")
                        else: # Should not happen if logic is correct
                            current_state = "main_menu" 
                            pygame.display.set_caption("ASCII RPG - Main Menu")
                    elif current_state == "main_menu":
                         pygame.display.set_caption("ASCII RPG - Main Menu")
                    break


        elif current_state == "game":
            # Attempt to load the game if a map is selected and the game isn't initialized
            # and not already in a persistent critical error state from a previous attempt.
            if selected_map_for_game and not game.is_initialized() and \
               game.game_state not in ["critical_error_no_player", "critical_error", "load_error"]:
                game.load_game_state(selected_map_for_game)

            # After attempting to load (or if already loaded/failed):
            if game.is_initialized():
                # Game is loaded and ready, run the game loop
                for event in events:
                    game.handle_input(event)
                game.update()
                game.draw()
                if game.is_over(): 
                    current_state = "main_menu"
                    selected_map_for_game = None # Reset selected map
                    game.reset() 
                    pygame.display.set_caption("ASCII RPG - Main Menu")
            else: # Game is NOT initialized
                # Game is not initialized. Check why.
                if game.game_state in ["critical_error_no_player", "critical_error", "load_error"]:
                    # A critical error occurred during loading. Transition out of "game" state.
                    print(f"MAIN_LOOP: Critical game load error: {game.game_state}. Returning to map selection.")
                    
                    # Force transition to map selection:
                    current_state = "map_selection"
                    selected_map_for_game = None # Crucial to prevent reloading the same bad map
                    game.reset() # Reset game's internal state (sets _initialized=False, game_state="loading")
                    
                    # Ensure map_selection_screen is ready
                    # Assuming map_selection_screen is defined in the scope and has load_available_maps
                    if 'map_selection_screen' in locals() and hasattr(map_selection_screen, 'load_available_maps'):
                        map_selection_screen.load_available_maps() 
                    
                    pygame.display.set_caption("ASCII RPG - Select Map")
                else:
                    # Game is not initialized, but not due to a critical load error.
                    # This could be initial state ("loading" but no map selected yet to trigger load_game_state),
                    # or game.load_game_state() hasn't been called yet in this cycle.
                    # A black screen will be shown as game.draw() will likely return early.
                    pass


        elif current_state == "editor":
            for event in events:
                editor.handle_input(event)
            editor.update()
            editor.draw()
            if editor.is_done(): # Example, if editor has a way to signal completion
                current_state = "main_menu"
                pygame.display.set_caption("ASCII RPG - Main Menu")

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
