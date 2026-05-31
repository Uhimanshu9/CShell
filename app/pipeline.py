import sys
import os


def is_builtin(command_name: str, commands_dict: dict) -> bool:
    """
    Check if command_name is a built-in shell command.
    
    Args:
        command_name: Name of the command (e.g., 'echo', 'type')
        commands_dict: The commands dictionary from main.py
    
    Returns:
        True if command is built-in, False otherwise
    """
    return command_name in commands_dict


def execute_command_in_child(cmd_list: list[str], commands_dict: dict) -> None:
    """
    Execute a command in a child process.
    
    If built-in: call the Python function, then exit child.
    If external: use os.execvp() to replace the process.
    
    Args:
        cmd_list: e.g., ['echo', 'hello'] or ['cat', 'file.txt']
        commands_dict: the commands dict from main.py
    
    NOTE: This function ALWAYS exits the child process (never returns to caller).
          This is called only from child processes forked in execute_pipeline().
    """
    if not cmd_list:
        os._exit(1)
    
    command_name = cmd_list[0]
    args = cmd_list[1:]
    
    if is_builtin(command_name, commands_dict):
        # Built-in command: call the Python function in the child
        try:
            # Flush stdout/stderr to ensure no buffering issues
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Call the built-in function
            commands_dict[command_name](args)
            
            # Flush again after execution
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Exit child successfully
            os._exit(0)
        except SystemExit:
            # handle_exit() calls sys.exit()
            # In a child process, convert this to os._exit()
            os._exit(0)
        except BrokenPipeError:
            # Right side of pipeline closed early (e.g., head -n 5)
            # This is normal - don't print error
            os._exit(0)
        except Exception as e:
            # Unexpected error in built-in
            print(f"Error in {command_name}: {e}", file=sys.stderr)
            os._exit(1)
    else:
        # External command: use os.execvp() to replace the process
        try:
            os.execvp(command_name, cmd_list)
            # execvp() never returns if successful
        except OSError:
            # Command not found or other OS error
            print(f"{command_name}: command not found", file=sys.stderr)
            os._exit(127)


def execute_pipeline(left_cmd: list[str], right_cmd: list[str], commands_dict: dict) -> None:
    """
    Execute two commands connected by a pipe: left_cmd | right_cmd
    
    Both sides can be built-in or external commands.
    This function handles all combinations:
    - external | external
    - builtin | external
    - external | builtin
    - builtin | builtin
    
    Args:
        left_cmd: list like ['cat', 'file.txt'] or ['echo', 'hello']
        right_cmd: list like ['wc', '-l'] or ['type', 'echo']
        commands_dict: the commands dict from main.py containing built-in handlers
    
    This function:
    1. Creates a pipe using os.pipe()
    2. Forks first child for left command (built-in or external)
    3. Forks second child for right command (built-in or external)
    4. Parent waits for both children
    5. Ensures commands run concurrently
    """
    # Step 1: Create a pipe
    # os.pipe() returns (read_fd, write_fd) - typically (3, 4)
    read_fd, write_fd = os.pipe()
    
    # Step 2: Fork the first child (left command)
    pid1 = os.fork()
    if pid1 == 0:  # Child 1 process
        # Redirect stdout (fd 1) to pipe write end
        # This makes all print() calls write to the pipe
        os.dup2(write_fd, 1)
        
        # Close unused file descriptors
        # (os.dup2 creates a copy; we close the originals)
        os.close(read_fd)   # Child 1 doesn't read from pipe
        os.close(write_fd)  # Close original after dup2
        
        # Execute command (built-in or external)
        # This function will os._exit() the child
        execute_command_in_child(left_cmd, commands_dict)
    
    # Step 3: Fork the second child (right command)
    pid2 = os.fork()
    if pid2 == 0:  # Child 2 process
        # Redirect stdin (fd 0) to pipe read end
        # This makes all input operations read from the pipe
        os.dup2(read_fd, 0)
        
        # Close unused file descriptors
        os.close(read_fd)   # Close original after dup2
        os.close(write_fd)  # Child 2 doesn't write to pipe
        
        # Execute command (built-in or external)
        # This function will os._exit() the child
        execute_command_in_child(right_cmd, commands_dict)
    
    # Step 4: Parent cleanup and wait
    # CRITICAL: Parent must close both pipe fds.
    # If parent keeps them open, Child 2 won't get EOF when reading.
    os.close(read_fd)
    os.close(write_fd)
    
    # Wait for both children to finish
    # This blocks until both processes exit
    # Child 1 writes to pipe, then exits
    # Child 2 reads from pipe, then exits
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)
