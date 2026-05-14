import sys
import os
import shlex

path = os.environ["PATH"].split(":")

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

    




commands = {
    "exit": handle_exit,
    "echo": handle_echo,
    "type": handle_type,
    "pwd": handle_present_dir,
    "cd": handle_cd
}


def main():

    while True:

        sys.stdout.write("$ ")
        sys.stdout.flush()

        user_command = sys.stdin.readline().rstrip()

        if not user_command:
            continue

        
        try:
            parts = shlex.split(user_command)

        except ValueError as e:
            continuation = input("> ")
            user_command += "\n" + continuation
            parts = shlex.split(user_command)



        command = parts[0]
        args = parts[1:]

        if command in commands:
            commands[command](args)
        else:
            execute_external(command, args)
            # print(f"{command}: command not found")


if __name__ == "__main__":
    main()