#!/usr/bin/env bash
# ============================================================
# XII OS — ISO Build Script
# scripts/build-iso.sh
# ============================================================
# Assembles a bootable hybrid ISO (UEFI + BIOS) from the
# XII OS rootfs produced by bootstrap-base.sh.
#
# Requirements:
#   - xorriso
#   - squashfs-tools (mksquashfs)
#   - grub-pc-bin (for BIOS/i386-pc El Torito)
#   - grub-efi-amd64-bin (for UEFI)
#   - A bootstrapped rootfs at build/rootfs/
#
# Usage:
#   sudo bash build-iso.sh [--output <file>] [--rootfs <dir>]
# ============================================================

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ROOTFS_DIR="$PROJECT_ROOT/build/rootfs"
ISO_STAGING="$PROJECT_ROOT/build/iso-staging"
ISO_OUTPUT="$PROJECT_ROOT/build/xii-os-1.0-genesis-amd64.iso"
SQUASH_COMP="zstd"   # Best compression ratio + speed

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) ISO_OUTPUT="$2"; shift 2 ;;
        --rootfs) ROOTFS_DIR="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--output <iso>] [--rootfs <dir>]"
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

C_BOLD="\033[1m"; C_CYAN="\033[36m"; C_GREEN="\033[32m"
C_RED="\033[31m"; C_RESET="\033[0m"

log() { echo -e "${C_BOLD}[XII BUILD-ISO]${C_RESET} $*"; }
ok()  { echo -e "${C_GREEN}    ✓ $*${C_RESET}"; }
die() { echo -e "${C_RED}  ✗ ERROR: $*${C_RESET}" >&2; exit 1; }
sep() { echo -e "${C_CYAN}──────────────────────────────────────────────${C_RESET}"; }

sep
log "XII OS — ISO Builder"
log "Rootfs      : $ROOTFS_DIR"
log "ISO Output  : $ISO_OUTPUT"
sep

# ────────────────────────────────────────────────────────────
# Preflight
# ────────────────────────────────────────────────────────────
log "Step 1/5: Preflight checks..."
[[ $EUID -eq 0 ]] || die "Must be run as root."
command -v xorriso    &>/dev/null || die "xorriso not found. Install: sudo apt install xorriso"
command -v mksquashfs &>/dev/null || die "mksquashfs not found. Install: sudo apt install squashfs-tools"
[[ -d "$ROOTFS_DIR" ]] || die "Rootfs not found at $ROOTFS_DIR — run bootstrap-base.sh first."
ok "All preflight checks passed."

# ────────────────────────────────────────────────────────────
# Prepare ISO staging area
# ────────────────────────────────────────────────────────────
log "Step 2/5: Preparing ISO staging directory..."
rm -rf "$ISO_STAGING"
mkdir -p "$ISO_STAGING/boot/grub"
mkdir -p "$ISO_STAGING/live"
mkdir -p "$ISO_STAGING/EFI/BOOT"
ok "Staging directory ready: $ISO_STAGING"

# ────────────────────────────────────────────────────────────
# Compress rootfs into SquashFS
# ────────────────────────────────────────────────────────────
log "Step 3/5: Compressing rootfs into SquashFS ($SQUASH_COMP)..."
mksquashfs "$ROOTFS_DIR" "$ISO_STAGING/live/filesystem.squashfs" \
    -comp "$SQUASH_COMP" \
    -noappend \
    -no-progress \
    -e "$ROOTFS_DIR/proc" -e "$ROOTFS_DIR/sys" -e "$ROOTFS_DIR/dev" \
    -e "$ROOTFS_DIR/run" -e "$ROOTFS_DIR/tmp"
SQUASH_SIZE=$(du -sh "$ISO_STAGING/live/filesystem.squashfs" | cut -f1)
ok "SquashFS created: $SQUASH_SIZE"

# Copy kernel and initrd from rootfs
KERNEL=$(ls "$ROOTFS_DIR/boot/vmlinuz-"* 2>/dev/null | sort -V | tail -1)
INITRD=$(ls "$ROOTFS_DIR/boot/initrd.img-"* 2>/dev/null | sort -V | tail -1)
[[ -n "$KERNEL" ]] || die "No kernel found in rootfs/boot/"
[[ -n "$INITRD" ]] || die "No initrd found in rootfs/boot/"
cp "$KERNEL" "$ISO_STAGING/boot/vmlinuz"
cp "$INITRD" "$ISO_STAGING/boot/initrd.img"
ok "Kernel and initrd copied."

