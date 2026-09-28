#!/usr/bin/env bash
# ============================================================
# XII OS — QEMU Boot Test Runner (Linux / WSL)
# scripts/run-qemu.sh
# ============================================================
# Launches XII OS in QEMU for boot verification.
#
# Requirements:
#   - qemu-system-x86_64
#   - An ISO at build/xii-os-1.0-genesis-amd64.iso
#     (or specify with --iso <path>)
#
# Usage:
#   bash run-qemu.sh                         # boot from default ISO
#   bash run-qemu.sh --iso <path>            # boot a specific ISO
#   bash run-qemu.sh --mode uefi             # boot in UEFI mode (default)
#   bash run-qemu.sh --mode bios             # boot in legacy BIOS mode
#   bash run-qemu.sh --ram 2048              # allocate 2 GB RAM (default: 2048)
#   bash run-qemu.sh --headless              # no display window (serial only)
#   bash run-qemu.sh --measure-ram           # wait for boot then report RAM usage
# ============================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ────────────────────────────────────────────────────────────
# Defaults
# ────────────────────────────────────────────────────────────
ISO_PATH="$PROJECT_ROOT/build/xii-os-1.0-genesis-amd64.iso"
BOOT_MODE="uefi"
RAM_MB=2048
CPUS=2
HEADLESS=false
MEASURE_RAM=false
OVMF_CODE="/usr/share/OVMF/OVMF_CODE.fd"
OVMF_VARS="/usr/share/OVMF/OVMF_VARS.fd"
QEMU_DISPLAY="sdl"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --iso)         ISO_PATH="$2"; shift 2 ;;
        --mode)        BOOT_MODE="$2"; shift 2 ;;
        --ram)         RAM_MB="$2"; shift 2 ;;
        --cpus)        CPUS="$2"; shift 2 ;;
        --headless)    HEADLESS=true; shift ;;
        --measure-ram) MEASURE_RAM=true; shift ;;
        --help|-h)
            echo "Usage: $0 [--iso <file>] [--mode uefi|bios] [--ram <MB>] [--headless]"
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

C_BOLD="\033[1m"; C_CYAN="\033[36m"; C_GREEN="\033[32m"
C_YELLOW="\033[33m"; C_RED="\033[31m"; C_RESET="\033[0m"

log() { echo -e "${C_BOLD}[XII QEMU]${C_RESET} $*"; }
ok()  { echo -e "${C_GREEN}  ✓ $*${C_RESET}"; }
die() { echo -e "${C_RED}  ✗ ERROR: $*${C_RESET}" >&2; exit 1; }
sep() { echo -e "${C_CYAN}──────────────────────────────────────────────${C_RESET}"; }

sep
log "XII OS QEMU Boot Test"
log "ISO         : $ISO_PATH"
log "Boot Mode   : $BOOT_MODE (QEMU x86_64)"
log "RAM         : ${RAM_MB} MB | CPUs: $CPUS"
sep

# ────────────────────────────────────────────────────────────
# Preflight
# ────────────────────────────────────────────────────────────
command -v qemu-system-x86_64 &>/dev/null || \
    die "qemu-system-x86_64 not found. Install: sudo apt install qemu-system-x86"
[[ -f "$ISO_PATH" ]] || die "ISO not found at: $ISO_PATH\n  Run: bash build-iso.sh"
ok "QEMU and ISO found."

# ────────────────────────────────────────────────────────────
# Build QEMU command
# ────────────────────────────────────────────────────────────
QEMU_ARGS=(
    -name "XII OS — Phase 1 Boot Test"
    -machine type=q35,accel=kvm:tcg
    -cpu host,+avx2
    -smp "$CPUS"
    -m "${RAM_MB}M"
    -cdrom "$ISO_PATH"
    -boot d
    -audiodev none,id=noaudio
    -device virtio-net-pci,netdev=net0
    -netdev user,id=net0
    -device virtio-balloon-pci
    -device virtio-rng-pci
    -serial mon:stdio
)

# UEFI vs BIOS
if [[ "$BOOT_MODE" == "uefi" ]]; then
    if [[ -f "$OVMF_CODE" ]]; then
        QEMU_ARGS+=(
            -drive "if=pflash,format=raw,readonly=on,file=${OVMF_CODE}"
            -drive "if=pflash,format=raw,file=${OVMF_VARS}"
        )
        ok "UEFI mode: using OVMF firmware"
    else
        log "OVMF not found at $OVMF_CODE — UEFI mode unavailable, falling back to BIOS."
        BOOT_MODE="bios"
    fi
fi

# Display
if [[ "$HEADLESS" == true ]]; then
    QEMU_ARGS+=(-display none -vga none)
    log "Headless mode: boot messages via serial console below."
else
    QEMU_ARGS+=(-display "$QEMU_DISPLAY" -vga virtio)
fi

# ────────────────────────────────────────────────────────────
# Launch QEMU
# ────────────────────────────────────────────────────────────
sep
log "Launching QEMU..."
log "Press Ctrl+A then X to quit (serial), or close the window."
sep

if [[ "$MEASURE_RAM" == true ]]; then
    log "RAM measurement mode enabled — check output after system boots."
fi

qemu-system-x86_64 "${QEMU_ARGS[@]}"
