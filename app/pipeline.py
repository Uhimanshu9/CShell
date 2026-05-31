import sys
import os


def execute_pipeline(left_cmd, right_cmd):
    """
    Execute two commands connected by a pipe: left_cmd | right_cmd
    
    Args:
        left_cmd: list like ['cat', 'file.txt']
        right_cmd: list like ['wc', '-l']
    
    This function:
    1. Creates a pipe using os.pipe()
    2. Forks first child for left command
    3. Forks second child for right command
    4. Parent waits for both children
    5. Ensures commands run concurrently
    """
    # Step 1: Create a pipe
    # os.pipe() returns (read_fd, write_fd)
    read_fd, write_fd = os.pipe()
    
    # Step 2: Fork the first child (left command)
    pid1 = os.fork()
    if pid1 == 0:  # Child 1 process
        # Redirect stdout (fd 1) to pipe write end
        os.dup2(write_fd, 1)
        # Close unused file descriptors
        # (dup2 duplicates the fd, so we close the originals)
        os.close(read_fd)
        os.close(write_fd)
        # Execute left command
        try:
            os.execvp(left_cmd[0], left_cmd)
        except OSError:
            print(f"{left_cmd[0]}: command not found", file=sys.stderr)
            os._exit(127)
    
    # Step 3: Fork the second child (right command)
    pid2 = os.fork()
    if pid2 == 0:  # Child 2 process
        # Redirect stdin (fd 0) to pipe read end
        os.dup2(read_fd, 0)
        # Close unused file descriptors
        os.close(read_fd)
        os.close(write_fd)
        # Execute right command
        try:
            os.execvp(right_cmd[0], right_cmd)
        except OSError:
            print(f"{right_cmd[0]}: command not found", file=sys.stderr)
            os._exit(127)
    
    # Step 4: Parent cleanup and wait
    # Parent must close both pipe fds (not used in parent)
    # If parent keeps them open, children won't get EOF when reading
    os.close(read_fd)
    os.close(write_fd)
    
    # Wait for both children to finish
    # This blocks until both processes exit
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)
