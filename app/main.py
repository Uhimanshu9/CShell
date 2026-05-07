import sys


def main():
    sys.stdout.write("$ ")
    # print("$ ", end="")
    user_command = input()
    print(f"{user_command}: command not found")
    #sys.stdin.readline().rstrip()



if __name__ == "__main__":
    main()
