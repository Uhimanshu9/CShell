# Multi-Stage Pipeline Implementation

## Overview

Multi-stage pipelines connect three or more commands sequentially:

```bash
$ cmd1 | cmd2 | cmd3 | cmd4
```

This requires:
- **N commands** → **N-1 pipes**
- **N child processes** (one per command)
- Careful file descriptor management for each stage

## Architecture

### Pipeline Structure for `cmd1 | cmd2 | cmd3`

```
Pipes Created:
  pipe1: read_fd=3, write_fd=4
  pipe2: read_fd=5, write_fd=6

Child 1 (cmd1):
  stdin  → terminal
  stdout → write_fd=4 (pipe1 write)
  Close: read_fd=3, read_fd=5, write_fd=6

Child 2 (cmd2):
  stdin  ← read_fd=3 (pipe1 read)
  stdout → write_fd=6 (pipe2 write)
  Close: write_fd=4, read_fd=5

Child 3 (cmd3):
  stdin  ← read_fd=5 (pipe2 read)
  stdout → terminal
  Close: write_fd=4, write_fd=6, read_fd=3
```

**Key insight:** Each child must close ALL pipe file descriptors it doesn't use.

## Algorithm

### Step 1: Parse Multiple Pipes
```python
def parse_pipeline(parts: list[str]) -> list[list[str]] | None:
    """
    Split command into pipeline stages.
    
    Input:  ['cat', 'file', '|', 'head', '-n', '3', '|', 'wc']
    Output: [['cat', 'file'], ['head', '-n', '3'], ['wc']]
    """
    # TODO: Find all pipe indices and split
```

### Step 2: Create N-1 Pipes
```python
def create_pipes(num_pipes: int) -> list[tuple[int, int]]:
    """
    Create N pipes and return list of (read_fd, write_fd) tuples.
    
    For N commands, create N-1 pipes.
    Returns: [(read1, write1), (read2, write2), ...]
    """
    # TODO: Loop and create each pipe with os.pipe()
```

### Step 3: Fork N Children and Connect Them
```python
def execute_multi_stage_pipeline(stages: list[list[str]], commands_dict: dict):
    """
    Execute N commands in a pipeline.
    
    stages: [['cat', 'file'], ['head', '-n', '3'], ['wc']]
    """
    # TODO:
    # 1. Create N-1 pipes
    # 2. Fork N children
    # 3. For each child i:
    #    - If i > 0: redirect stdin from pipe[i-1].read
    #    - If i < N-1: redirect stdout to pipe[i].write
    #    - Close ALL unused pipe fds
    #    - Execute command
    # 4. Parent: close all pipe fds and waitpid() all children
```

## File Descriptor Management

For **N commands**, there are **N-1 pipes**, creating **2(N-1) file descriptors**.

**General rules:**
- **Child 0 (first):** Reads from terminal (fd 0), writes to pipe[0].write
- **Child i (middle):** Reads from pipe[i-1].read, writes to pipe[i].write
- **Child N-1 (last):** Reads from pipe[N-2].read, writes to terminal (fd 1)

**Every child must close:**
- write_fd of pipes where it reads
- read_fd of pipes where it writes
- ALL OTHER pipe file descriptors

### Example: 3 Commands (2 Pipes)

```
pipes = [(3, 4), (5, 6)]

Child 0:
  dup2(pipe[0].write=4, 1)  # stdout → pipe 0 write
  close(3, 4)               # Close pipe 0 (created copies)
  close(5, 6)               # Close pipe 1 (not used)
  execvp(cmd0)

Child 1:
  dup2(pipe[0].read=3, 0)   # stdin ← pipe 0 read
  dup2(pipe[1].write=6, 1)  # stdout → pipe 1 write
  close(3, 4)               # Close pipe 0
  close(5, 6)               # Close pipe 1 (created copies)
  execvp(cmd1)

Child 2:
  dup2(pipe[1].read=5, 0)   # stdin ← pipe 1 read
  close(3, 4)               # Close pipe 0 (not used)
  close(5, 6)               # Close pipe 1 (created copy)
  execvp(cmd2)

Parent:
  for each pipe: close(read), close(write)
  for each child: waitpid(pid)
```

