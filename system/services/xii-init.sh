#!/usr/bin/env bash
# ============================================================
# XII OS — First Boot Initialization Script
# /usr/lib/xii-os/xii-init.sh
# ============================================================
# Runs once per boot (via xii-init.service, triggered by
# systemd before multi-user.target).
#
# Responsibilities:
#   1. Verify XII OS environment integrity
#   2. Apply ZRAM compressed swap
#   3. Apply sysctl performance tuning
#   4. Apply selected Performance Mode via xii-mode
#   5. Write boot timestamp to journal
# ============================================================

set -euo pipefail

readonly XII_VERSION_FILE="/etc/xii-os/version"
readonly XII_MODE_FILE="/etc/xii-os/current-mode"
readonly XII_LOG_TAG="xii-init"

log()  { systemd-cat -t "$XII_LOG_TAG" -p info  echo "$*"; echo "[XII INIT] $*"; }
warn() { systemd-cat -t "$XII_LOG_TAG" -p warning echo "$*"; echo "[XII INIT WARN] $*"; }
err()  { systemd-cat -t "$XII_LOG_TAG" -p err  echo "$*"; echo "[XII INIT ERR] $*" >&2; }

# ────────────────────────────────────────────────────────────
# 1. Environment Check
# ────────────────────────────────────────────────────────────
log "XII OS Initialization starting..."

if [[ ! -f "$XII_VERSION_FILE" ]]; then
    warn "XII OS version file not found at $XII_VERSION_FILE — skipping XII-specific tuning."
    exit 0
fi

XII_VERSION=$(cat "$XII_VERSION_FILE")
log "XII OS version: $XII_VERSION"

# ────────────────────────────────────────────────────────────
# 2. ZRAM Compressed Swap Setup
# ────────────────────────────────────────────────────────────
setup_zram() {
    log "Setting up ZRAM compressed swap..."

    # Determine ZRAM size based on current performance mode
    local current_mode="standard"
    if [[ -f "$XII_MODE_FILE" ]]; then
        current_mode=$(cat "$XII_MODE_FILE" | tr -d '[:space:]')
    fi

    local zram_size
    case "$current_mode" in
        lite)        zram_size="50%"  ;;  # 50% of RAM for aggressive compression
        standard)    zram_size="25%"  ;;  # 25% of RAM — balanced
        performance) zram_size="10%"  ;;  # Minimal, prefer physical RAM
        *)           zram_size="25%"  ;;
    esac

    if modprobe zram 2>/dev/null; then
        local total_ram_kb
        total_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        local zram_size_bytes
        # Calculate size: percentage of total RAM in bytes
        # Using awk for arithmetic to avoid bash float issues
        zram_size_bytes=$(awk -v ram_kb="$total_ram_kb" -v pct="${zram_size//%/}" \
            'BEGIN { printf "%d", (ram_kb * 1024 * pct / 100) }')

        echo zstd > /sys/block/zram0/comp_algorithm 2>/dev/null || \
            echo lz4  > /sys/block/zram0/comp_algorithm 2>/dev/null || \
            echo lzo   > /sys/block/zram0/comp_algorithm

        echo "$zram_size_bytes" > /sys/block/zram0/disksize
        mkswap /dev/zram0 -q && swapon /dev/zram0 -p 100
        log "ZRAM swap enabled: ${zram_size} of RAM, algorithm=$(cat /sys/block/zram0/comp_algorithm)"
    else
        warn "ZRAM module not available — skipping compressed swap."
    fi
}

setup_zram || warn "ZRAM setup encountered an error — system continues without ZRAM."

# ────────────────────────────────────────────────────────────
# 3. Apply sysctl Tuning
# ────────────────────────────────────────────────────────────
log "Applying XII OS sysctl performance parameters..."
if [[ -d /etc/sysctl.d ]]; then
    sysctl --system --quiet 2>/dev/null && log "sysctl parameters applied successfully." \
        || warn "Some sysctl parameters failed to apply."
fi

# ────────────────────────────────────────────────────────────
# 4. Apply Performance Mode
# ────────────────────────────────────────────────────────────
# Read boot-time mode from kernel cmdline (xii.mode=<mode>)
KERNEL_MODE=$(grep -oP '(?<=xii\.mode=)\S+' /proc/cmdline || true)
if [[ -n "$KERNEL_MODE" ]]; then
    log "Kernel cmdline requested mode: $KERNEL_MODE"
    if command -v xii-mode &>/dev/null; then
        xii-mode set "$KERNEL_MODE" && log "Performance mode set to: $KERNEL_MODE" \
            || warn "xii-mode failed to apply mode: $KERNEL_MODE"
    else
        warn "xii-mode CLI not found — writing mode file directly."
        echo "$KERNEL_MODE" > "$XII_MODE_FILE"
    fi
else
    log "No xii.mode in kernel cmdline — using persisted mode: $(cat "$XII_MODE_FILE" 2>/dev/null || echo standard)"
fi

# ────────────────────────────────────────────────────────────
# 5. Log Boot Timestamp
# ────────────────────────────────────────────────────────────
BOOT_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$BOOT_TS" > /run/xii-os/last-boot-timestamp 2>/dev/null || true
log "XII OS initialization complete. Boot timestamp: $BOOT_TS"
