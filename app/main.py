import sys


def main():

    buildin_commands = ["echo" , "exit" , "type"]
    
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        user_command = sys.stdin.readline().rstrip()

        if user_command =="exit":
            break


        user_instruction = user_command.split()

        command  = user_instruction[0]

        if command == "echo":
            sys.stdout.write(f"{' '.join(user_instruction[1:])}\n")
        
        elif command == "type":
            if len(user_instruction) < 2:
                sys.stdout.write(f"{user_command}: command not found\n")
            elif user_instruction[1] in buildin_commands:
                sys.stdout.write(f"{user_instruction[1]} is a shell builtin\n")
            else:
                sys.stdout.write(f"{user_command}: command not found\n")
        else:
            sys.stdout.write(f"{user_command}: command not found\n")



if __name__ == "__main__":
    main()
