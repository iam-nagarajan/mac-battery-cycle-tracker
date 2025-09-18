#!/usr/bin/env zsh
#
# Battery Cycle Cron Script
#
# This script can be used with cron to automatically record battery cycles.
# Add this to your crontab to run every hour:
#
# Record battery cycle every hour
# 0 * * * * /path-to/folder/mac-battery-cycle/cron_battery_check.sh
#
# Or to run multiple times per day:
# Record battery cycle every 6 hours
# 0 */6 * * * /path-to/folder/mac-battery-cycle/cron_battery_check.sh
#

# Get the directory where this script is located (zsh compatible)
if [[ -n "${ZSH_VERSION}" ]]; then
    # Running in zsh
    SCRIPT_DIR="${0:A:h}"
else
    # Running in bash or other shell
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
fi

# Change to the project directory
cd "$SCRIPT_DIR" || exit 1

# Set up PATH to ensure we can find python3
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:$PATH"

# Find python3 executable
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "$(date): ERROR - Python not found in PATH" >> battery_tracker.log
    exit 1
fi

# Run the battery tracker to record current cycle count
"$PYTHON_CMD" battery_tracker.py --record >> battery_tracker.log 2>&1

# Log the execution with exit status
if [[ $? -eq 0 ]]; then
    echo "$(date): Battery check completed successfully" >> battery_tracker.log
else
    echo "$(date): Battery check failed with exit code $?" >> battery_tracker.log
fi