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
                            # game.load_game_state(selected_map_for_game) # We'll implement this next
                            pygame.display.set_caption(f"ASCII RPG - Game ({selected_map_for_game})")
                        else: # Should not happen if logic is correct
                            current_state = "main_menu" 
                            pygame.display.set_caption("ASCII RPG - Main Menu")
                    elif current_state == "main_menu":
                         pygame.display.set_caption("ASCII RPG - Main Menu")
                    break


        elif current_state == "game":
            # Initialize game with selected map if not already done
            # This is a bit of a placeholder, actual loading should happen once
            if selected_map_for_game and not game.is_initialized(): # Add is_initialized to Game class
                game.load_game_state(selected_map_for_game)

            if game.is_initialized():
                for event in events:
                    game.handle_input(event)
                game.update()
                game.draw()
                if game.is_over(): 
                    current_state = "main_menu"
                    selected_map_for_game = None # Reset selected map
                    game.reset() # Add a reset method to Game class
                    pygame.display.set_caption("ASCII RPG - Main Menu")
            else:
                # Handle case where game couldn't initialize (e.g. map load failed)
                # For now, just go back to map selection or main menu
                font = pygame.font.Font(None, 36)
                text = font.render(f"Error: Game not initialized. Map: {selected_map_for_game}", True, (255,0,0))
                text_rect = text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
                screen.blit(text, text_rect)
                # Potentially add a timer or key press to go back
                # For simplicity, this state will persist until ESC is pressed (handled globally)


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
