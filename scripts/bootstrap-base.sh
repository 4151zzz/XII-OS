#!/usr/bin/env bash
# ============================================================
# XII OS — Bootstrap Base Script
# scripts/bootstrap-base.sh
# ============================================================
# Builds a minimal Debian-based rootfs for XII OS Phase 1.
#
# Requirements:
#   - Debian/Ubuntu host (or Debian WSL environment)
#   - debootstrap or mmdebstrap installed
#   - Root privileges (or fakechroot + fakeroot for non-root build)
#   - ~2 GB free disk space for the rootfs
#
# Usage:
#   sudo bash bootstrap-base.sh [--output <dir>] [--arch amd64]
#   bash bootstrap-base.sh --dry-run
# ============================================================

set -euo pipefail

# ────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly PACKAGE_MANIFEST="$PROJECT_ROOT/build/manifests/base-packages.txt"

ROOTFS_OUTPUT="${1:-$PROJECT_ROOT/build/rootfs}"
DEBIAN_MIRROR="https://deb.debian.org/debian"
DEBIAN_SUITE="bookworm"   # Debian 12 Stable LTS
ARCH="amd64"
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)  ROOTFS_OUTPUT="$2"; shift 2 ;;
        --arch)    ARCH="$2"; shift 2 ;;
        --mirror)  DEBIAN_MIRROR="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--output <dir>] [--arch <arch>] [--mirror <url>] [--dry-run]"
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

# ────────────────────────────────────────────────────────────
# Color Helpers
# ────────────────────────────────────────────────────────────
C_BOLD="\033[1m"; C_CYAN="\033[36m"; C_GREEN="\033[32m"
C_YELLOW="\033[33m"; C_RED="\033[31m"; C_RESET="\033[0m"

log()   { echo -e "${C_BOLD}[XII BOOTSTRAP]${C_RESET} $*"; }
ok()    { echo -e "${C_GREEN}    ✓ $*${C_RESET}"; }
warn()  { echo -e "${C_YELLOW}  ⚠ $*${C_RESET}"; }
die()   { echo -e "${C_RED}  ✗ ERROR: $*${C_RESET}" >&2; exit 1; }
sep()   { echo -e "${C_CYAN}──────────────────────────────────────────────${C_RESET}"; }

sep
log "XII OS Phase 1 — Rootfs Bootstrap"
log "Output directory : $ROOTFS_OUTPUT"
log "Debian suite     : $DEBIAN_SUITE ($ARCH)"
log "Mirror           : $DEBIAN_MIRROR"
[[ "$DRY_RUN" == true ]] && log "Mode             : DRY RUN (no changes will be made)"
sep

# ────────────────────────────────────────────────────────────
# Preflight checks
# ────────────────────────────────────────────────────────────
log "Step 1/6: Preflight checks..."

if [[ "$DRY_RUN" == false && $EUID -ne 0 ]]; then
    die "This script must be run as root (or with --dry-run for testing)."
fi

if [[ "$DRY_RUN" == false ]]; then
    if command -v mmdebstrap &>/dev/null; then
        BOOTSTRAP_CMD="mmdebstrap"
    elif command -v debootstrap &>/dev/null; then
        BOOTSTRAP_CMD="debootstrap"
    else
        die "Neither 'mmdebstrap' nor 'debootstrap' found. Install one:\n  sudo apt install mmdebstrap"
    fi
    ok "Bootstrap tool: $BOOTSTRAP_CMD"
fi

[[ -f "$PACKAGE_MANIFEST" ]] || die "Package manifest not found at: $PACKAGE_MANIFEST"
ok "Package manifest found."

