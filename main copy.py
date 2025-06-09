import pygame
import sys
import os
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from game import Game
# Conditional import for Editor
# from editor import Editor # Moved down
from ui import MainMenu, MapSelectionScreen

def main():
    print("WASM: main() called")
    try:
        pygame.init()
        print("WASM: pygame.init() successful")
    except Exception as e:
        print(f"WASM: ERROR during pygame.init(): {e}")
        return

    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ASCII RPG")
        print("WASM: Screen initialized")
    except Exception as e:
        print(f"WASM: ERROR setting up screen: {e}")
        return
            
    clock = pygame.time.Clock()

    WASM_DIRECT_MAP_NAME = os.environ.get("WASM_DIRECT_MAP_NAME")
    
    game = None
    editor = None # Initialize editor to None
    main_menu = None
    map_selection_screen = None
    running = True

    if WASM_DIRECT_MAP_NAME:
        print(f"WASM: Direct Play Mode. Map Name from env: '{WASM_DIRECT_MAP_NAME}'")
        current_state = "game"
        selected_map_for_game = WASM_DIRECT_MAP_NAME
        # Editor is not needed and not imported/instantiated
        print("WASM: Initializing Game object for direct play...")
        try:
            game = Game(screen)
            print("WASM: Game object initialized successfully.")
        except Exception as e:
            print(f"WASM: ERROR initializing Game object: {e}")
            running = False
    else:
        # Standard setup with Editor
        print("WASM: Standard Play Mode (main menu or editor).")
        from editor import Editor # Import Editor only when needed
        current_state = "main_menu"
        selected_map_for_game = None
        try:
            main_menu = MainMenu(screen)
            map_selection_screen = MapSelectionScreen(screen)
            game = Game(screen)
            editor = Editor(screen) # Instantiate Editor
            print("WASM: Standard mode objects (including Editor) initialized.")
        except Exception as e:
            print(f"WASM: ERROR initializing standard mode objects: {e}")
            running = False

    print(f"WASM: Starting main loop. Initial state: {current_state}, Running: {running}")
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                print("WASM: QUIT event received.")
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    print("WASM: ESCAPE key pressed.")
                    if WASM_DIRECT_MAP_NAME:
                        pass
                    elif current_state == "game" or current_state == "editor":
                        current_state = "main_menu"
                        pygame.display.set_caption("ASCII RPG - Main Menu")

        try:
            screen.fill((0, 0, 0))

            if current_state == "main_menu" and main_menu:
                main_menu.draw()
                for event_m in events: # Use a different var name
                    new_state_info = main_menu.handle_input(event_m)
                    if isinstance(new_state_info, tuple):
                        new_state, data = new_state_info
                    else:
                        new_state, data = new_state_info, None

                    if new_state != "main_menu":
                        current_state = new_state
                        if current_state == "map_selection" and map_selection_screen:
                            map_selection_screen.load_available_maps()
                            pygame.display.set_caption("ASCII RPG - Select Map")
                        elif current_state == "game":
                            pygame.display.set_caption("ASCII RPG - Game")
                        elif current_state == "editor" and editor: # editor will be None in WASM mode
                            if editor: editor.load_entity_definitions() 
                            pygame.display.set_caption("ASCII RPG - Editor")
                        break 
            
            elif current_state == "map_selection" and map_selection_screen:
                map_selection_screen.draw()
                for event_s in events: # Use a different var name
                    new_state_info = map_selection_screen.handle_input(event_s)
                    if isinstance(new_state_info, tuple):
                        new_state, data = new_state_info
                    else:
                        new_state, data = new_state_info, None

                    if new_state != "map_selection":
                        current_state = new_state
                        if current_state == "game":
                            if data and game: 
                                selected_map_for_game = data
                                game.reset()
                                game.game_state = "loading"
                                pygame.display.set_caption(f"ASCII RPG - Loading ({selected_map_for_game})...")
                            else: 
                                current_state = "main_menu" 
                                pygame.display.set_caption("ASCII RPG - Main Menu")
                        elif current_state == "main_menu":
                             pygame.display.set_caption("ASCII RPG - Main Menu")
                        break

            elif current_state == "game" and game:
                if selected_map_for_game and not game.is_initialized() and \
                   game.game_state not in ["critical_error_no_player", "critical_error", "load_error"]:
                    print(f"WASM: Attempting to load game state for map: {selected_map_for_game}")
                    try:
                        game.load_game_state(selected_map_for_game)
                        print(f"WASM: game.load_game_state called. Game initialized: {game.is_initialized()}, Game state: {game.game_state}")
                    except Exception as e:
                        print(f"WASM: ERROR during game.load_game_state: {e}")
                        if game: game.game_state = "load_error" 
                
                if game.is_initialized():
                    for event_g in events:
                        game.handle_input(event_g)
                    game.update()
                    game.draw()
                    if game.is_over(): 
                        if WASM_DIRECT_MAP_NAME:
                            pass
                        else:
                            current_state = "main_menu"
                            selected_map_for_game = None 
                            if game: game.reset() 
                            pygame.display.set_caption("ASCII RPG - Main Menu")
                elif game.game_state in ["critical_error_no_player", "critical_error", "load_error"]:
                    print(f"WASM: Game in error state: {game.game_state}. Cannot proceed with game logic.")
                else:
                    pass

            elif current_state == "editor" and editor: # This block will not be entered in WASM direct play
                for event_e in events: # Use a different var name
                    editor.handle_input(event_e)
                editor.update()
                editor.draw()
                if editor.is_done(): 
                    current_state = "main_menu"
                    pygame.display.set_caption("ASCII RPG - Main Menu")

            pygame.display.flip()
        except Exception as e:
            print(f"WASM: ERROR in main loop drawing/flipping: {e}")
            # import traceback
            # traceback.print_exc()
            running = False

        clock.tick(FPS)

    print("WASM: Exiting main loop.")
    pygame.quit()
    print("WASM: pygame.quit() called.")
    # sys.exit() # Generally not needed/problematic in WASM

if __name__ == "__main__":
    print("WASM: __main__ block reached.")
    main()
