"""History management for the shell.

Provides command history tracking with support for:
- Reading history from file (-r flag)
- Writing history to file (-w flag)
- Appending history to file (-a flag)
- Displaying history with optional limit
"""

import os
import sys

# Global list to track command history for the history builtin
COMMAND_HISTORY: list[str] = []

# How many commands have been written/synced to file
COMMAND_HISTORY_SYNCED: int = 0

# History file path - respects HISTFILE environment variable
HISTORY_FILE: str = os.path.expanduser(os.environ.get("HISTFILE", "~/.shell_history"))


def handle_history(args):
    """Handle the history builtin command.
    
    Supports:
    - history: Display all commands
    - history N: Display last N commands
    - history -r [file]: Read history from file
    - history -w [file]: Write all history to file
    - history -a [file]: Append new history to file
    """
    global COMMAND_HISTORY_SYNCED
    try:
        # Check for -r flag (read history file)
        if args and args[0] == "-r":
            # Determine which file to read from
            history_file_to_read = HISTORY_FILE  # default
            if len(args) > 1:
                history_file_to_read = args[1]  # use the provided path
            
            if os.path.exists(history_file_to_read):
                try:
                    with open(history_file_to_read, 'r') as f:
                        for line in f:
                            line = line.rstrip('\n\r')
                            if line and line not in COMMAND_HISTORY:
                                COMMAND_HISTORY.append(line)
                except Exception:
                    pass
            return
        
        # Check for -w flag (write history file)
        if args and args[0] == "-w":
            # Determine which file to write to
            history_file_to_write = HISTORY_FILE  # default
            if len(args) > 1:
                history_file_to_write = args[1]  # use the provided path
            
            try:
                with open(history_file_to_write, 'w') as f:
                    for cmd in COMMAND_HISTORY:
                        f.write(cmd + '\n')
                COMMAND_HISTORY_SYNCED = len(COMMAND_HISTORY)
            except Exception:
                pass
            return
        
        # Check for -a flag (append history file)
        if args and args[0] == "-a":
            # Determine which file to append to
            history_file_to_append = HISTORY_FILE  # default
            if len(args) > 1:
                history_file_to_append = args[1]  # use the provided path
            
            try:
                with open(history_file_to_append, 'a') as f:
                    # Only append commands that haven't been written yet
                    for i in range(COMMAND_HISTORY_SYNCED, len(COMMAND_HISTORY)):
                        f.write(COMMAND_HISTORY[i] + '\n')
                COMMAND_HISTORY_SYNCED = len(COMMAND_HISTORY)
            except Exception:
                pass
            return
        
        # Determine how many history items to display
        num_to_display = None
        if args:
            try:
                num_to_display = int(args[0])
            except (ValueError, IndexError):
                print("history: invalid argument")
                return
        
        # Use manual history list (reliably populated)
        if not COMMAND_HISTORY:
            return
        
        # Determine which items to display
        start_index = 0
        if num_to_display is not None:
            start_index = max(0, len(COMMAND_HISTORY) - num_to_display)
        
        # Print history items with 1-indexed line numbers
        for i in range(start_index, len(COMMAND_HISTORY)):
            line_number = i + 1
            print(f"{line_number:5}  {COMMAND_HISTORY[i]}")
    except BrokenPipeError:
        # Right side of pipeline closed early
        os._exit(0)


def load_history_file():
    """Load history from file into COMMAND_HISTORY on startup."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                for line in f:
                    line = line.rstrip('\n\r')
                    if line and line not in COMMAND_HISTORY:
                        COMMAND_HISTORY.append(line)
        except Exception:
            pass


def save_history_file():
    """Save all history to file on exit."""
    global COMMAND_HISTORY_SYNCED
    try:
        with open(HISTORY_FILE, 'w') as f:
            for cmd in COMMAND_HISTORY:
                f.write(cmd + '\n')
        COMMAND_HISTORY_SYNCED = len(COMMAND_HISTORY)
    except Exception:
        pass
