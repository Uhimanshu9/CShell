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


def parse_pipeline(parts: list[str]) -> list[list[str]] | None:
    """
    Parse a command line with pipes into separate command stages.
    
    Input:  ['cat', 'file.txt', '|', 'head', '-n', '3', '|', 'wc']
    Output: [['cat', 'file.txt'], ['head', '-n', '3'], ['wc']]
    
    Args:
        parts: List of parsed command tokens
    
    Returns:
        List of command stages (each stage is a list of tokens)
        Returns None if '|' is first or last, or if empty stages found
    """
    if not parts or '|' not in parts:
        return None
    
    stages = []
    current_stage = []
    
    for part in parts:
        if part == '|':
            # End of current stage
            if not current_stage:
                # Empty stage (e.g., "cmd1 | | cmd2")
                return None
            stages.append(current_stage)
            current_stage = []
        else:
            current_stage.append(part)
    
    # Add final stage
    if not current_stage:
        # Empty final stage
        return None
    stages.append(current_stage)
    
    # Return only if we have 2+ stages (otherwise use two-stage pipeline)
    return stages if len(stages) >= 2 else None


def create_pipes(num_pipes: int) -> list[tuple[int, int]]:
    """
    Create N pipes for a multi-stage pipeline.
    
    For N commands, we need N-1 pipes.
    
    Args:
        num_pipes: Number of pipes to create (should be num_commands - 1)
    
    Returns:
        List of (read_fd, write_fd) tuples, one per pipe
    
    Example:
        For 3 commands: create_pipes(2) returns [(3, 4), (5, 6)]
    """
    pipes = []
    for _ in range(num_pipes):
        read_fd, write_fd = os.pipe()
        pipes.append((read_fd, write_fd))
    return pipes


def close_all_pipes(pipes: list[tuple[int, int]]) -> None:
    """
    Close all pipe file descriptors.
    
    Used by parent process after forking all children.
    
    Args:
        pipes: List of (read_fd, write_fd) tuples
    """
    for read_fd, write_fd in pipes:
        os.close(read_fd)
        os.close(write_fd)


def execute_multi_stage_pipeline(stages: list[list[str]], commands_dict: dict) -> None:
    """
    Execute N commands in a multi-stage pipeline.
    
    Example:
        stages = [['cat', 'file.txt'], ['head', '-n', '5'], ['wc']]
        This executes: cat file.txt | head -n 5 | wc
    
    Args:
        stages: List of command stages, each as [command, arg1, arg2, ...]
        commands_dict: Dictionary of built-in commands
    
    Process:
    1. Create N-1 pipes for N commands
    2. Fork N child processes
    3. For each child i (0 to N-1):
       - If i > 0: redirect stdin from pipes[i-1].read
       - If i < N-1: redirect stdout to pipes[i].write
       - Close all unused pipe file descriptors
       - Execute command
    4. Parent: close all pipes, wait for all children
    """
    num_stages = len(stages)
    
    # Create N-1 pipes for N stages
    pipes = create_pipes(num_stages - 1)
    pids = []
    
    # Fork one child per stage
    for i, stage in enumerate(stages):
        pid = os.fork()
        
        if pid == 0:  # Child process
            # Setup stdin: read from pipe (unless first stage)
            if i > 0:
                # Not first stage: read from previous pipe
                os.dup2(pipes[i - 1][0], 0)  # Redirect stdin
            
            # Setup stdout: write to pipe (unless last stage)
            if i < num_stages - 1:
                # Not last stage: write to current pipe
                os.dup2(pipes[i][1], 1)  # Redirect stdout
            
            # Close ALL pipe file descriptors in child
            # This is CRITICAL - child must not hold any pipes
            for read_fd, write_fd in pipes:
                os.close(read_fd)
                os.close(write_fd)
            
            # Execute the command (built-in or external)
            execute_command_in_child(stage, commands_dict)
        else:
            # Parent process: save child PID
            pids.append(pid)
    
    # Parent cleanup: close all pipe file descriptors
    # This allows children to get EOF when pipes are closed
    close_all_pipes(pipes)
    
    # Parent wait: wait for all children to finish
    for pid in pids:
        os.waitpid(pid, 0)


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
