#!/usr/bin/env bash
# ============================================================
# XII OS — Window Snap Helper
# desktop/window-manager/xii-snap.sh
#
# Provides snap zones for windows via hyprctl:
#   left-half  / right-half  (50/50 split)
#   top-half   / bottom-half
#   top-left   / top-right   / bottom-left / bottom-right (quarters)
#   maximize   / restore
#
# Designed to be bound in hyprland.conf:
#   bind = SUPER, left,  exec, xii-snap.sh left-half
#   bind = SUPER, right, exec, xii-snap.sh right-half
#   bind = SUPER, up,    exec, xii-snap.sh maximize
#   bind = SUPER, down,  exec, xii-snap.sh restore
#
# Usage:
#   xii-snap.sh <zone>
# ============================================================

set -euo pipefail

ZONE="${1:-}"
GAPS_OUT=10  # Must match hyprland.conf gaps_out

if [[ -z "$ZONE" ]]; then
    echo "Usage: $0 <zone>"
    echo "Zones: left-half right-half top-half bottom-half"
    echo "       top-left top-right bottom-left bottom-right"
    echo "       maximize restore center"
    exit 1
fi

# ────────────────────────────────────────────────────────────
# Get monitor geometry
# ────────────────────────────────────────────────────────────
get_monitor_info() {
    hyprctl monitors -j 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
focused = next((m for m in data if m.get('focused')), data[0] if data else None)
if focused:
    print(f\"{focused['width']} {focused['height']} {focused['x']} {focused['y']}\")
else:
    print('1920 1080 0 0')
"
}

read -r MON_W MON_H MON_X MON_Y <<< "$(get_monitor_info)"

# Usable area (subtract gaps)
USABLE_W=$((MON_W - GAPS_OUT * 2))
USABLE_H=$((MON_H - GAPS_OUT * 2 - 34))  # 34 = statusbar height
HALF_W=$(( USABLE_W / 2 ))
HALF_H=$(( USABLE_H / 2 ))

POS_X=$((MON_X + GAPS_OUT))
POS_Y=$((MON_Y + GAPS_OUT + 34))
MID_X=$((POS_X + HALF_W + GAPS_OUT))
MID_Y=$((POS_Y + HALF_H + GAPS_OUT))

# ────────────────────────────────────────────────────────────
# Apply snap
# ────────────────────────────────────────────────────────────
snap() {
    local x=$1 y=$2 w=$3 h=$4
    hyprctl dispatch togglefloating active 2>/dev/null || true
    hyprctl dispatch moveactive exact "$x" "$y"
    hyprctl dispatch resizeactive exact "$w" "$h"
}

case "$ZONE" in
    left-half)
        snap "$POS_X" "$POS_Y" "$HALF_W" "$USABLE_H" ;;

    right-half)
        snap "$MID_X" "$POS_Y" "$HALF_W" "$USABLE_H" ;;

    top-half)
        snap "$POS_X" "$POS_Y" "$USABLE_W" "$HALF_H" ;;

    bottom-half)
        snap "$POS_X" "$MID_Y" "$USABLE_W" "$HALF_H" ;;

    top-left)
        snap "$POS_X" "$POS_Y" "$HALF_W" "$HALF_H" ;;

    top-right)
        snap "$MID_X" "$POS_Y" "$HALF_W" "$HALF_H" ;;

    bottom-left)
        snap "$POS_X" "$MID_Y" "$HALF_W" "$HALF_H" ;;

    bottom-right)
        snap "$MID_X" "$MID_Y" "$HALF_W" "$HALF_H" ;;

    maximize)
        hyprctl dispatch fullscreen 1 ;;  # Fake fullscreen (keeps status bar)

    center)
        CEN_W=$(( USABLE_W * 2 / 3 ))
        CEN_H=$(( USABLE_H * 3 / 4 ))
        CEN_X=$(( POS_X + (USABLE_W - CEN_W) / 2 ))
        CEN_Y=$(( POS_Y + (USABLE_H - CEN_H) / 2 ))
        snap "$CEN_X" "$CEN_Y" "$CEN_W" "$CEN_H" ;;

    restore)
        hyprctl dispatch togglefloating active ;;

    *)
        echo "Unknown zone: $ZONE" >&2
        exit 1 ;;
esac
