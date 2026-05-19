import sys
import os
import shlex
import readline
import subprocess

path = os.environ["PATH"].split(":")
COMPLETION_SCRIPT_REGISTRY: dict[str, str] = {}



def get_path_executables() -> set[str]:
    executables: set[str] = set()
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        try:
            for name in os.listdir(directory):
                full_path = os.path.join(directory, name)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    executables.add(name)
        except (FileNotFoundError, PermissionError):
            continue
    return executables

PATH_EXECUTABLES = get_path_executables()



def get_filename_completions(text: str) -> list[str]:
    # Expand ~ for matching, but keep returned paths in expanded form too.
    expanded = os.path.expanduser(text)
    directory, prefix = os.path.split(expanded)
    search_dir = directory if directory else "."

    try:
        entries = os.listdir(search_dir)
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return []

    completions: list[str] = []
    for entry in entries:
        if not entry.startswith(prefix):
            continue

        candidate = os.path.join(directory, entry) if directory else entry
        full_candidate = os.path.join(search_dir, entry)

        # Directories usually continue with '/', files usually continue with a space.
        if os.path.isdir(full_candidate):
            completions.append(candidate + "/")
        else:
            completions.append(candidate + " ")

    return sorted(completions)

def handle_exit(args):
    sys.exit(0)

def handle_echo(args):
    print(" ".join(args))

def handle_type(args):

    # No command provided
    if not args:
        print("type: missing argument")
        return

    command_name = args[0]

    # Step 1: Check builtin commands
    if command_name in commands:
        print(f"{command_name} is a shell builtin")
        return

    # Step 2: Search PATH directories
    paths = os.environ["PATH"].split(":")

    for path in paths:

        # Create full path like:
        # /usr/bin/ls
        full_path = os.path.join(path, command_name)

        # Step 3:
        # Check:
        # 1. file exists
        # 2. file is executable
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):

            print(f"{command_name} is {full_path}")
            return

    # Step 4: Not found anywhere
    print(f"{command_name}: not found")

def execute_external(command_name, command_args):

    paths = os.environ["PATH"].split(":")

    for path in paths:

        full_path = os.path.join(path, command_name)

        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):

            pid = os.fork()

            # Child
            if pid == 0:

                os.execv(full_path, [command_name] + command_args)

            # Parent
            else:

                os.wait()

            return

    print(f"{command_name}: command not found")

def handle_present_dir(args):
    print(os.getcwd())

def handle_cd(args):
    if not args:
        print("cd: missing argument")
        return
    
    path = args[0]

    if path == '~':
        path = os.path.expanduser("~")

    # check if the directory exists
    if os.path.isdir(path):
        os.chdir(path)
    else:
        print(f"cd: {path}: No such file or directory")

def handle_completer(args):
    if "-p" in args or "--path" in args:
        if len(args) == 2:
            target = args[1]
            if target in COMPLETION_SCRIPT_REGISTRY:
                print(f"complete -C '{COMPLETION_SCRIPT_REGISTRY[args[1]]}' {args[1]}")
            else:
                print(f"complete: {target}: no completion specification") 
        else:
                raise ValueError("Invalid complete option")
    elif "-C" in args:
        if len(args) == 3:
            target = args[2]
            script = args[1]
            COMPLETION_SCRIPT_REGISTRY[target] = script
            # print(f"Registered completion script for {target}")
        else:
                raise ValueError("Invalid complete option")
    else:
        raise ValueError("Invalid complete option")


def get_completer_script_for_command(command: str) -> str | None:
    return COMPLETION_SCRIPT_REGISTRY.get(command) 


commands = {
    "exit": handle_exit,
    "echo": handle_echo,
    "type": handle_type,
    "pwd": handle_present_dir,
    "cd": handle_cd,
    "complete": handle_completer
}

REDIRECT_MAP = {
    "1>": 1, # stdout
    ">": 1,  # stdout
    "2>": 2,  # stderr
    ">>": 1,  # stdout append
    "2>>": 2,   # stderr append
    "1>>": 1   # stdout append
}


