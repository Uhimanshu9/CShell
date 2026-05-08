import sys


def handle_exit(args):
    sys.exit(0)


def handle_echo(args):
    print(" ".join(args))


def handle_type(args):

    if not args:
        print("type: missing argument")
        return

    command_name = args[0]

    if command_name in commands:
        print(f"{command_name} is a shell builtin")
    else:
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