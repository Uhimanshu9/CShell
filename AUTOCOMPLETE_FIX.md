# Autocomplete (Tab) test failure + fix

## Problem
Codecrafters runs the shell on Linux (usually **GNU readline**). My local macOS Python often uses **libedit**.

If we bind Tab using the *wrong* syntax for the active readline implementation, Tab is treated like a literal `\t` character.
That shows up as extra spaces (e.g. `$ ech   `) instead of autocompleting to `$ echo `.

## Fix
In `app/main.py` we:

1) Detect which implementation is active:
- If `"libedit"` is present in `readline.__doc__`, use:
  - `readline.parse_and_bind("bind ^I rl_complete")`
- Otherwise (GNU readline), use:
  - `readline.parse_and_bind("tab: complete")`

2) Return a trailing space from the completer **only when completing the first token**.
This matches Codecrafters’ expected prompt line (e.g. `$ echo `).