def completer(text, state):
    try:
        begidx = readline.get_begidx()
    except Exception:
        begidx = 0

    # Programmable completion: if the command has a registered script via
    # `complete -C <script_path> <command>`, run it and use its stdout.
    line_buffer = readline.get_line_buffer()
    stripped = line_buffer.lstrip()
    command_name = stripped.split(maxsplit=1)[0] if stripped else ""
    script_path = get_completer_script_for_command(command_name) if command_name else None

    if script_path and command_name:
        # Passing arguments to the completer script:
        # argv[1] = command name
        # argv[2] = word being completed (readline passes this as `text`)
        # argv[3] = previous word (or empty string)
        before_current = line_buffer[:begidx].rstrip()
        previous_word = before_current.split()[-1] if before_current.split() else ""

        # Environment variables required by programmable completion.
        # COMP_LINE: full command line (no trailing newline)
        # COMP_POINT: zero-based byte index of cursor position in COMP_LINE
        try:
            cursor_char_index = readline.get_endidx()
        except Exception:
            cursor_char_index = len(line_buffer)

        comp_line = line_buffer
        comp_point = len(comp_line[:cursor_char_index].encode("utf-8"))

        env = os.environ.copy()
        env["COMP_LINE"] = comp_line
        env["COMP_POINT"] = str(comp_point)

        try:
            result = subprocess.run(
                [script_path, command_name, text, previous_word],
                capture_output=True,
                text=True,
                env=env,
            )
            candidates = [ln for ln in result.stdout.splitlines() if ln]
        except OSError:
            candidates = []

        # For this stage we assume exactly one line is returned.
        if candidates:
            candidate = candidates[0]
            if not candidate.endswith(" "):
                candidate += " "
            matches = [candidate]
        else:
            matches = []
    else:
        matches = []

    # Fallback completion (when no programmable completer exists):
    # - first token: builtins + PATH executables
    # - other tokens: filenames
    if not matches:
        if begidx == 0:
            fallback_candidates = set(commands.keys()) | PATH_EXECUTABLES
            matches = [cmd for cmd in sorted(fallback_candidates) if cmd.startswith(text)]
        else:
            matches = get_filename_completions(text)

    # If there are no valid completions, keep input unchanged and ring the bell.
    # Readline calls completer(text, state) with state=0,1,2,... for a single completion attempt.
    # Ring only on the first call (state==0).
    # No completions: keep input unchanged, ring bell once.
    if not matches and state == 0:
        sys.stdout.write("\x07")
        sys.stdout.flush()
        return None

    # Codecrafters expects a trailing space after completing the command name.
    # Only add it when completing the first token.
    if begidx == 0:
        matches = [m + " " for m in matches]

    if state < len(matches):
        return matches[state]
    return None


def main():
    # macOS often uses libedit, Codecrafters runner typically uses GNU readline.
    if readline.__doc__ and "libedit" in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    readline.set_completer(completer)
    # Treat only whitespace as a delimiter so path completion like ./src works.
    readline.set_completer_delims(" \t\n")

    while True:

        # sys.stdout.write("$ ")
        # sys.stdout.flush()

        # user_command = sys.stdin.readline().rstrip()
        user_command = input("$ ")

        while True:

            try:

                parts = shlex.split(user_command)
                break

            except ValueError:

                sys.stdout.write("> ")
                sys.stdout.flush()

                continuation = sys.stdin.readline().rstrip()

                user_command += "\n" + continuation

        if not parts:
            continue

        # index of output redirection operator (1>, >, 2>)
# --------------------------------------------------------------------------------------#
        output_redirection_index = None  
        original_redirect_fd = None
        original_redirect = None
        operation = "w"  # default to write mode
        fd = None

        # if "1>" in parts:
        #     output_redirection_index = parts.index("1>")
        # elif ">" in parts:
        #     output_redirection_index = parts.index(">")
        # elif "2>" in parts:
        #     output_redirection_index = parts.index("2>")

        for i , part in enumerate(parts):
            if part in REDIRECT_MAP:
                output_redirection_index = i
                original_redirect = REDIRECT_MAP[part]
                operation = "a" if part == ">>" or part == "2>>" or part == "1>>" else "w"
                break
            # i -> index
            # part -> value at that index (eg 1>, >, 2>)



        # seprate command and args
# --------------------------------------------------------------------------------------#

        command = parts[0]
        args = parts[1:] # this is a list


        # handle output redirection if present
# --------------------------------------------------------------------------------------#

        if output_redirection_index is not None:
            args = parts[1:output_redirection_index]
            output_file = parts[output_redirection_index + 1] if output_redirection_index + 1 < len(parts) else None
            fd = open(f'{output_file}', operation)
            original_redirect_fd = os.dup(original_redirect)  # Save original stdout # type: ignore
            os.dup2(fd.fileno(), original_redirect)  # Redirect stdout to the file # type: ignore

        

        # print(args)

        if command in commands:

            commands[command](args)

        else:
            
            execute_external(command, args)

        if output_redirection_index is not None:
     

            os.dup2(original_redirect_fd, original_redirect)  # type: ignore
            os.close(original_redirect_fd)  # type: ignore
            fd.close()  # type: ignore
            

if __name__ == "__main__":
    main()