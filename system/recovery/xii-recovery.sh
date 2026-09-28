#!/bin/bash
# =============================================================
# XII OS — System Recovery Console
# system/recovery/xii-recovery.sh
#
# Interactive rescue environment for XII OS.
# Triggered via GRUB "XII OS (Recovery Mode)" entry.
# =============================================================

set -e

CYAN='\033[0;36m'
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_banner() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    XII OS RECOVERY CONSOLE                 ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo -e "  XII OS Version: 1.0 (Genesis) | Architecture: x86-64"
    echo -e "  System Emergency & Repair Environment"
    echo "------------------------------------------------------------"
}

show_menu() {
    echo -e "${YELLOW}Please select a recovery operation:${NC}"
    echo ""
    echo "  [1] Rollback to Previous System Snapshot (Btrfs / Backup)"
    echo "  [2] Check and Repair Filesystem (fsck)"
    echo "  [3] Reinstall & Repair GRUB Bootloader"
    echo "  [4] Reset User / Root Password"
    echo "  [5] Emergency Network Diagnostics"
    echo "  [6] Open Emergency Root Shell"
    echo "  [7] Reboot System"
    echo "  [8] Power Off"
    echo ""
    echo -n "Enter option [1-8]: "
}

do_snapshot_rollback() {
    echo -e "\n${CYAN}--- System Snapshot Rollback ---${NC}"
    if [ -x /usr/bin/xii-snapshot ]; then
        /usr/bin/xii-snapshot list
        echo ""
        read -p "Enter snapshot ID to restore (or press ENTER to cancel): " snap_id
        if [ -n "$snap_id" ]; then
            /usr/bin/xii-snapshot restore "$snap_id"
            echo -e "${GREEN}Rollback staged! Please reboot.${NC}"
        fi
    else
        echo -e "${RED}Snapshot utility xii-snapshot not found.${NC}"
    fi
    read -p "Press Enter to continue..."
}

do_fsck() {
    echo -e "\n${CYAN}--- Filesystem Check & Repair ---${NC}"
    echo "Checking unmounted root filesystem..."
    ROOT_DEV=$(findmnt -n -o SOURCE / || echo "/dev/sda2")
    echo "Root device: $ROOT_DEV"
    fsck -f -y "$ROOT_DEV" || true
    echo -e "${GREEN}Filesystem check complete.${NC}"
    read -p "Press Enter to continue..."
}

do_repair_grub() {
    echo -e "\n${CYAN}--- GRUB Bootloader Repair ---${NC}"
    read -p "Target drive for GRUB install (e.g., /dev/sda or /dev/nvme0n1): " drive
    if [ -n "$drive" ] && [ -b "$drive" ]; then
        echo "Installing GRUB to $drive..."
        grub-install "$drive" || true
        update-grub || true
        echo -e "${GREEN}GRUB bootloader reinstalled successfully.${NC}"
    else
        echo -e "${RED}Invalid block device.${NC}"
    fi
    read -p "Press Enter to continue..."
}

do_reset_password() {
    echo -e "\n${CYAN}--- Reset User Password ---${NC}"
    read -p "Enter username to reset password: " username
    if id "$username" >/dev/null 2>&1; then
        passwd "$username"
        echo -e "${GREEN}Password updated for user $username.${NC}"
    else
        echo -e "${RED}User $username does not exist.${NC}"
    fi
    read -p "Press Enter to continue..."
}

do_network_diag() {
    echo -e "\n${CYAN}--- Network Diagnostics ---${NC}"
    ip addr show
    echo ""
    ping -c 3 1.1.1.1 || echo -e "${RED}Ping test failed.${NC}"
    read -p "Press Enter to continue..."
}

do_emergency_shell() {
    echo -e "\n${YELLOW}Spawning root rescue shell. Type 'exit' to return to menu.${NC}"
    /bin/bash --login || /bin/sh
}

main() {
    while true; do
        show_banner
        show_menu
        read choice
        case "$choice" in
            1) do_snapshot_rollback ;;
            2) do_fsck ;;
            3) do_repair_grub ;;
            4) do_reset_password ;;
            5) do_network_diag ;;
            6) do_emergency_shell ;;
            7) reboot; exit 0 ;;
            8) poweroff; exit 0 ;;
            *) echo "Invalid option"; sleep 1 ;;
        esac
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
