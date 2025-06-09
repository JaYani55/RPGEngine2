import os
import shutil
import json
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMP_BUILD_SRC_DIR = os.path.join(PROJECT_ROOT, "temp_wasm_build_src")
FINAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "wasm_game_output")

# Core Python files to include
CORE_FILES = [
    "main.py", "game.py", "engine.py", "renderer.py", "ui.py",
    "config.py", "utils.py", "abilities.py", "data_manager.py", "tiles.py", "ai.py",
    "editor.py" 
]

# Asset directories relative to PROJECT_ROOT
DATA_DIR_NAME = "data"
MAP_DIR_REL = os.path.join(DATA_DIR_NAME, "maps")
ENTITY_DIR_REL = os.path.join(DATA_DIR_NAME, "entities")
ABILITY_DIR_REL = os.path.join(DATA_DIR_NAME, "abilities")

def create_temp_project_dir():
    if os.path.exists(TEMP_BUILD_SRC_DIR):
        shutil.rmtree(TEMP_BUILD_SRC_DIR)
    os.makedirs(TEMP_BUILD_SRC_DIR)

    # No longer creating a separate 'assets' subdirectory for Python files here.
    # Python files will go to the root of TEMP_BUILD_SRC_DIR.

    # Create data subdirectories at the root of TEMP_BUILD_SRC_DIR
    data_root_in_temp = os.path.join(TEMP_BUILD_SRC_DIR, DATA_DIR_NAME)
    os.makedirs(data_root_in_temp)
    os.makedirs(os.path.join(data_root_in_temp, "maps"))
    os.makedirs(os.path.join(data_root_in_temp, "entities"))
    os.makedirs(os.path.join(data_root_in_temp, "abilities"))


def copy_core_files():
    # Destination for Python files is now the root of TEMP_BUILD_SRC_DIR
    py_dst_dir = TEMP_BUILD_SRC_DIR

    for file_name in CORE_FILES:
        src_path = os.path.join(PROJECT_ROOT, file_name)
        dst_path = os.path.join(py_dst_dir, file_name) # Copy to root of temp dir
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_path)
        else:
            print(f"Warning: Core file {file_name} not found at {src_path}")
    
    # Create a minimal requirements.txt at the root of TEMP_BUILD_SRC_DIR
    wasm_requirements_path = os.path.join(py_dst_dir, "requirements.txt")
    with open(wasm_requirements_path, "w") as f:
        f.write("pygame==2.6.1\n") # Ensure this matches your Pygame version
    print(f"Generated minimal requirements.txt for WASM build at {wasm_requirements_path}")

def get_entities_from_map(map_file_path_abs):
    entities = set()
    try:
        with open(map_file_path_abs, 'r') as f:
            map_data = json.load(f) # Ensure json is loaded
        if "entities_on_map" in map_data:
            for entity_info in map_data["entities_on_map"]:
                if "id" in entity_info:
                    entities.add(entity_info["id"] + ".json")
    except Exception as e:
        print(f"Error reading map {map_file_path_abs}: {e}")
    return list(entities)

def copy_specific_assets(target_map_name_no_ext):
    target_map_filename = target_map_name_no_ext + ".json"
    data_root_in_temp = os.path.join(TEMP_BUILD_SRC_DIR, DATA_DIR_NAME)

    src_map_path_abs = os.path.join(PROJECT_ROOT, MAP_DIR_REL, target_map_filename)
    dst_map_path_abs = os.path.join(data_root_in_temp, "maps", target_map_filename)
    if os.path.exists(src_map_path_abs):
        shutil.copy(src_map_path_abs, dst_map_path_abs)
    else:
        print(f"Error: Target map {target_map_filename} not found at {src_map_path_abs}.")
        return False

    entity_files_to_copy = get_entities_from_map(src_map_path_abs) # Pass original source map path
    print(f"Entities referenced in map '{target_map_filename}': {entity_files_to_copy}")
    for entity_file in entity_files_to_copy:
        src_entity_path_abs = os.path.join(PROJECT_ROOT, ENTITY_DIR_REL, entity_file)
        dst_entity_path_abs = os.path.join(data_root_in_temp, "entities", entity_file)
        if os.path.exists(src_entity_path_abs):
            shutil.copy(src_entity_path_abs, dst_entity_path_abs)
        else:
            print(f"Warning: Entity file {entity_file} not found at {src_entity_path_abs}.")
            
    src_ability_dir_abs = os.path.join(PROJECT_ROOT, ABILITY_DIR_REL)
    dst_ability_dir_temp = os.path.join(data_root_in_temp, "abilities")
    if os.path.exists(src_ability_dir_abs):
        for item in os.listdir(src_ability_dir_abs):
            s_abs = os.path.join(src_ability_dir_abs, item)
            d_temp = os.path.join(dst_ability_dir_temp, item)
            if os.path.isfile(s_abs) and s_abs.endswith(".json"):
                shutil.copy2(s_abs, d_temp)
    else:
        print(f"Warning: Ability directory not found at {src_ability_dir_abs}")
    return True

