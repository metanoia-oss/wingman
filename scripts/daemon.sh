#!/bin/bash
# Wingman Daemon Management Script
# Usage: ./daemon.sh [start|stop|restart|status|logs|logs-err|install|uninstall]

# Get the project directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PLIST_NAME="com.wingman.agent"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
LOG_OUT="$PROJECT_DIR/logs/launchd.out"
LOG_ERR="$PROJECT_DIR/logs/launchd.err"

# Ensure logs directory exists
mkdir -p "$PROJECT_DIR/logs"

create_plist() {
    cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/.venv/bin/python</string>
        <string>$PROJECT_DIR/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$LOG_OUT</string>
    <key>StandardErrorPath</key>
    <string>$LOG_ERR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF
    echo "Created plist at $PLIST_PATH"
}

case "$1" in
    start|load)
        echo "Starting Wingman daemon..."
        if [ ! -f "$PLIST_PATH" ]; then
            echo "Creating launch agent plist..."
            create_plist
        fi
        launchctl load "$PLIST_PATH" 2>/dev/null
        sleep 1
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo "Daemon started successfully"
            launchctl list | grep "$PLIST_NAME"
        else
            echo "Failed to start daemon"
            exit 1
        fi
        ;;

    stop|unload)
        echo "Stopping Wingman daemon..."
        launchctl unload "$PLIST_PATH" 2>/dev/null
        echo "Daemon stopped"
        ;;

    restart)
        echo "Restarting Wingman daemon..."
        launchctl unload "$PLIST_PATH" 2>/dev/null
        sleep 1
        if [ ! -f "$PLIST_PATH" ]; then
            create_plist
        fi
        launchctl load "$PLIST_PATH"
        sleep 1
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo "Daemon restarted successfully"
        else
            echo "Failed to restart daemon"
            exit 1
        fi
        ;;

    status)
        echo "Checking daemon status..."
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo "Daemon is running:"
            launchctl list | grep "$PLIST_NAME"
        else
            echo "Daemon is not running"
        fi
        ;;

    logs|log)
        echo "Tailing stdout log (Ctrl+C to exit)..."
        tail -f "$LOG_OUT"
        ;;

    logs-err|err)
        echo "Tailing stderr log (Ctrl+C to exit)..."
        tail -f "$LOG_ERR"
        ;;

    install)
        echo "Installing launch agent..."
        create_plist
        echo "Launch agent installed at $PLIST_PATH"
        echo "Run './daemon.sh start' to start the daemon"
        ;;

    uninstall)
        echo "Uninstalling launch agent..."
        launchctl unload "$PLIST_PATH" 2>/dev/null
        if [ -f "$PLIST_PATH" ]; then
            rm "$PLIST_PATH"
            echo "Launch agent uninstalled"
        else
            echo "Launch agent plist not found"
        fi
        ;;

    interactive)
        echo "Running bot interactively (for QR code scanning)..."
        echo "Press Ctrl+C to stop after authentication is complete"
        cd "$PROJECT_DIR"
        source "$PROJECT_DIR/.venv/bin/activate"
        python run.py
        ;;

    *)
        echo "Wingman Daemon Manager"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  start       - Start the daemon (load launch agent)"
        echo "  stop        - Stop the daemon (unload launch agent)"
        echo "  restart     - Restart the daemon"
        echo "  status      - Check if daemon is running"
        echo "  logs        - Tail stdout log"
        echo "  logs-err    - Tail stderr log"
        echo "  install     - Create/update launch agent plist"
        echo "  uninstall   - Remove launch agent completely"
        echo "  interactive - Run bot interactively (for QR scanning)"
        echo ""
        echo "Project directory: $PROJECT_DIR"
        exit 1
        ;;
esac
