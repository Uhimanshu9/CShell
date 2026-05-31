import curses
import random
import time
import os

# ====================================================================================== #
# COLOR AND GRAPHICS HELPERS
# ====================================================================================== #

def init_game_colors():
    """Initializes terminal color pairs for rich game aesthetics if supported."""
    if curses.has_colors():
        curses.use_default_colors()
        # Pair 1: Walls and heavy blocks (Blue on Default background)
        curses.init_pair(1, curses.COLOR_BLUE, -1)
        # Pair 2: Player and friendly units (Green on Default background)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        # Pair 3: Exits, hazards, and locks (Red on Default background)
        curses.init_pair(3, curses.COLOR_RED, -1)
        # Pair 4: Treasures, keys, and alerts (Yellow on Default background)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        # Pair 5: Paths, borders, and menus (Cyan on Default background)
        curses.init_pair(5, curses.COLOR_CYAN, -1)


# ====================================================================================== #
# GAME 1: SHIP DODGER
# ====================================================================================== #

def create_board(width, height):
    """Initializes and returns the Ship Dodger game state dictionary."""
    return {
        "width": width,
        "height": height,
        "ship_x": width // 2,
        "stones": [],
        "score": 0,
        "speed": 0.12,  # Frame delay (lower is faster)
        "game_over": False
    }