# ────────────────────────────────────────────────────────────
# Configure GRUB for ISO
# ────────────────────────────────────────────────────────────
log "Step 4/5: Configuring GRUB bootloader..."

# Copy XII GRUB theme
if [[ -d "$PROJECT_ROOT/boot/grub" ]]; then
    cp -r "$PROJECT_ROOT/boot/grub/"* "$ISO_STAGING/boot/grub/"
fi

# GRUB config for live ISO (root is squashfs)
cat > "$ISO_STAGING/boot/grub/grub.cfg" <<'GRUBEOF'
# XII OS — Live ISO GRUB Configuration
set default="0"
set timeout=5
set timeout_style=menu

set menu_color_normal=light-gray/black
set menu_color_highlight=cyan/black

insmod all_video
insmod gfxterm
insmod iso9660
set gfxmode=auto
terminal_output gfxterm

menuentry "XII OS — Standard Mode (Live)" --class xii-os --class gnu-linux {
    linux  /boot/vmlinuz boot=live quiet splash loglevel=3 xii.mode=standard
    initrd /boot/initrd.img
}

menuentry "XII OS — Lite Mode (Live)" --class xii-os-lite --class gnu-linux {
    linux  /boot/vmlinuz boot=live quiet splash loglevel=3 xii.mode=lite
    initrd /boot/initrd.img
}

menuentry "XII OS — Performance Mode (Live)" --class xii-os-perf --class gnu-linux {
    linux  /boot/vmlinuz boot=live quiet splash loglevel=3 xii.mode=performance
    initrd /boot/initrd.img
}

menuentry "XII OS — Recovery Mode" --class xii-os-recovery --class gnu-linux {
    linux  /boot/vmlinuz boot=live single nomodeset loglevel=7 xii.mode=recovery
    initrd /boot/initrd.img
}
GRUBEOF
ok "GRUB configuration written."

# Build GRUB hybrid EFI image
grub-mkstandalone \
    --format=x86_64-efi \
    --output="$ISO_STAGING/EFI/BOOT/BOOTX64.EFI" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$ISO_STAGING/boot/grub/grub.cfg"

# Build GRUB BIOS core image
grub-mkstandalone \
    --format=i386-pc \
    --output="$ISO_STAGING/boot/grub/core.img" \
    --locales="" \
    --fonts="" \
    "boot/grub/grub.cfg=$ISO_STAGING/boot/grub/grub.cfg"

cat /usr/lib/grub/i386-pc/cdboot.img "$ISO_STAGING/boot/grub/core.img" \
    > "$ISO_STAGING/boot/grub/bios.img"
ok "GRUB EFI and BIOS images built."

# ────────────────────────────────────────────────────────────
# Assemble final hybrid ISO with xorriso
# ────────────────────────────────────────────────────────────
log "Step 5/5: Assembling hybrid ISO with xorriso..."
mkdir -p "$(dirname "$ISO_OUTPUT")"

xorriso \
    -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "XII_OS_1_0" \
    -appid "XII OS 1.0 (Genesis)" \
    -publisher "XII OS Project" \
    -preparer "XII OS build-iso.sh" \
    --grub2-boot-info \
    --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img \
    -partition_offset 16 \
    --mbr-force-bootable \
    -append_partition 2 28732ac11ff8d211ba4b00a0c93ec93b "$ISO_STAGING/EFI/BOOT/BOOTX64.EFI" \
    -appended_part_as_gpt \
    -iso_mbr_part_type a2a0d0ebe5b9334487c068b6b72699c7 \
    -c boot/grub/boot.cat \
    --interval:appended_partition_2:all:: \
    -b boot/grub/bios.img \
    -no-emul-boot \
    -boot-load-size 4 \
    -boot-info-table \
    --efi-boot boot/grub/efi.img \
    -efi-boot-part --efi-boot-image \
    -o "$ISO_OUTPUT" \
    "$ISO_STAGING"

ISO_SIZE=$(du -sh "$ISO_OUTPUT" | cut -f1)

sep
log "ISO build complete!"
echo ""
echo -e "  Output ISO  : ${C_CYAN}$ISO_OUTPUT${C_RESET}"
echo -e "  ISO Size    : ${C_CYAN}$ISO_SIZE${C_RESET}"
echo ""
echo -e "  ${C_BOLD}Test in QEMU:${C_RESET}"
echo -e "    bash scripts/run-qemu.sh --iso \"$ISO_OUTPUT\""
echo -e "  ${C_BOLD}Write to USB (Linux):${C_RESET}"
echo -e "    sudo dd if=\"$ISO_OUTPUT\" of=/dev/sdX bs=4M status=progress"
sep
