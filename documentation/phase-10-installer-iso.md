# XII OS — Phase 10: Live Installer & Hybrid ISO Specification

## 1. Overview

Phase 10 ส่งมอบตัวติดตั้งระบบแบบกราฟิก (Graphical Live Installer) และกระบวนการสร้างอิมเมจ Hybrid ISO (UEFI + BIOS):
- **XII Live Installer (`xii-installer`):** โปรแกรม Wizard (GTK4/Libadwaita) แนะนำขั้นตอนการติดตั้งอย่างเรียบง่าย
- **Installer Backend Engine (`installer_backend.py`):** ค้นหาอุปกรณ์ดิสก์, กำหนด Partition GPT, ฟอร์แมต Btrfs, สร้างผู้ใช้และตั้งค่า XII Mode
- **Hybrid ISO Builder (`scripts/build-iso.sh`):** ประกอบ Live ISO บูตได้ทั้งบน UEFI (x86-64) และ Legacy BIOS ผ่าน xorriso El Torito
- **ISO Verifier (`scripts/verify-iso.py`):** เครื่องมือตรวจสอบความสมบูรณ์ของ ISO image อัตโนมัติ

---

## 2. Installation Wizard Steps

```
[ Step 1: Welcome ] ──► Language & Keyboard selection (Thai / English)
         │
         ▼
[ Step 2: Target Drive ] ──► Auto-detect SSD/NVMe, Btrfs subvolumes layout
         │
         ▼
[ Step 3: User Setup ] ──► Hostname, Username, Password, Auto-login
         │
         ▼
[ Step 4: XII Mode ] ──► Lite / Standard / Performance default profile
         │
         ▼
[ Step 5: Install & Progress ] ──► Extract rootfs, configure GRUB, finalize
         │
         ▼
[ Step 6: Complete ] ──► Reboot now or continue testing Live session
```

---

## 3. Files Created

- `installer/installer_backend.py` — Disk inspection and installation backend
- `installer/xii-installer.py` — GTK4 Live Installer Wizard
- `installer/xii-installer.css` — Modern glassmorphic styling
- `installer/xii-installer.desktop` — Desktop shortcut for Live desktop session
- `scripts/verify-iso.py` — ISO integrity validation tool
- `tests/test_installer_iso.py` — Test suite for Phase 10
