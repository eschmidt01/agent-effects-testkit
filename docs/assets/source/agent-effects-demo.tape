# Reproducible terminal recording for docs/assets/agent-effects-demo.gif.
# Requires VHS: https://github.com/charmbracelet/vhs
Output docs/assets/agent-effects-demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 24
Set TypingSpeed 30ms
Set Framerate 12
Set Theme { "background": "#0d1117", "foreground": "#e6edf3", "black": "#0d1117", "brightBlack": "#8b949e", "red": "#ff7b72", "brightRed": "#ffa198", "green": "#3fb950", "brightGreen": "#56d364", "yellow": "#d29922", "brightYellow": "#e3b341", "blue": "#58a6ff", "brightBlue": "#79c0ff", "magenta": "#bc8cff", "brightMagenta": "#d2a8ff", "cyan": "#39c5cf", "brightCyan": "#56d4dd", "white": "#b1bac4", "brightWhite": "#f0f6fc" }

Type "agent-effects demo --agent naive --report"
Sleep 350ms
Enter
Sleep 7s
Type "agent-effects bundle verify .agent-effects/failures/refund-lost-ack-*/"
Sleep 350ms
Enter
Sleep 2s
Type "ls .agent-effects/failures/*-report.html"
Sleep 350ms
Enter
Sleep 6s