## Implementation Details

### Pattern: Close All Unused FDs

```python
def close_all_pipes(pipes: list[tuple[int, int]]):
    """Close all pipe file descriptors."""
    for read_fd, write_fd in pipes:
        os.close(read_fd)
        os.close(write_fd)
```

### Pattern: Setup Stdin from Pipe

```python
def setup_stdin_from_pipe(pipe_read_fd: int):
    """Redirect stdin to read from a pipe."""
    os.dup2(pipe_read_fd, 0)  # Copy pipe read end to fd 0
    os.close(pipe_read_fd)    # Close the original
```

### Pattern: Setup Stdout to Pipe

```python
def setup_stdout_to_pipe(pipe_write_fd: int):
    """Redirect stdout to write to a pipe."""
    os.dup2(pipe_write_fd, 1)  # Copy pipe write end to fd 1
    os.close(pipe_write_fd)    # Close the original
```

## Common Mistakes

### Mistake 1: Not Closing All Unused Pipes in Each Child

```python
# WRONG:
for i, stage in enumerate(stages):
    pid = os.fork()
    if pid == 0:
        if i > 0:
            os.dup2(pipes[i-1][0], 0)
        if i < len(stages) - 1:
            os.dup2(pipes[i][1], 1)
        # Forgot to close pipes!
        execute_command_in_child(stage, commands_dict)

# CORRECT:
for i, stage in enumerate(stages):
    pid = os.fork()
    if pid == 0:
        if i > 0:
            os.dup2(pipes[i-1][0], 0)
        if i < len(stages) - 1:
            os.dup2(pipes[i][1], 1)
        # Close ALL pipes
        for read_fd, write_fd in pipes:
            os.close(read_fd)
            os.close(write_fd)
        execute_command_in_child(stage, commands_dict)
```

### Mistake 2: Parent Doesn't Close Pipes

```python
# WRONG:
for i, stage in enumerate(stages):
    pid = os.fork()
    # ... child setup ...
    
# Parent forgot to close!
for pid in pids:
    os.waitpid(pid, 0)

# CORRECT:
for i, stage in enumerate(stages):
    pid = os.fork()
    # ... child setup ...

# Parent MUST close all pipes
for read_fd, write_fd in pipes:
    os.close(read_fd)
    os.close(write_fd)

for pid in pids:
    os.waitpid(pid, 0)
```

### Mistake 3: Closing Pipe FDs Before dup2

```python
# WRONG:
if i > 0:
    os.close(pipes[i-1][0])  # Close before dup2!
    os.dup2(pipes[i-1][0], 0)  # This fails!

# CORRECT:
if i > 0:
    os.dup2(pipes[i-1][0], 0)  # dup2 first (creates copy to fd 0)
    os.close(pipes[i-1][0])  # Then close original
```

## Testing Strategy

```bash
# Test 1: 3-stage pipeline
$ cat file.txt | head -n 5 | wc -l
# Should output line count

# Test 2: 4-stage pipeline
$ ls -la | grep something | wc | tail -n 1
# Should output the last line of wc output

# Test 3: Built-in in pipeline
$ echo -e "a\nb\nc" | sort | wc -l
# Should output: 3

# Test 4: Built-in multiple stages
$ echo hello | cat | wc -c
# Should output: 6
```

## Implementation Checklist

- [ ] Create `parse_pipeline()` to split on all `|` characters
- [ ] Create `create_pipes()` to generate N-1 pipes
- [ ] Create `execute_multi_stage_pipeline()` main function
- [ ] For each child: setup stdin/stdout correctly based on stage index
- [ ] For each child: close all pipe file descriptors
- [ ] Parent: close all pipes before waitpid
- [ ] Test with 3+ stage pipelines
- [ ] Test with built-ins in multi-stage pipelines
- [ ] Verify no deadlocks or hanging processes

