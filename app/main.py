import sys
import os

path = os.environ["PATH"].split(":")

def handle_exit(args):
    sys.exit(0)


def handle_echo(args):
    print(" ".join(args))


import os


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

commands = {
    "exit": handle_exit,
    "echo": handle_echo,
    "type": handle_type,
}


def main():

    while True:

        sys.stdout.write("$ ")
        sys.stdout.flush()

        user_command = sys.stdin.readline().rstrip()

        if not user_command:
            continue

        parts = user_command.split()

        command = parts[0]
        args = parts[1:]

        if command in commands:
            commands[command](args)
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()