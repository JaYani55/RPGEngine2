## WASM Export Explained

The goal of the WebAssembly (WASM) export is to package your Python and Pygame application so it can run directly in a web browser. This is achieved using **Pygbag**, a tool that bundles your Python code, assets, and a Python interpreter (compiled to WASM) into a web-friendly format.

### 1. The export_wasm_single_map.py Script

This script automates the process of preparing your game files and running Pygbag for a specific game map.

**How it Functions:**

1.  **Initialization:**
    *   Defines project paths (`PROJECT_ROOT`, `TEMP_BUILD_SRC_DIR`, `FINAL_OUTPUT_DIR`).
    *   Lists `CORE_FILES`: These are all the Python `.py` files that make up your game's codebase, including editor.py again.
    *   Defines relative paths for your data asset directories (`DATA_DIR_NAME`, `MAP_DIR_REL`, etc.).

2.  **`create_temp_project_dir()`:**
    *   Clears and creates a temporary directory (`temp_wasm_build_src`). This directory will be the staging area for Pygbag.
    *   Crucially, it **does not** create an `assets` subdirectory for Python files anymore. Python files go to the root of `temp_wasm_build_src`.
    *   It creates the data directory structure (maps, entities, abilities) directly within `temp_wasm_build_src`. This matches the structure your game expects when running from the `assets` directory inside the VFS.

3.  **`copy_core_files()`:**
    *   Copies all Python files listed in `CORE_FILES` from your project root to the root of `TEMP_BUILD_SRC_DIR`.
    *   Generates a minimal requirements.txt file (containing `pygame==2.6.1`) in `TEMP_BUILD_SRC_DIR`. Pygbag uses this to know which version of Pygame to bundle.

4.  **`get_entities_from_map(map_file_path_abs)`:**
    *   Reads the specified JSON map file.
    *   Extracts all unique entity IDs referenced in the `entities_on_map` section.
    *   Returns a list of entity filenames (e.g., `["goblin.json", "player_character.json"]`).

5.  **`copy_specific_assets(target_map_name_no_ext)`:**
    *   Copies the chosen map file (e.g., `King Of The Hill.json`) into `temp_wasm_build_src/data/maps/`.
    *   Uses `get_entities_from_map()` to find out which entity JSON files are needed for that map and copies them from your project's entities to `temp_wasm_build_src/data/entities/`.
    *   Copies all ability JSON files from your project's abilities to `temp_wasm_build_src/data/abilities/`.

6.  **`run_pygbag_build(target_map_name_no_ext)`:**
    *   Clears the `FINAL_OUTPUT_DIR` if it exists.
    *   Sets an environment variable `WASM_DIRECT_MAP_NAME` to the name of the map being exported. Your main.py uses this to bypass menus and load the specified map directly.
    *   Constructs the `pygbag` command:
        *   `sys.executable -m pygbag`: Runs Pygbag as a module.
        *   `--app_name myrpgengine`: Sets the application name.
        *   `--template c:\CodingProjects\Games\RPGEngine2\custom_pygbag.tmpl`: **Crucially, this tells Pygbag to use your modified HTML template.**
        *   `TEMP_BUILD_SRC_DIR`: Specifies the directory containing the files to package.
    *   Runs the `pygbag` command. Pygbag will:
        *   Create an APK-like archive (e.g., `temp_wasm_build_src.apk`) containing all files from `TEMP_BUILD_SRC_DIR`.
        *   Use the custom_pygbag.tmpl to generate the final `index.html` and other necessary web files.
    *   Moves the generated web files from Pygbag's build output (usually `temp_wasm_build_src/build/web`) to your `FINAL_OUTPUT_DIR`.

