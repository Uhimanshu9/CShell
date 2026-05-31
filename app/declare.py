import os

SHELL_VARIABLES: dict[str, str] = {}  # Variables declared in the shell


def is_valid_identifier(name: str) -> bool:
    """Check if a name is a valid shell variable identifier.
    
    Rules:
    - Must start with a letter or underscore
    - Can contain letters, digits, and underscores
    - Cannot be empty
    """
    if not name:
        return False
    
    # First character must be letter or underscore
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    
    # Rest can be letters, digits, or underscores
    for char in name[1:]:
        if not (char.isalnum() or char == "_"):
            return False
    
    return True


def handle_declare(args):
    """Handle the declare builtin command.
    
    Supports:
    - declare NAME=VALUE: Store a shell variable
    - declare -p NAME: Print a description of the variable NAME
    """
    if not args:
        return
    
    # Check for -p flag
    if args[0] == "-p":
        if len(args) < 2:
            print("declare: -p: argument required")
            return
        
        var_name = args[1]
        
        # Check if variable exists
        if var_name in SHELL_VARIABLES:
            value = SHELL_VARIABLES[var_name]
            print(f'declare -- {var_name}="{value}"')
        else:
            print(f"declare: {var_name}: not found")
            return
    else:
        # Handle declare NAME=VALUE
        assignment = args[0]
        
        # Check if it contains an equals sign
        if "=" in assignment:
            var_name, var_value = assignment.split("=", 1)
            
            # Validate variable name
            if not is_valid_identifier(var_name):
                print(f"declare: `{assignment}': not a valid identifier")
                return
            
            SHELL_VARIABLES[var_name] = var_value
        else:
            # If no equals sign, treat as a flag or error
            print(f"declare: {assignment}: invalid option")
            return
