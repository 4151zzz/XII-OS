#!/usr/bin/env bash
# =============================================================
# XII OS — Hardware Hotplug Handler
# system/hardware/xii-hotplug.sh
#
# Called by udev rules and systemd on hardware events.
# Handles: USB storage, display connection, Bluetooth audio.
#
# Usage (via udev RUN+= or xii-hotplug.service):
#   xii-hotplug.sh <event> <device>
#
# Events:
#   usb-added     <device>    USB storage plugged in
#   removed       <device>    USB device removed
#   display-added <device>    External display connected
#   display-removed <device>  External display disconnected
# =============================================================

set -euo pipefail

EVENT="${1:-}"
DEVICE="${2:-}"

# ────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────
LOG_FILE="/var/log/xii-os/hotplug.log"
_log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$EVENT] $DEVICE: $*" >> "$LOG_FILE" 2>/dev/null || true
}

# ────────────────────────────────────────────────────────────
# Desktop notification (as logged-in user)
# ────────────────────────────────────────────────────────────
_notify_user() {
    local icon="$1" summary="$2" body="$3"
    # Find current desktop session user
    local user session_bus
    user=$(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $3}' | head -1)
    if [[ -n "$user" ]]; then
        session_bus=$(loginctl show-user "$user" --property=Display --value 2>/dev/null || echo "")
        if [[ -n "$session_bus" ]]; then
            sudo -u "$user" \
                DISPLAY=:0 \
                DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u "$user")/bus" \
                notify-send \
                    --app-name="XII Hardware" \
                    --icon="$icon" \
                    "$summary" "$body" 2>/dev/null || true
        fi
    fi
}

# ────────────────────────────────────────────────────────────
# USB Storage Added
# ────────────────────────────────────────────────────────────
handle_usb_added() {
    _log "USB storage device connected"

    # Mount via udisksctl (no root needed if in plugdev group)
    local mount_point
    mount_point=$(udisksctl mount --block-device "/dev/$DEVICE" --no-user-interaction 2>/dev/null \
        | grep -oP 'at \K.*' || echo "")

    if [[ -n "$mount_point" ]]; then
        _log "Mounted at $mount_point"
        _notify_user "drive-removable-media" \
            "USB Drive Connected" \
            "Mounted at $mount_point"

        # Open in XII Files if a desktop session is active
        local user
        user=$(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $3}' | head -1)
        if [[ -n "$user" ]]; then
            sudo -u "$user" \
                WAYLAND_DISPLAY=wayland-1 \
                XDG_RUNTIME_DIR="/run/user/$(id -u "$user")" \
                xii-files "$mount_point" &
        fi
    else
        _notify_user "drive-removable-media" \
            "USB Drive Connected" \
            "Could not auto-mount /dev/$DEVICE"
    fi
}

# ────────────────────────────────────────────────────────────
# Device Removed
# ────────────────────────────────────────────────────────────
handle_removed() {
    _log "Device removed"
    # Try unmounting if still mounted
    udisksctl unmount --block-device "/dev/$DEVICE" --no-user-interaction 2>/dev/null || true
    udisksctl power-off --block-device "/dev/$DEVICE" --no-user-interaction 2>/dev/null || true
    _notify_user "drive-removable-media" \
        "USB Drive Removed" \
        "Safely ejected /dev/$DEVICE"
}

# ────────────────────────────────────────────────────────────
# Display Added
# ────────────────────────────────────────────────────────────
handle_display_added() {
    _log "Display connected"
    _notify_user "video-display" \
        "Display Connected" \
        "External monitor detected. Open Settings → Display to configure."

    # Trigger Hyprland to re-detect monitors
    local user
    user=$(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $3}' | head -1)
    if [[ -n "$user" ]]; then
        sudo -u "$user" \
            HYPRLAND_INSTANCE_SIGNATURE="$(ls /tmp/hypr/ 2>/dev/null | head -1)" \
            hyprctl reload 2>/dev/null || true
    fi
}

# ────────────────────────────────────────────────────────────
# Display Removed
# ────────────────────────────────────────────────────────────
handle_display_removed() {
    _log "Display disconnected"
    _notify_user "video-display" \
        "Display Disconnected" \
        "External monitor removed. Windows moved to primary display."
}

# ────────────────────────────────────────────────────────────
# Dispatch
# ────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_FILE")"

case "$EVENT" in
    usb-added)       handle_usb_added    ;;
    removed)         handle_removed      ;;
    display-added)   handle_display_added ;;
    display-removed) handle_display_removed ;;
    *)
        echo "Unknown event: $EVENT" >&2
        exit 1
        ;;
esac
