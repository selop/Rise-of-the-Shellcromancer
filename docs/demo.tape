# VHS play-test recording of the reworked Shellcromancer TUI.
# Render with:  vhs demo.tape   (run from the repo root)

Output docs/demo.gif
Output docs/demo.mp4

Set Shell zsh
Set FontSize 17
Set Width 1320
Set Height 820
Set Padding 12
Set Framerate 24
Set Theme "Catppuccin Mocha"

# --- launch a fresh game (typing hidden from the recording) ---
Hide
Type "cd /Users/selop/Git/Rise-of-the-Shellcromancer && rm -rf /tmp/sc-demo"
Enter
Type "XDG_DATA_HOME=/tmp/sc-demo uv run shellcromancer"
Enter
Sleep 5s
Show

# --- Scribe: themed panels, stores, units, buildings ---
Sleep 4s

# --- Reign: three interactive shop columns + selection sync ---
Type "r"
Sleep 2s
Down
Sleep 900ms
Down
Sleep 900ms
Right
Sleep 1.2s
Down
Sleep 900ms
Right
Sleep 1.2s
Down
Sleep 900ms
Enter
Sleep 2s
Down
Sleep 700ms
Enter
Sleep 2.5s

# --- Battle: next-threat bar + threat countdowns ---
Type "b"
Sleep 4s

# --- Logs ---
Type "l"
Sleep 3s

# --- Encyclopedia / Codex ---
Type "e"
Sleep 3.5s

# --- back to Scribe to show resources ticking up ---
Type "s"
Sleep 5s
