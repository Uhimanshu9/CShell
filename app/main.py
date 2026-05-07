import sys


def main():
    
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        user_command = sys.stdin.readline().rstrip()

        if user_command =="exit":
            break
        sys.stdout.write(f"{user_command}: command not found\n")



if __name__ == "__main__":
    main()