def ship_dodger_main(stdscr):
    """Main runner for the Ship Dodger game using real-time loop updates and retro graphics."""
    width, height = 20, 15
    state = create_board(width, height)
    
    curses.curs_set(0)          # Hide cursor
    stdscr.nodelay(True)        # Non-blocking input
    stdscr.keypad(True)         # Enable keyboard arrows
    
    last_stone_fall_time = time.time()
    
    has_colors = curses.has_colors()
    color_cyan = curses.color_pair(5) if has_colors else curses.A_NORMAL
    color_yellow = curses.color_pair(4) if has_colors else curses.A_NORMAL
    color_red = curses.color_pair(3) if has_colors else curses.A_NORMAL
    color_green = curses.color_pair(2) if has_colors else curses.A_NORMAL
    color_blue = curses.color_pair(1) if has_colors else curses.A_NORMAL

    while not state["game_over"]:
        current_time = time.time()
        
        # 1. Handle Input (non-blocking check)
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            break
        elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
            if state["ship_x"] > 0:
                state["ship_x"] -= 1
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            if state["ship_x"] < width - 1:
                state["ship_x"] += 1
                
        # 2. Update Stones and Difficulty
        if current_time - last_stone_fall_time >= state["speed"]:
            new_stones = []
            for sx, sy in state["stones"]:
                if sy + 1 < height:
                    new_stones.append((sx, sy + 1))
            state["stones"] = new_stones
            
            spawn_prob = min(0.25 + (state["score"] / 200), 0.6)
            if random.random() < spawn_prob:
                state["stones"].append((random.randint(0, width - 1), 0))
                
            last_stone_fall_time = current_time
            state["score"] += 1
            state["speed"] = max(0.12 - (state["score"] / 400) * 0.08, 0.04)

        # 3. Collision Detection
        for sx, sy in state["stones"]:
            if sy == height - 1 and sx == state["ship_x"]:
                state["game_over"] = True
                break
                
        # 4. Render Board Frame
        stdscr.clear()
        term_height, term_width = stdscr.getmaxyx()
        offset_y = max(0, (term_height - height - 4) // 2)
        offset_x = max(0, (term_width - width * 2 - 2) // 2)
        
        speed_multiplier = int(120 // (state["speed"] * 100))
        stdscr.addstr(offset_y, offset_x, f"SCORE: {state['score']}  |  SPEED LEVEL: {speed_multiplier}", color_yellow | curses.A_BOLD)
        
        # Premium double-line top border
        stdscr.addstr(offset_y + 1, offset_x, "╔" + "═" * (width * 2) + "╗", color_cyan)
        
        for r in range(height):
            stdscr.addstr(offset_y + 2 + r, offset_x, "║", color_cyan)
            
            for c in range(width):
                is_stone = False
                for sx, sy in state["stones"]:
                    if sx == c and sy == r:
                        is_stone = True
                        break
                
                if r == height - 1 and c == state["ship_x"]:
                    stdscr.addstr("🚀", color_green | curses.A_BOLD)
                elif is_stone:
                    stdscr.addstr("☄ ", color_red | curses.A_BOLD)
                else:
                    stdscr.addstr("  ")
                    
            stdscr.addstr("║", color_cyan)
            
        # Premium double-line bottom border
        stdscr.addstr(offset_y + 2 + height, offset_x, "╚" + "═" * (width * 2) + "╝", color_cyan)
        stdscr.addstr(offset_y + 3 + height, offset_x, "A/D or Arrows: Move | Q: Quit", color_cyan)
        
        stdscr.refresh()
        time.sleep(0.01)
        
    # Game Over screen
    stdscr.nodelay(False)
    stdscr.clear()
    term_height, term_width = stdscr.getmaxyx()
    
    go_lines = [
        "╔═════════════════════════════════════╗",
        "║             GAME OVER!              ║",
        "╠═════════════════════════════════════╣",
        "║                                     ║",
        f"║        FINAL SCORE: {state['score']}       ║",
        "║                                     ║",
        "╚═════════════════════════════════════╝",
        "     Press any key to return...      "
    ]
    
    for idx, line in enumerate(go_lines):
        y = max(0, (term_height // 2) - len(go_lines) // 2 + idx)
        x = max(0, (term_width // 2) - len(line) // 2)
        if "║" in line or "╔" in line or "╠" in line or "╚" in line:
            stdscr.addstr(y, x, line, color_red | curses.A_BOLD)
        else:
            stdscr.addstr(y, x, line, color_yellow | curses.A_BOLD)
        
    stdscr.refresh()
    stdscr.getch()


# ====================================================================================== #
# GAME 2: MAZE ESCAPE
# ====================================================================================== #

def load_maze(level_idx=0):
    """Loads and returns the 2D grid and variables representing the level's state.
    
    Allows full customization of mazes, supporting extensible entities:
    '#' = Wall, 'P' = Player, 'E' = Exit, 'K' = Key, 'D' = Lock Door, '$' = Treasure
    """
    levels = [
        # Level 1: Simple introductory tutorial maze with treasures
        [
            "###########",
            "#P........#",
            "#.##..#.#.#",
            "#...$.#.#E#",
            "###########"
        ],
        # Level 2: Challenging puzzle with a locked door 'D', key 'K', and collectibles '$'
        [
            "###############",
            "#P#...........#",
            "#.#.#########.#",
            "#...#.......#.#",
            "#####.#.###.#.#",
            "#.#...#.#.#.#.#",
            "#.#.###.#.#.#.#",
            "#.....#.$.#...#",
            "#####.#####.###",
            "#...#.#...#.#.#",
            "#K#.#.#.#.#.#.#",
            "#.#...#.#...#.#",
            "#.#####D#####.#",
            "#......$......E",
            "###############"
        ],
        # Level 3: Large, complicated, winding maze
        [
            "###################",
            "#P#.......#.......#",
            "#.#.#####.#.#####.#",
            "#...#...#...#...#.#",
            "#####.#.#####.#.#.#",
            "#...#.#.#...#.#.#.#",
            "#.#.###.#.###.###.#",
            "#.#...........#...#",
            "#.#############.###",
            "#.#...........#.#.#",
            "#.#.#########.#.#.#",
            "#.#.#.......#.#.#.#",
            "#.#.#.#####.#.#.#.#",
            "#...#.#...#.#...#.#",
            "#####.#.#.#####.###",
            "#.....#.#.......#.#",
            "#.#####.#########.#",
            "#.................E",
            "###################"
        ]
    ]
    
    grid = [list(row) for row in levels[level_idx]]
    player_y, player_x = 0, 0
    
    # Locate starting coordinate of the player 'P'
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] == 'P':
                player_y, player_x = r, c
                grid[r][c] = '.'  # Clear coordinate in raw grid (track player separately)
                
    return {
        "grid": grid,
        "player_y": player_y,
        "player_x": player_x,
        "has_key": False,
        "score": 0,
        "treasures_total": sum(row.count('$') for row in levels[level_idx]),
        "treasures_collected": 0,
        "fog_of_war": False,
        "level": level_idx + 1,
        "win": False,
        "start_time": time.time()  # Initialize the countdown timer reference for this level
    }

def render_maze(stdscr, state, offset_y, offset_x, maze_h, maze_w, message, num_levels, time_left):
    """Draws the current frame of the maze onto the curses screen with double-line cabinet frames."""
    has_colors = curses.has_colors()
    color_cyan = curses.color_pair(5) if has_colors else curses.A_NORMAL
    color_yellow = curses.color_pair(4) if has_colors else curses.A_NORMAL
    color_red = curses.color_pair(3) if has_colors else curses.A_NORMAL
    color_green = curses.color_pair(2) if has_colors else curses.A_NORMAL
    color_blue = curses.color_pair(1) if has_colors else curses.A_NORMAL

    # Print stats and configuration (aligned single-line block to avoid overlaps)
    prefix = f"LEVEL: {state['level']}/{num_levels} | SCORE: {state['score']} | "
    stdscr.addstr(offset_y, offset_x, prefix, curses.A_BOLD)
    
    timer_str = f"TIME LEFT: {int(time_left)}s"
    if time_left < 10:
        stdscr.addstr(offset_y, offset_x + len(prefix), timer_str, color_red | curses.A_BOLD)
    else:
        stdscr.addstr(offset_y, offset_x + len(prefix), timer_str, color_yellow | curses.A_BOLD)
        
    stdscr.addstr(offset_y + 1, offset_x, f"TREASURES: {state['treasures_collected']}/{state['treasures_total']} | KEY: {'YES' if state['has_key'] else 'NO'} | FOG: {'ON' if state['fog_of_war'] else 'OFF'}")
    
    # Draw top border with double-line box drawing characters
    stdscr.addstr(offset_y + 2, offset_x, "╔" + "═" * (maze_w * 2) + "╗", color_cyan)

    # Render each row
    for r in range(maze_h):
        stdscr.addstr(offset_y + 3 + r, offset_x, "║", color_cyan)
        
        for c in range(maze_w):
            # Fog of War coordinate verification
            if state["fog_of_war"]:
                dist = max(abs(r - state["player_y"]), abs(c - state["player_x"]))
                if dist > 3:
                    stdscr.addstr("  ")  # Draw as pitch-black empty cells
                    continue
            
            # Check player draw (Space Alien emoji)
            if r == state["player_y"] and c == state["player_x"]:
                stdscr.addstr("👾", color_green | curses.A_BOLD)
                continue
                
            char = state["grid"][r][c]
            if char == '#':
                stdscr.addstr("██", color_blue)
            elif char == 'E':
                stdscr.addstr("🏁", color_red | curses.A_BOLD)
            elif char == 'K':
                stdscr.addstr("🔑", color_yellow | curses.A_BOLD)
            elif char == 'D':
                stdscr.addstr("🧱", color_red | curses.A_BOLD)
            elif char == '$':
                stdscr.addstr("💎", color_yellow | curses.A_BOLD)
            else:
                stdscr.addstr("· ", color_cyan)
                
        stdscr.addstr("║", color_cyan)
        
    # Draw bottom border
    stdscr.addstr(offset_y + 3 + maze_h, offset_x, "╚" + "═" * (maze_w * 2) + "╝", color_cyan)
    
    # Render action feedback message
    stdscr.addstr(offset_y + 4 + maze_h, offset_x, f"Status: {message}", color_yellow | curses.A_BOLD)
    stdscr.addstr(offset_y + 5 + maze_h, offset_x, "HINT: Apply Dijkstra's algorithm to solve!", color_yellow | curses.A_BOLD)
    stdscr.addstr(offset_y + 6 + maze_h, offset_x, "W/A/S/D or Arrows: Move | F: Fog of War | Q: Quit", color_cyan)

def move_player(state, dy, dx, maze_h, maze_w):
    """Validates movement rules, collects entities, and updates player location."""
    ny = state["player_y"] + dy
    nx = state["player_x"] + dx
    
    # Boundary check
    if ny < 0 or ny >= maze_h or nx < 0 or nx >= maze_w:
        return "Boundary limit reached!"
        
    target = state["grid"][ny][nx]
    
    if target == '#':
        return "You collided with a solid wall!"
        
    elif target == 'D':
        if state["has_key"]:
            state["grid"][ny][nx] = '.'
            state["has_key"] = False
            state["player_y"], state["player_x"] = ny, nx
            state["score"] += 50
            return "Unlocked Locked Door! +50 pts"
        else:
            return "The Door is Locked! Find the Key (K)."
            
    elif target == 'K':
        state["grid"][ny][nx] = '.'
        state["has_key"] = True
        state["player_y"], state["player_x"] = ny, nx
        state["score"] += 50
        return "Collected the Key! +50 pts"
        
    elif target == '$':
        state["grid"][ny][nx] = '.'
        state["treasures_collected"] += 1
        state["score"] += 100
        state["player_y"], state["player_x"] = ny, nx
        return "Discovered Gold Treasure! +100 pts"
        
    elif target == 'E':
        state["player_y"], state["player_x"] = ny, nx
        state["win"] = True
        return "Arrived at Exit!"
        
    else:  # Path '.'
        state["player_y"], state["player_x"] = ny, nx
        return ""

def maze_escape_main(stdscr):
    """Main Maze Escape game loop with real-time countdown timer."""
    curses.curs_set(0)
    stdscr.nodelay(True)  # Turn-based movement but non-blocking timer updates
    stdscr.keypad(True)
    stdscr.timeout(100)   # Check input every 100ms to update time countdown
    
    current_level = 0
    num_levels = 3        # Expanded to 3 challenging levels!
    state = load_maze(current_level)
    message = "Locate the Exit (E)!"
    
    has_colors = curses.has_colors()
    color_yellow = curses.color_pair(4) if has_colors else curses.A_NORMAL
    color_red = curses.color_pair(3) if has_colors else curses.A_NORMAL
    
    while True:
        # Evaluate timer state
        elapsed = time.time() - state["start_time"]
        time_left = max(0.0, 30.0 - elapsed)
        
        if time_left <= 0:
            # 30-Second Limit Defeat / Insult Screen
            stdscr.timeout(-1)  # Restore blocking input for text display
            stdscr.clear()
            term_h, term_w = stdscr.getmaxyx()
            
            # Force user to wait for 5 seconds staring at the insult
            for wait_sec in range(5, 0, -1):
                stdscr.clear()
                # Big, flashing red banner at the very top of the screen
                stdscr.addstr(1, max(0, (term_w - 53) // 2), "*****************************************************", color_red | curses.A_BOLD | curses.A_BLINK)
                stdscr.addstr(2, max(0, (term_w - 53) // 2), "*  YOUR DEGREE IS WORTHLESS IF YOU CAN'T SOLVE THIS! *", color_red | curses.A_BOLD | curses.A_BLINK)
                stdscr.addstr(3, max(0, (term_w - 53) // 2), "*****************************************************", color_red | curses.A_BOLD | curses.A_BLINK)
                
                fail_lines = [
                    "╔═════════════════════════════════════╗",
                    "║             TIME'S UP!              ║",
                    "╠═════════════════════════════════════╣",
                    "║                                     ║",
                    "║       Your degree is worthless      ║",
                    "║        if you can't solve this!     ║",
                    "║                                     ║",
                    "╚═════════════════════════════════════╝",
                    f"     Stare at this for: {wait_sec}s...      "
                ]
                for idx, line in enumerate(fail_lines):
                    y = max(0, (term_h // 2) - len(fail_lines) // 2 + idx)
                    x = max(0, (term_w // 2) - len(line) // 2)
                    if "║" in line or "╔" in line or "╠" in line or "╚" in line:
                        stdscr.addstr(y, x, line, color_red | curses.A_BOLD)
                    else:
                        stdscr.addstr(y, x, line, color_red)
                stdscr.refresh()
                time.sleep(1.0)
                
            # Clear any pending keypresses by making input non-blocking temporarily
            stdscr.nodelay(True)
            while stdscr.getch() != -1:
                pass
            
            # Now let them exit by pressing any key
            stdscr.nodelay(False)
            stdscr.clear()
            
            # Static banner on exit option
            stdscr.addstr(1, max(0, (term_w - 53) // 2), "*****************************************************", color_red | curses.A_BOLD)
            stdscr.addstr(2, max(0, (term_w - 53) // 2), "*  YOUR DEGREE IS WORTHLESS IF YOU CAN'T SOLVE THIS! *", color_red | curses.A_BOLD)
            stdscr.addstr(3, max(0, (term_w - 53) // 2), "*****************************************************", color_red | curses.A_BOLD)
            
            fail_lines = [
                "╔═════════════════════════════════════╗",
                "║             TIME'S UP!              ║",
                "╠═════════════════════════════════════╣",
                "║                                     ║",
                "║       Your degree is worthless      ║",
                "║        if you can't solve this!     ║",
                "║                                     ║",
                "╚═════════════════════════════════════╝",
                "     Press any key to return...      "
            ]
            for idx, line in enumerate(fail_lines):
                y = max(0, (term_h // 2) - len(fail_lines) // 2 + idx)
                x = max(0, (term_w // 2) - len(line) // 2)
                if "║" in line or "╔" in line or "╠" in line or "╚" in line:
                    stdscr.addstr(y, x, line, color_red | curses.A_BOLD)
                else:
                    stdscr.addstr(y, x, line, color_red)
            stdscr.refresh()
            stdscr.getch()
            break
            
        stdscr.clear()
        
        maze_h = len(state["grid"])
        maze_w = len(state["grid"][0])
        term_h, term_w = stdscr.getmaxyx()
        
        # Calculate dynamic offsets to center render contents
        offset_y = max(0, (term_h - maze_h - 7) // 2)
        offset_x = max(0, (term_w - maze_w * 2 - 2) // 2)
        
        # Render the board frame
        render_maze(stdscr, state, offset_y, offset_x, maze_h, maze_w, message, num_levels, time_left)
        stdscr.refresh()
        
        # Get user command
        key = stdscr.getch()
        dy, dx = 0, 0
        
        if key == -1:
            # Idle input, tick the timer
            continue
            
        if key in (ord('q'), ord('Q')):
            break
        elif key in (ord('f'), ord('F')):
            state["fog_of_war"] = not state["fog_of_war"]
            message = f"Fog of War {'ENABLED' if state['fog_of_war'] else 'DISABLED'}!"
            continue
        elif key in (curses.KEY_UP, ord('w'), ord('W')):
            dy, dx = -1, 0
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            dy, dx = 1, 0
        elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
            dy, dx = 0, -1
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            dy, dx = 0, 1
        else:
            continue
            
        # Update move actions
        message = move_player(state, dy, dx, maze_h, maze_w)
        
        # Evaluate Win State
        if state["win"]:
            stdscr.clear()
            term_h, term_w = stdscr.getmaxyx()
            
            if current_level + 1 < num_levels:
                current_level += 1
                next_level = load_maze(current_level)
                next_level["score"] += state["score"]
                state = next_level
                message = f"Level Completed! ESCAPE LEVEL {current_level + 1}!"
            else:
                # Absolute game escape success screen
                win_lines = [
                    "╔═════════════════════════════════════╗",
                    "║        YOU ESCAPED THE MAZE!        ║",
                    "╠═════════════════════════════════════╣",
                    "║                                     ║",
                    f"║        FINAL SCORE: {state['score']}       ║",
                    "║           Congratulations!          ║",
                    "║                                     ║",
                    "╚═════════════════════════════════════╝",
                    "     Press any key to return...      "
                ]
                for idx, line in enumerate(win_lines):
                    y = max(0, (term_h // 2) - len(win_lines) // 2 + idx)
                    x = max(0, (term_w // 2) - len(line) // 2)
                    if "║" in line or "╔" in line or "╠" in line or "╚" in line:
                        stdscr.addstr(y, x, line, color_yellow | curses.A_BOLD)
                    else:
                        stdscr.addstr(y, x, line, color_yellow)
                stdscr.refresh()
                stdscr.timeout(-1)  # Restore blocking input
                stdscr.getch()
                break


# ====================================================================================== #
# SYSTEM INITIALIZATION & MAIN GAMES MENU
# ====================================================================================== #

def draw_menu(stdscr):
    """Renders the terminal games selection menu and returns the user's choice."""
    stdscr.nodelay(False)
    stdscr.timeout(-1)  # Enable standard blocking input for menu selections
    stdscr.clear()
    
    height, width = stdscr.getmaxyx()
    
    # Large 3D Arcade Title
    title = [
        "  ██████╗  █████╗ ███╗   ███╗███████╗███████╗",
        "  ██╔════╝ ██╔══██╗████╗ ████║██╔════╝██╔════╝",
        "  ██║  ███╗███████║██╔████╔██║█████╗  ███████╗",
        "  ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  ╚════██║",
        "  ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗███████║",
        "   ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝"
    ]
    
    menu_lines = [
        "╔═════════════════════════════════════════════════╗",
        "║               TERMINAL ARCADE MENU              ║",
        "╠═════════════════════════════════════════════════╣",
        "║                                                 ║",
        "║  [1] 🚀 SHIP DODGER  (Avoid falling Meteors)    ║",
        "║  [2] 👾 MAZE ESCAPE  (Dungeon Explorer Puzzle)  ║",
        "║  [3] 🚪 EXIT ARCADE                             ║",
        "║                                                 ║",
        "╚═════════════════════════════════════════════════╝",
        "Press [1], [2], or [3] to select a game..."
    ]
    
    has_colors = curses.has_colors()
    color_yellow = curses.color_pair(4) if has_colors else curses.A_NORMAL
    color_cyan = curses.color_pair(5) if has_colors else curses.A_NORMAL
    
    # Draw Title
    title_start_y = max(0, (height // 2) - (len(title) + len(menu_lines)) // 2)
    for idx, line in enumerate(title):
        stdscr.addstr(title_start_y + idx, max(0, (width - len(line)) // 2), line, color_yellow | curses.A_BOLD)
        
    # Draw Menu Frame
    menu_start_y = title_start_y + len(title) + 1
    for idx, line in enumerate(menu_lines):
        y = menu_start_y + idx
        x = max(0, (width - len(line)) // 2)
        if "║" in line or "╔" in line or "╠" in line or "╚" in line:
            stdscr.addstr(y, x, line, color_yellow | curses.A_BOLD)
        else:
            stdscr.addstr(y, x, line, color_cyan)
            
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key == ord('1'):
            return "ship_dodger"
        elif key == ord('2'):
            return "maze_escape"
        elif key in (ord('3'), 27):  # 3 is exit, 27 is Escape
            return "exit"

def run_games_system():
    """Wrapper function to execute games within a curses terminal session."""
    try:
        def main_menu(stdscr):
            init_game_colors()  # Initialize color systems once
            while True:
                choice = draw_menu(stdscr)
                if choice == "ship_dodger":
                    ship_dodger_main(stdscr)
                elif choice == "maze_escape":
                    maze_escape_main(stdscr)
                elif choice == "exit":
                    break
                    
        curses.wrapper(main_menu)
    except Exception as e:
        print(f"Error starting game session: {e}")
