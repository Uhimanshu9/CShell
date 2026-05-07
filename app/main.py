import sys


def main():
    
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
        
        else:
            sys.stdout.write(f"{user_command}: command not found\n")



if __name__ == "__main__":
    main()
