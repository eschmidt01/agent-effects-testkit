# Reproducible terminal recording for docs/assets/agent-effects-demo.gif.
# Requires VHS: https://github.com/charmbracelet/vhs
Output docs/assets/agent-effects-demo.gif
Set Shell "bash"
Set FontSize 18
Set Width 1200
Set Height 720
Set Padding 24
Set TypingSpeed 35ms
Set Framerate 12
Set Theme { "background": "#101513", "foreground": "#edf4ef", "black": "#101513", "brightBlack": "#61706a", "red": "#ff8a80", "brightRed": "#ff8a80", "green": "#4bd1b3", "brightGreen": "#9be6d4", "yellow": "#f2c14e", "brightYellow": "#ffe299", "blue": "#75b8ff", "brightBlue": "#a9d3ff", "magenta": "#c7a8ff", "brightMagenta": "#dbc9ff", "cyan": "#4bd1b3", "brightCyan": "#9be6d4", "white": "#edf4ef", "brightWhite": "#ffffff" }

Type "agent-effects demo --agent naive --report"
Sleep 500ms
Enter
Sleep 11s
Type "agent-effects bundle report .agent-effects/failures/refund-lost-ack-*/ --output .agent-effects/failure-report.html"
Sleep 500ms
Enter
Sleep 3s
Type "# expected 1 refund · observed 2 refunds · open .agent-effects/failure-report.html"
Sleep 3s
