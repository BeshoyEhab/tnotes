"""Gruvbox-bright palette shared by the CLI renderer and the Textual TUI.

The colors come from the starship `gruvbox_bright` palette already used by
the user's prompt, so `tn` blends into the shell instead of inventing a look.
"""

BG = "#282828"
SURFACE = "#3c3836"
PANEL = "#504945"
FG = "#fbf1c7"
MUTED = "#928374"
FAINT = "#665c54"
ORANGE = "#fe8019"
YELLOW = "#fabd2f"
GREEN = "#b8bb26"
AQUA = "#8ec07c"
BLUE = "#83a598"
PURPLE = "#d3869b"
RED = "#fb4934"

TYPE_COLORS = {"note": GREEN, "url": BLUE, "cmd": YELLOW}
ICONS = {"note": "✎", "url": "↗", "cmd": "❯"}
