# Pipeline Support for Built-in Commands

## Overview

This document describes how to extend the shell to support built-in commands (like `echo`, `type`, `pwd`) within pipelines.

**Examples that should work:**
```bash
$ echo hello | wc -c
       6
$ echo apple | type
# or
$ type echo | wc
```

## Key Challenges

### 1. Built-ins Print Directly to stdout

**Problem:** Built-in commands use `print()` which writes to Python's stdout (fd 1 in the shell).

```python
def handle_echo(args):
    print(" ".join(args))  # This goes to terminal, not the pipe!
```

**Solution:** Before calling a built-in in a pipeline, redirect fd 1 to the pipe's write end using `os.dup2()`.

### 2. Built-ins Can't Use `execvp()`

**Problem:** `os.execvp()` replaces the entire process, so built-in functions can't be called.

**Solution:** Run built-ins in a forked child process, then call the function directly (no exec needed).

### 3. Partial Pipelines (Mixed Built-in & External)

**Problem:** Some pipelines have a built-in on one side and external on the other (or both).

**Solution:** Use a unified `execute_command()` function that detects the type and handles it appropriately.

---

## Architecture Overview

```
Pipeline Parsing
    │
    ├─ Detect "|" in parts
    ├─ Split into: left_cmd, right_cmd
    └─ Call execute_pipeline_with_builtins(left_cmd, right_cmd)

execute_pipeline_with_builtins()
    │
    ├─ Create pipe: read_fd, write_fd = os.pipe()
    │
    ├─ Fork Child 1
    │   ├─ os.dup2(write_fd, 1)  # stdout → pipe
    │   ├─ detect_and_execute(left_cmd)
    │   │   ├─ if builtin: call_builtin_function(args)
    │   │   └─ else: os.execvp(cmd, args)
    │   └─ os._exit()
    │
    ├─ Fork Child 2
    │   ├─ os.dup2(read_fd, 0)   # stdin ← pipe
    │   ├─ detect_and_execute(right_cmd)
    │   └─ os._exit()
    │
    ├─ Parent cleanup
    │   ├─ os.close(read_fd)
    │   ├─ os.close(write_fd)
    │   ├─ os.waitpid(pid1, 0)
    │   └─ os.waitpid(pid2, 0)
```

---

## File Descriptor Management

### Before Pipeline
```
Process stdin (fd 0)  ← Terminal keyboard
Process stdout (fd 1) ← Terminal display
Process stderr (fd 2) ← Terminal display
```

### After Creating Pipe
```
read_fd = 3
write_fd = 4
```

### Child 1 (Left Command)
```
stdin (fd 0)   → Terminal keyboard (unchanged)
stdout (fd 1)  → Pipe write end (fd 4) via dup2()
write_fd (4)   → Closed (not needed)
read_fd (3)    → Closed (not needed)
```

### Child 2 (Right Command)
```
stdin (fd 0)   → Pipe read end (fd 3) via dup2()
stdout (fd 1)  → Terminal display (unchanged)
read_fd (3)    → Closed (not needed)
write_fd (4)   → Closed (not needed)
```

### Parent After Fork
```
read_fd (3)    → Closed
write_fd (4)   → Closed
```

---

## Implementation Strategy

### Step 1: Create a Command Detector

Determine if a command is built-in or external:

```python
def is_builtin(command_name):
    """Check if command_name is a built-in shell command."""
    return command_name in commands  # where commands = {"echo": ..., "type": ..., etc}
```

### Step 2: Create a Unified Executor

For use **inside child processes**:

```python
def execute_command_in_child(cmd_list):
    """
    Execute a command in a child process.
    If built-in: call the function.
    If external: use os.execvp().
    
    NOTE: This function should NOT return (exits child process).
    """
    command_name = cmd_list[0]
    args = cmd_list[1:]
    
    if is_builtin(command_name):
        # Built-in: call the function
        try:
            commands[command_name](args)
            # Built-in finished successfully
            os._exit(0)
        except SystemExit:
            # handle_exit() calls sys.exit()
            os._exit(0)
        except Exception as e:
            print(f"Error in {command_name}: {e}", file=sys.stderr)
            os._exit(1)
    else:
        # External: use execvp
        try:
            os.execvp(command_name, cmd_list)
        except OSError:
            print(f"{command_name}: command not found", file=sys.stderr)
            os._exit(127)
```

### Step 3: Modify `execute_pipeline()`

Update the pipeline function to support both types:

```python
def execute_pipeline_with_builtins(left_cmd, right_cmd):
    """
    Execute: left_cmd | right_cmd
    Both sides can be built-in or external.
    """
    # Step 1: Create pipe
    read_fd, write_fd = os.pipe()
    
    # Step 2: Fork Child 1
    pid1 = os.fork()
    if pid1 == 0:  # Child 1
        # Redirect stdout to pipe
        os.dup2(write_fd, 1)
        # Close unused fds
        os.close(read_fd)
        os.close(write_fd)
        # Execute (don't return)
        execute_command_in_child(left_cmd)
    
    # Step 3: Fork Child 2
    pid2 = os.fork()
    if pid2 == 0:  # Child 2
        # Redirect stdin from pipe
        os.dup2(read_fd, 0)
        # Close unused fds
        os.close(read_fd)
        os.close(write_fd)
        # Execute (don't return)
        execute_command_in_child(right_cmd)
    
    # Step 4: Parent cleanup
    os.close(read_fd)
    os.close(write_fd)
    os.waitpid(pid1, 0)
    os.waitpid(pid2, 0)
```