# Build package include list (strip comments and blanks)
PACKAGES=$(grep -v '^#' "$PACKAGE_MANIFEST" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
ok "Packages loaded: $(echo "$PACKAGES" | tr ',' '\n' | wc -l) packages"

# ────────────────────────────────────────────────────────────
# Create output directory
# ────────────────────────────────────────────────────────────
log "Step 2/6: Preparing output directory..."
if [[ "$DRY_RUN" == false ]]; then
    if [[ -d "$ROOTFS_OUTPUT" && "$(ls -A "$ROOTFS_OUTPUT")" ]]; then
        warn "Output directory exists and is not empty: $ROOTFS_OUTPUT"
        warn "Proceeding may overwrite existing rootfs."
        read -rp "  Continue? [y/N] " confirm
        [[ "${confirm,,}" == "y" ]] || { log "Aborted by user."; exit 0; }
        rm -rf "$ROOTFS_OUTPUT"
    fi
    mkdir -p "$ROOTFS_OUTPUT"
    ok "Directory ready: $ROOTFS_OUTPUT"
else
    ok "[DRY RUN] Would create: $ROOTFS_OUTPUT"
fi

# ────────────────────────────────────────────────────────────
# Bootstrap rootfs
# ────────────────────────────────────────────────────────────
log "Step 3/6: Running Debian bootstrap (this takes a few minutes)..."
if [[ "$DRY_RUN" == false ]]; then
    if [[ "$BOOTSTRAP_CMD" == "mmdebstrap" ]]; then
        mmdebstrap --arch="$ARCH" \
            --include="$PACKAGES" \
            --variant=minbase \
            "$DEBIAN_SUITE" "$ROOTFS_OUTPUT" "$DEBIAN_MIRROR"
    else
        debootstrap --arch="$ARCH" \
            --include="$PACKAGES" \
            --variant=minbase \
            "$DEBIAN_SUITE" "$ROOTFS_OUTPUT" "$DEBIAN_MIRROR"
    fi
    ok "Debian base bootstrapped successfully."
else
    ok "[DRY RUN] Would run: $BOOTSTRAP_CMD --arch=$ARCH --variant=minbase $DEBIAN_SUITE $ROOTFS_OUTPUT"
fi

# ────────────────────────────────────────────────────────────
# Install XII OS files into rootfs
# ────────────────────────────────────────────────────────────
log "Step 4/6: Installing XII OS system files..."
if [[ "$DRY_RUN" == false ]]; then
    # os-release
    install -Dm644 "$PROJECT_ROOT/system/os-release" "$ROOTFS_OUTPUT/etc/os-release"
    ok "Installed /etc/os-release"

    # XII OS version tag
    mkdir -p "$ROOTFS_OUTPUT/etc/xii-os"
    echo "1.0 (Genesis)" > "$ROOTFS_OUTPUT/etc/xii-os/version"
    echo "standard" > "$ROOTFS_OUTPUT/etc/xii-os/current-mode"
    ok "Installed /etc/xii-os/version and current-mode"

    # xii-mode CLI
    install -Dm755 "$PROJECT_ROOT/system/services/xii-mode" "$ROOTFS_OUTPUT/usr/bin/xii-mode"
    ok "Installed /usr/bin/xii-mode"

    # systemd services
    install -Dm644 "$PROJECT_ROOT/system/services/xii-init.service" \
        "$ROOTFS_OUTPUT/usr/lib/systemd/system/xii-init.service"
    install -Dm644 "$PROJECT_ROOT/system/services/xii-mode.service" \
        "$ROOTFS_OUTPUT/usr/lib/systemd/system/xii-mode.service"
    install -Dm755 "$PROJECT_ROOT/system/services/xii-init.sh" \
        "$ROOTFS_OUTPUT/usr/lib/xii-os/xii-init.sh"
    ok "Installed systemd services"

    # Enable services via symlink
    mkdir -p "$ROOTFS_OUTPUT/etc/systemd/system/multi-user.target.wants"
    ln -sf "/usr/lib/systemd/system/xii-init.service" \
        "$ROOTFS_OUTPUT/etc/systemd/system/multi-user.target.wants/xii-init.service"
    ln -sf "/usr/lib/systemd/system/xii-mode.service" \
        "$ROOTFS_OUTPUT/etc/systemd/system/multi-user.target.wants/xii-mode.service"
    ok "Enabled xii-init and xii-mode services"

    # Sysctl tuning
    install -Dm644 "$PROJECT_ROOT/kernel/sysctl.d/99-xii-performance.conf" \
        "$ROOTFS_OUTPUT/etc/sysctl.d/99-xii-performance.conf"
    ok "Installed sysctl tuning"
else
    ok "[DRY RUN] Would install XII OS files into rootfs"
fi

# ────────────────────────────────────────────────────────────
# Configure ZRAM
# ────────────────────────────────────────────────────────────
log "Step 5/6: Configuring ZRAM..."
if [[ "$DRY_RUN" == false ]]; then
    cat > "$ROOTFS_OUTPUT/etc/default/zramswap" <<'EOF'
# XII OS — ZRAM Swap Configuration
# Managed by xii-init.sh at boot (size adapts per xii-mode)
ALGO=zstd
PERCENT=25
PRIORITY=100
EOF
    ok "ZRAM swap configuration written"
else
    ok "[DRY RUN] Would configure ZRAM"
fi

# ────────────────────────────────────────────────────────────
# Summary
# ────────────────────────────────────────────────────────────
sep
log "Step 6/6: Bootstrap complete!"
echo ""
if [[ "$DRY_RUN" == false ]]; then
    ROOTFS_SIZE=$(du -sh "$ROOTFS_OUTPUT" 2>/dev/null | cut -f1 || echo "?")
    echo -e "  Rootfs location : ${C_CYAN}$ROOTFS_OUTPUT${C_RESET}"
    echo -e "  Rootfs size     : ${C_CYAN}$ROOTFS_SIZE${C_RESET}"
    echo ""
    echo -e "  ${C_BOLD}Next step:${C_RESET} Run build-iso.sh to create the bootable ISO"
    echo -e "  ${C_BOLD}Or test:${C_RESET}   Run run-qemu.sh to verify the base system in QEMU"
else
    echo -e "  ${C_YELLOW}Dry run complete — no changes were made.${C_RESET}"
fi
sep