def run_pygbag_build(target_map_name_no_ext):
    if os.path.exists(FINAL_OUTPUT_DIR):
        shutil.rmtree(FINAL_OUTPUT_DIR)
    
    current_env = os.environ.copy()
    current_env["WASM_DIRECT_MAP_NAME"] = target_map_name_no_ext
    
    app_package_name = "myrpgengine" 
    custom_template_name = "custom_pygbag.tmpl" # Name of your custom template file
    custom_template_path = os.path.join(PROJECT_ROOT, custom_template_name)

    if not os.path.exists(custom_template_path):
        print(f"ERROR: Custom template '{custom_template_name}' not found at '{custom_template_path}'.")
        print(f"Please download the default Pygbag template, modify it, and save it as '{custom_template_name}' in your project root.")
        print("See instructions for template modification.")
        return # Stop if template is missing

    pygbag_cmd = [
        sys.executable, "-m", "pygbag",
        "--app_name", app_package_name,
        "--template", custom_template_path, # Use the custom template
        TEMP_BUILD_SRC_DIR 
    ]
    
    try:
        print(f"Running Pygbag with command: {' '.join(pygbag_cmd)}")
        print(f"Setting environment variable for pygbag: WASM_DIRECT_MAP_NAME={target_map_name_no_ext}")
        subprocess.run(pygbag_cmd, check=True, cwd=PROJECT_ROOT, env=current_env)

        pygbag_build_output = os.path.join(TEMP_BUILD_SRC_DIR, "build", "web")
        if os.path.exists(pygbag_build_output):
            if os.path.exists(FINAL_OUTPUT_DIR):
                shutil.rmtree(FINAL_OUTPUT_DIR)
            shutil.move(pygbag_build_output, FINAL_OUTPUT_DIR)
            print(f"Pygbag build successful. Output moved to: {FINAL_OUTPUT_DIR}")
            print(f"You can usually serve this directory with a local web server, e.g.:")
            print(f"cd \"{FINAL_OUTPUT_DIR}\" && python -m http.server")
        else:
            print("Pygbag build completed, but output directory not found where expected.")
            print(f"Expected at: {pygbag_build_output}")
            # Fallback check (less likely with current pygbag behavior)
            fallback_output = os.path.join(PROJECT_ROOT, "build", "web")
            if os.path.exists(fallback_output):
                 if os.path.exists(FINAL_OUTPUT_DIR):
                    shutil.rmtree(FINAL_OUTPUT_DIR)
                 shutil.move(fallback_output, FINAL_OUTPUT_DIR)
                 print(f"Pygbag build successful. Output found at fallback and moved to: {FINAL_OUTPUT_DIR}")


    except subprocess.CalledProcessError as e:
        print(f"Pygbag build failed: {e}")
    except FileNotFoundError:
        print("Pygbag command (via python -m pygbag) failed or Pygbag is not installed correctly.")
        print("Ensure Pygbag is installed: pip install pygbag")

def main():
    print("RPG Engine WASM Export for Single Map")
    print("------------------------------------")
    
    available_maps = []
    maps_path = os.path.join(PROJECT_ROOT, MAP_DIR_REL)
    if os.path.exists(maps_path):
        available_maps = [f.replace(".json", "") for f in os.listdir(maps_path) if f.endswith(".json")]
    
    if not available_maps:
        print(f"No maps found in '{maps_path}'. Please create a map first.")
        return

    print("Available maps:")
    for i, map_name in enumerate(available_maps):
        print(f"  {i+1}. {map_name}")
    
    choice = input("Enter the number of the map to export: ")
    try:
        map_idx = int(choice) - 1
        if not (0 <= map_idx < len(available_maps)):
            raise ValueError
        target_map_name_no_ext = available_maps[map_idx]
    except ValueError:
        print("Invalid choice.")
        return

    print(f"\nSelected map for export: {target_map_name_no_ext}.json")

    print("\nStep 1: Creating temporary build directory...")
    create_temp_project_dir()
    
    print("\nStep 2: Copying core game files to the root of temp directory...")
    copy_core_files()
    
    print(f"\nStep 3: Copying data assets for map '{target_map_name_no_ext}' into 'data' subdirectory...")
    if not copy_specific_assets(target_map_name_no_ext):
        print("Asset copying failed. Aborting.")
        shutil.rmtree(TEMP_BUILD_SRC_DIR)
        return
    
    print("\nStep 4: Running Pygbag to build WASM package...")
    run_pygbag_build(target_map_name_no_ext)
        
    print("\nExport process finished.")

if __name__ == "__main__":
    main()