### Step 4: Handle Output Redirection in Pipelines

If a pipeline also has output redirection (e.g., `echo hello | wc > out.txt`):

```python
# Parse and detect BOTH pipe AND redirection
if "|" in parts:
    # Find pipe and split
    pipe_index = parts.index("|")
    pipeline_parts = parts[:pipe_index]
    rest = parts[pipe_index + 1:]
    
    # Check if rest has redirection
    output_redirection_index = None
    for i, part in enumerate(rest):
        if part in REDIRECT_MAP:
            output_redirection_index = i
            break
    
    if output_redirection_index is not None:
        # Handle: cmd1 | cmd2 > file
        right_cmd = rest[:output_redirection_index]
        redirect_op = rest[output_redirection_index]
        redirect_file = rest[output_redirection_index + 1]
        
        # Execute pipeline, then apply redirection to Child 2
        # (This requires modifying execute_pipeline to accept redirect params)
    else:
        # Simple pipeline
        left_cmd = pipeline_parts
        right_cmd = rest
```

---

## Common Mistakes & How to Fix Them

### Mistake 1: Built-in Returns Instead of Exits

```python
# WRONG - Child process:
def handle_echo(args):
    print(" ".join(args))
    # Function returns - child continues running!

# Child 1 after execute_command_in_child():
execute_command_in_child(['echo', 'hello'])
# Returns here - but child should exit!
os._exit(0)  # Too late, child might fork again

# FIX:
def execute_command_in_child(cmd_list):
    if is_builtin(cmd_list[0]):
        commands[cmd_list[0]](cmd_list[1:])
        os._exit(0)  # ALWAYS exit child after builtin
```

### Mistake 2: Not Capturing Exceptions in Built-ins

```python
# WRONG:
handle_exit([])  # Calls sys.exit(), kills parent shell!

# FIX: In child process, catch and convert to os._exit()
try:
    commands[command_name](args)
    os._exit(0)
except SystemExit as e:
    os._exit(e.code if hasattr(e, 'code') else 0)
```

### Mistake 3: Print to Terminal Instead of Pipe

```python
# WRONG - Built-in still prints to terminal:
def handle_type(args):
    # Before dup2, but forget to redirect stdout
    command_name = args[0]
    if command_name in commands:
        print(f"{command_name} is a shell builtin")  # Goes to terminal!

# FIX: In child process, call dup2 BEFORE executing built-in
os.dup2(write_fd, 1)  # Redirect stdout
os.close(write_fd)    # Close duplicate
# Now print() writes to pipe
handle_type(['echo'])  # Output goes to pipe
```

### Mistake 4: Not Closing Duplicate FDs After dup2

```python
# WRONG:
os.dup2(write_fd, 1)
# write_fd (4) still open; parent's copy is also open

# Child finishes, but write_fd in parent keeps pipe open
# Other child reading from pipe never gets EOF
# HANG!

# FIX:
os.dup2(write_fd, 1)  # Copy write_fd to fd 1
os.close(write_fd)    # Close the original
os.close(read_fd)     # Close unused read
```

### Mistake 5: Not Handling Built-in stderr

```python
# WRONG:
# Built-in prints error to stderr (fd 2), bypasses pipe
def handle_type(args):
    if not args:
        print("type: missing argument")  # Goes to terminal, not pipe!

# Note: This is technically correct - errors go to stderr, not pipe
# But be aware that error output won't flow through the pipeline
```

---

## Testing Strategy

### Test 1: Simple External Pipeline
```bash
$ echo hello | wc -c
```
**Expected:** 6 (works with current code)

### Test 2: Built-in as Left Command
```bash
$ echo hello | cat
```
**Expected:** `hello` printed (built-in writes to pipe, external reads)

### Test 3: Built-in as Right Command
```bash
$ cat < test_file | wc
```
**Expected:** Line/word/char count (external writes to pipe, built-in reads)

### Test 4: Both Built-ins
```bash
$ echo hello | type echo
```
**Expected:** Should show info about the echo command

### Test 5: With Redirection
```bash
$ echo hello | wc > output.txt
```
**Expected:** output.txt contains word count

---

## Integration Checklist

- [ ] Create `execute_command_in_child()` function
- [ ] Create `execute_pipeline_with_builtins()` function
- [ ] Update main loop to detect and handle pipelines
- [ ] Handle built-ins that call `sys.exit()` in child processes
- [ ] Test built-in on left side of pipe
- [ ] Test built-in on right side of pipe
- [ ] Test both sides as built-ins
- [ ] Test with output redirection
- [ ] Verify no hanging/deadlocks
- [ ] Ensure parent shell stdin/stdout restored after pipeline

---

## Edge Cases to Consider

1. **Broken Pipes:** If right command exits early, left command gets SIGPIPE
2. **Built-in Output Buffering:** `print()` may buffer; might need `sys.stdout.flush()`
3. **Exit Codes:** Pipeline should report right command's exit code
4. **Background Pipelines:** `echo hello | cat &` should work
5. **Multiple Pipes:** `cmd1 | cmd2 | cmd3` (future: requires loop)

