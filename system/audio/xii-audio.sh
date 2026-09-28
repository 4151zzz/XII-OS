#!/usr/bin/env bash
# =============================================================
# XII OS — Audio Control Helper
# system/audio/xii-audio.sh
#
# Thin wrapper around wpctl (WirePlumber) and pactl (PulseAudio
# compat) for scripting audio controls from Hyprland keybinds,
# Waybar click actions, and xii-mode switching.
#
# Usage:
#   xii-audio volume up [5]        # Increase by 5% (default)
#   xii-audio volume down [5]
#   xii-audio volume set 75        # Set to 75%
#   xii-audio volume get           # Print current volume %
#   xii-audio mute toggle          # Toggle mute
#   xii-audio mute on|off
#   xii-audio sink list            # List output devices
#   xii-audio sink set <id>        # Set default output
#   xii-audio source list          # List input devices
#   xii-audio source set <id>      # Set default input
#   xii-audio mode lite|standard|performance
#                                  # Adjust quantum for XII mode
# =============================================================

set -euo pipefail

CMD="${1:-}"
shift || true

# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────
_wpctl() { wpctl "$@" 2>/dev/null; }
_notify() {
    local msg="$1" icon="${2:-audio-speakers}"
    notify-send --app-name="XII Audio" --icon="$icon" \
                --expire-time=2000 "XII Audio" "$msg" 2>/dev/null || true
}

_get_volume() {
    _wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null \
        | awk '{printf "%.0f", $2 * 100}'
}

_is_muted() {
    _wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null | grep -q "MUTED"
}

# ────────────────────────────────────────────────────────────
# Commands
# ────────────────────────────────────────────────────────────
case "$CMD" in

  volume)
    SUBCMD="${1:-get}"
    AMOUNT="${2:-5}"
    case "$SUBCMD" in
      up)
        _wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ "${AMOUNT}%+"
        VOL=$(_get_volume)
        _notify "Volume: ${VOL}%" "audio-volume-high"
        ;;
      down)
        _wpctl set-volume @DEFAULT_AUDIO_SINK@ "${AMOUNT}%-"
        VOL=$(_get_volume)
        _notify "Volume: ${VOL}%" "audio-volume-low"
        ;;
      set)
        LEVEL="${1:-70}"
        _wpctl set-volume @DEFAULT_AUDIO_SINK@ "${LEVEL}%"
        _notify "Volume set to ${LEVEL}%"
        ;;
      get)
        echo "$(_get_volume)%"
        ;;
    esac
    ;;

  mute)
    SUBCMD="${1:-toggle}"
    case "$SUBCMD" in
      toggle)
        _wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle
        if _is_muted; then
            _notify "Muted" "audio-volume-muted"
        else
            VOL=$(_get_volume)
            _notify "Unmuted (${VOL}%)" "audio-volume-high"
        fi
        ;;
      on)
        _wpctl set-mute @DEFAULT_AUDIO_SINK@ 1
        _notify "Muted" "audio-volume-muted"
        ;;
      off)
        _wpctl set-mute @DEFAULT_AUDIO_SINK@ 0
        VOL=$(_get_volume)
        _notify "Unmuted (${VOL}%)"
        ;;
    esac
    ;;

  mic)
    SUBCMD="${1:-toggle}"
    case "$SUBCMD" in
      mute)   _wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 1; _notify "Microphone muted" "microphone-sensitivity-muted" ;;
      unmute) _wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0; _notify "Microphone active" "microphone-sensitivity-high" ;;
      toggle)
        _wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
        _notify "Microphone toggled" "microphone-sensitivity-medium"
        ;;
    esac
    ;;

  sink)
    SUBCMD="${1:-list}"
    case "$SUBCMD" in
      list)
        wpctl status | grep -A30 "Audio" | grep "Sinks" -A20 | head -20
        ;;
      set)
        wpctl set-default "${2:-}"
        _notify "Output device changed"
        ;;
    esac
    ;;

  source)
    SUBCMD="${1:-list}"
    case "$SUBCMD" in
      list)
        wpctl status | grep -A30 "Audio" | grep "Sources" -A20 | head -20
        ;;
      set)
        wpctl set-default "${2:-}"
        _notify "Input device changed"
        ;;
    esac
    ;;

  mode)
    # Adjust PipeWire quantum for XII Performance Mode
    MODE="${1:-standard}"
    case "$MODE" in
      lite)
        # Larger buffer = less CPU, more battery
        pw-metadata -n settings 0 clock.quantum 1024
        pw-metadata -n settings 0 clock.min-quantum 512
        _notify "Audio: Lite Mode (low power)"
        ;;
      standard)
        pw-metadata -n settings 0 clock.quantum 256
        pw-metadata -n settings 0 clock.min-quantum 128
        _notify "Audio: Standard Mode"
        ;;
      performance)
        # Smallest buffer = lowest latency
        pw-metadata -n settings 0 clock.quantum 128
        pw-metadata -n settings 0 clock.min-quantum 32
        _notify "Audio: Performance Mode (low latency)"
        ;;
    esac
    ;;

  status)
    echo "=== XII OS Audio Status ==="
    echo "Volume:  $(_get_volume)%"
    if _is_muted; then echo "Muted:   YES"; else echo "Muted:   NO"; fi
    echo ""
    wpctl status
    ;;

  *)
    echo "Usage: xii-audio <command> [args]"
    echo ""
    echo "Commands:"
    echo "  volume  up|down|set|get [amount]"
    echo "  mute    toggle|on|off"
    echo "  mic     mute|unmute|toggle"
    echo "  sink    list|set [id]"
    echo "  source  list|set [id]"
    echo "  mode    lite|standard|performance"
    echo "  status"
    exit 1
    ;;
esac