7.  **`main()` (script's entry point):**
    *   Prompts the user to select a map.
    *   Calls the functions above in sequence to prepare files and build the WASM package.

### 2. The custom_pygbag.tmpl File

This file is a modified version of Pygbag's default HTML template. It allows you to customize the HTML structure and, more importantly, the Python bootstrap code that runs when the page loads in the browser.

**How it Functions (Key Parts):**

*   **HTML Structure:** It's a standard HTML file. The most important part is the `<script src="{{cookiecutter.cdn}}pythons.js" ... id=site ...>` tag. The Python code embedded within the `#<!-- ... -->` comments inside this script tag is executed by the Pygbag JavaScript runtime.
*   **`async def custom_site():`**: This is the main asynchronous Python function that Pygbag executes from the template.
    *   **Imports:** Imports necessary modules like `pygame`, `asyncio`, `platform` (Pygbag's bridge to JavaScript/browser APIs), `os`, `sys`, `json`, `Path`, `embed`.
    *   **Initial Pygame Setup:** Initializes Pygame and sets up a display surface. This was initially used for a loading screen. The `ux` and `uy` functions for dynamic screen sizing were commented out, and fixed dimensions (`fixed_width`, `fixed_height`) are used for simplicity during troubleshooting.
    *   **APK Mounting Logic (Critical Section):**
        1.  `apk = "{{cookiecutter.archive}}.apk"`: Gets the name of the archive Pygbag creates (e.g., `temp_wasm_build_src.apk`).
        2.  `bundle = "{{cookiecutter.archive}}"`: The base name of the archive.
        3.  `appdir = Path(f"/data/data/{bundle}")`: Defines the target mount point in the Emscripten Virtual File System (VFS). This will be something like `/data/data/temp_wasm_build_src`.
        4.  `appdir.mkdir(parents=True, exist_ok=True)`: **This was a key fix.** It ensures that the entire path `/data/data/temp_wasm_build_src` is created as a directory within the VFS *before* BrowserFS (used by Pygbag) attempts to mount the APK onto it. This resolved earlier `ErrnoError` issues.
        5.  `code_root = appdir / "assets"`: **This is another critical piece.** It defines that your Python code and assets (which are at the root of your `TEMP_BUILD_SRC_DIR` and thus at the root of the APK) will be accessible under `/data/data/temp_wasm_build_src/assets/` in the VFS *after* the mount.
        6.  `cfg = { ... "mount" : { "point" : appdir.as_posix(), "path" : "/", } ... }`: This configures BrowserFS. It tells it to take the root (`/`) of the APK file and mount it at the `appdir` VFS path (`/data/data/temp_wasm_build_src`).
        7.  `track = platform.window.MM.prepare(apk, json.dumps(cfg))`: This JavaScript interop call initiates the download (if needed) and mounting of the APK.
        8.  The `while not track.ready:` loop displays a progress bar.
    *   **Python Environment Setup:**
        1.  `platform.run_main(PyConfig, loaderhome=code_root, loadermain=None)`: **This was the most crucial fix for running your code.**
            *   `loaderhome=code_root`: This tells the Python interpreter that its "home" directory (where it looks for main.py and other modules, and what `os.getcwd()` will initially be) is `/data/data/temp_wasm_build_src/assets/`.
            *   Since your Python files are at the root of the APK, and the APK's root is mounted at `appdir`, and you want Python to think its files are in an `assets` subdirectory of `appdir`, this makes everything line up.
    *   **Filesystem Checks:** The template includes `platform.window.console.log` statements to print `sys.path`, `os.getcwd()`, and `os.listdir(".")` after `platform.run_main`. This was vital for debugging and confirming that the CWD was correctly set to `/data/data/temp_wasm_build_src/assets` and that main.py was visible there.
    *   **Running Your Game's main.py:**
        1.  `await shell.runpy("main.py", callback=ui_callback)`: This executes your game's main.py script. Because `loaderhome` set the CWD correctly, `shell.runpy` can find main.py directly. The `await` is used because your main.py now contains an `async def main()` function.
    *   **Global Execution:**
        1.  `asyncio.run(custom_site())`: At the very end of the Python block in the template, this line actually executes the `custom_site` coroutine.

**In summary, the custom_pygbag.tmpl was modified to:**
1.  Ensure the VFS mount point directory exists before mounting.
2.  Tell Python (via `platform.run_main`'s `loaderhome`) that its effective root directory for code execution is `/data/data/your_archive_name/assets/`, even though the files in the APK are at its root and the APK is mounted at `/data/data/your_archive_name/`. This "simulates" an `assets` folder for Python's perspective.

### 3. Documentation for wasm_export.md

````markdown
# WebAssembly (WASM) Export Guide for RPG Engine

This document explains how the Python-based RPG Engine is packaged into a WebAssembly format to run in web browsers using Pygbag.

## Overview

The WASM export process bundles the game's Python scripts, necessary assets for a chosen map, and a Python interpreter (compiled to WASM) into a web-friendly application. This allows the game to be played directly in a browser without requiring users to install Python or Pygame.

The primary tools involved are:
*   **`export_wasm_single_map.py`**: A Python script to automate the packaging process.
*   **Pygbag**: A command-line tool that handles the bundling and WASM conversion.
*   **`custom_pygbag.tmpl`**: A customized HTML template that controls how Pygbag sets up the web page and initializes the Python environment in the browser.

## The `export_wasm_single_map.py` Script

This script orchestrates the export. Its main responsibilities include:

1.  **User Interaction**: Prompts the user to select a game map to be packaged.
2.  **Temporary Build Directory (`temp_wasm_build_src`)**:
    *   Creates a clean temporary directory.
    *   Copies all core Python game files (e.g., `main.py`, `game.py`, `engine.py`, etc.) to the root of this temporary directory.
    *   Creates a `data` subdirectory structure (`data/maps/`, `data/entities/`, `data/abilities/`) within the temporary directory.
3.  **Asset Management**:
    *   Copies the selected map's JSON file to `temp_wasm_build_src/data/maps/`.
    *   Identifies and copies only the entity JSON files referenced by the selected map to `temp_wasm_build_src/data/entities/`.
    *   Copies all ability JSON files to `temp_wasm_build_src/data/abilities/`.
4.  **Requirements**: Generates a `requirements.txt` file (specifying `pygame`) in the temporary directory for Pygbag.
5.  **Environment Variable**: Sets `WASM_DIRECT_MAP_NAME` to the chosen map's name. The game's `main.py` uses this variable to bypass menus and load the specified map directly when running in the WASM environment.
6.  **Pygbag Execution**:
    *   Invokes the `pygbag` command-line tool.
    *   Specifies the `temp_wasm_build_src` directory as the source for packaging.
    *   Crucially, it directs Pygbag to use the `custom_pygbag.tmpl` file as its HTML/bootstrap template.
7.  **Output Management**: Moves the final web application (generated by Pygbag) from its build location to `wasm_game_output/`.

## The `custom_pygbag.tmpl` File

This HTML template is vital for controlling the browser environment in which the Python code runs. It contains embedded Python code that Pygbag's JavaScript runtime executes.

Key functionalities of the Python code within this template:

1.  **Initialization (`async def custom_site()`):**
    *   Sets up basic Pygame for a loading screen (currently using fixed dimensions).
2.  **APK Mounting (Virtual File System Setup):**
    *   Pygbag packages the contents of `temp_wasm_build_src` into an archive (e.g., `temp_wasm_build_src.apk`).
    *   The template defines a mount point in the browser's virtual file system (VFS), typically `/data/data/temp_wasm_build_src`.
    *   **Critical Fix**: It programmatically creates this VFS directory path *before* attempting to mount the APK. This prevents filesystem errors.
    *   The entire content of the APK (which is the content of `temp_wasm_build_src`) is then mounted at this VFS location.
3.  **Python Environment Configuration:**
    *   **Critical Fix**: It calls `platform.run_main(PyConfig, loaderhome="/data/data/temp_wasm_build_src/assets", ...)`.
        *   This `loaderhome` parameter tells the Python interpreter running in WASM to consider `/data/data/temp_wasm_build_src/assets/` as its primary working directory and the root for module imports.
        *   Even though the Python files (`main.py`, etc.) are at the root of the APK (and thus at `/data/data/temp_wasm_build_src/` after mounting), this configuration makes Python behave as if they are in an `assets` subfolder. This aligns with how Pygbag typically structures things and simplifies path management for Python.
4.  **Executing the Game:**
    *   After setting up the environment, it calls `await shell.runpy("main.py")`.
    *   Since the `loaderhome` has correctly set the context, Python can find and execute `main.py` from the virtual `assets` directory.
5.  **Asynchronous Execution:** The entire `custom_site` function is asynchronous, and the game's `main.py` is also designed with an `async def main()` and uses `await asyncio.sleep(0)` in its main loop to yield control to the browser, preventing it from freezing.

## How to Use the Export Script

1.  Ensure Python and Pygame are installed in your environment.
2.  Install Pygbag: `pip install pygbag`
3.  Run the script from your project root: `python export_wasm_single_map.py`
4.  Follow the prompts to select a map.
5.  Once completed, the packaged web application will be in the `wasm_game_output/` directory.
6.  To run the game, navigate to `wasm_game_output/` in your terminal and start a local web server (e.g., `python -m http.server`).
7.  Open your web browser and go to the server address (e.g., `http://localhost:8000`).

## Troubleshooting Notes

*   **ModuleNotFoundError**: Ensure all necessary Python files are listed in `CORE_FILES` in `export_wasm_single_map.py`.
*   **File Not Found (Assets)**: Verify that paths in your game code correctly access assets relative to the CWD established by `loaderhome` (i.e., from the virtual `assets` directory). The `data` folder should be directly accessible as `data/maps/map_name.json`.
*   **Browser Console**: Always check the browser's developer console for error messages. Logs from `platform.window.console.log` in the template and `print()` statements from your Python code will appear here.
*   **Async/Await**: Ensure that asynchronous functions are correctly defined with `async def` and called with `await`. The main game loop in `main.py` must use `await asyncio.sleep(0)` to yield control.
````

## TODOs and Next Steps

1.  **Thorough WASM Testing:**
    *   Test all game mechanics, UI interactions, and map features in the exported WASM version.
    *   Verify that all entities load and behave correctly.
    *   Test different map complexities.
2.  **Asset Path Robustness:**
    *   Review all file loading paths in your Python code (data_manager.py, game.py, etc.).
    *   Ensure they are robust and work correctly given that the CWD in WASM will be `/data/data/your_archive_name/assets/`. Paths like `"data/maps/map_name.json"` should work directly.
3.  **Error Handling in WASM:**
    *   Implement a more user-friendly way to display critical errors in the WASM version if main.py or other core components fail to load or run (e.g., drawing an error message to the Pygame screen instead of relying solely on browser console logs).
4.  **Conditional Editor Logic for WASM:**
    *   In main.py, the `from editor import Editor` and `editor = Editor(screen)` calls happen even if `WASM_DIRECT_MAP_NAME` is set (though `editor` object might not be used).
    *   For a cleaner direct-to-game WASM export, you might want to make the import and instantiation of `Editor` strictly conditional on `WASM_DIRECT_MAP_NAME` *not* being set, to avoid loading editor code if it's truly not needed for gameplay.
    ```python
    # main.py
    # ...
    if not WASM_DIRECT_MAP_NAME:
        from editor import Editor # Import only if not in direct map mode
        # ... instantiate editor ...
    # ...
    ```
5.  **AI Behavior Warnings:**
    *   Address the "Warning: Unknown behavior 'player_controlled'. Defaulting to AggressiveMelee." and similar warnings. Ensure that all behavior types specified in your entity JSON files are correctly implemented in ai.py and registered or handled by `create_behavior`.
6.  **Cleanup Debug Prints:**
    *   Remove or comment out excessive `print()` statements used for debugging from both your Python game code and the custom_pygbag.tmpl once everything is stable.
7.  **Dynamic Screen Sizing (Optional):**
    *   If you want the game to adapt to browser window size, you'll need to revisit the `ux`, `uy` functions (or similar logic) in custom_pygbag.tmpl. This requires careful interaction with `platform.window` and `platform.document` properties. For now, fixed size is simpler.
8.  **Optimize Assets:**
    *   For web deployment, consider optimizing the size of your JSON data files or any image/sound assets you might add later.
9.  **Documentation Update:**
    *   Keep wasm_export.md and other documentation updated as you refine the export process or game features.