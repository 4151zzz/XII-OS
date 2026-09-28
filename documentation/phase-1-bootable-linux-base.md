# Phase 1: Bootable Linux Base — Specification & Plan

## 1. Architecture

Phase 1 มุ่งเน้นการสร้างแกนระบบ Linux พื้นฐาน (Minimal Bootable Base) สำหรับสถาปัตยกรรม x86-64 โดยให้มีความจุเล็ก กะทัดรัด บูตได้ทั้งบน UEFI และ Legacy BIOS

```
+--------------------------------------------------------------+
|                     XII OS Bootloader                        |
|  - GRUB 2.12+ (x86_64-efi & i386-pc hybrid)                  |
|  - XII Splash / Quiet Boot                                   |
|  - Boot Profile Entries:                                     |
|    * XII OS Standard Mode (Default)                          |
|    * XII OS Lite Mode (Low Memory / nomodeset option)        |
|    * XII OS Performance Mode (GPU / High Throughput)         |
|    * XII OS Recovery & Maintenance Mode                      |
+--------------------------------------------------------------+
                               ↓
+--------------------------------------------------------------+
|                    Linux LTS Kernel 6.x                      |
|  - Parameters: quiet splash loglevel=3 mitigations=auto      |
|  - ZRAM Module (Compressed swap with zstd)                   |
|  - Optimized sysctl (swappiness=10, vfs_cache_pressure=50)   |
+--------------------------------------------------------------+
                               ↓
+--------------------------------------------------------------+
|                   Systemd Init & Services                    |
|  - systemd-udevd (Hardware discovery)                        |
|  - systemd-journald (Optimized in-memory logging)            |
|  - xii-init.service (XII OS hardware & tuning bootstrap)     |
|  - xii-mode daemon/CLI (Lite / Standard / Performance)       |
+--------------------------------------------------------------+
                               ↓
+--------------------------------------------------------------+
|                 Minimal Root Filesystem                      |
|  - FHS Compliant structure (/etc/xii-os/version, etc.)       |
|  - Essential POSIX utilities + bash/coreutils                |
|  - Network base (iproute2, systemd-networkd / resolved)      |
|  - Test Harness for automated verification                   |
+--------------------------------------------------------------+
```

---

## 2. File Tree for Phase 1

```
xii-os/
├── boot/
│   ├── grub/
│   │   ├── grub.cfg               # Multi-profile GRUB configuration
│   │   └── xii-theme.txt          # Visual design tokens for bootloader
│   └── splash/
│       └── xii-boot-logo.svg      # Minimalist XII OS boot emblem
├── kernel/
│   ├── cmdline.conf               # Kernel command line parameters
│   └── sysctl.d/
│       └── 99-xii-performance.conf# Sysctl memory & disk responsiveness tuning
├── system/
│   ├── services/
│   │   ├── xii-init.service       # Boot initialization unit
│   │   ├── xii-init.sh            # First boot configuration script
│   │   ├── xii-mode               # Core CLI tool for switching OS modes
│   │   └── xii-mode.service       # Service that applies selected profile on boot
│   └── os-release                 # /etc/os-release identifying XII OS
├── build/
│   └── manifests/
│       └── base-packages.txt      # List of minimal required packages
├── scripts/
│   ├── bootstrap-base.sh          # Rootfs bootstrap builder
│   ├── build-iso.sh               # ISO generator script using xorriso
│   ├── run-qemu.sh                # Linux/WSL QEMU launcher
│   └── run-qemu.ps1               # Windows PowerShell QEMU launcher
└── tests/
    ├── test_base_system.py        # Automated test suite for base OS config
    └── test_boot_config.py        # GRUB config & boot profile validator
```

---

## 3. Dependencies

### Build Environment Dependencies:
- **`debootstrap` หรือ `mmdebstrap`:** สำหรับสร้าง Debian Minimal rootfs แบบ reproducible
- **`grub-pc-bin`, `grub-efi-amd64-bin`:** ไบนารี bootloader สำหรับสร้าง hybrid ISO
- **`xorriso`, `mksquashfs`:** สำหรับรวม squashfs และคอมไพล์เป็น bootable ISO
- **`python3` + `pytest` (หรือ unittest):** สำหรับรัน test suite อัตโนมัติ

### Runtime Base Dependencies:
- **`linux-image-amd64` (LTS Kernel):** เคอร์เนลมาตรฐาน x86-64
- **`systemd`, `udev`:** ระบบ init และ device management
- **`zram-tools`:** ระบบบีบอัด RAM swap
- **`sudo`, `bash`, `coreutils`, `iproute2`:** ยูทิลิตีระบบพื้นฐาน

---

## 4. Implementation Plan

1. **Boot Configuration:**
   - สร้างไฟล์ `boot/grub/grub.cfg` พร้อมเมนูบูต 4 ตัวเลือก: XII Standard, XII Lite, XII Performance และ XII Recovery Mode
   - กำหนด kernel command line arguments สำหรับแต่ละโหมด (เช่น Lite เพิ่ม `nomodeset` / ลด memory overhead)
2. **Kernel & Memory Tuning:**
   - สร้าง `kernel/sysctl.d/99-xii-performance.conf` ปรับแต่ง `vm.swappiness=10`, `vm.dirty_ratio=15`, `fs.inotify.max_user_watches=524288`
   - สร้างการคอนฟิก ZRAM อัตโนมัติ
3. **XII System Services:**
   - สร้าง `/etc/os-release` สำหรับระบุชื่อระบบ "XII OS" เวอร์ชัน "1.0 (Genesis)"
   - สร้าง `system/services/xii-mode` (CLI tool) สำหรับคำสั่ง `xii-mode set [lite|standard|performance]` และ `xii-mode get`
   - สร้าง `system/services/xii-mode.service` และ `system/services/xii-init.service`
4. **Build & Test Automation:**
   - สร้างสคริปต์ `scripts/bootstrap-base.sh` และ `scripts/build-iso.sh`
   - สร้างสคริปต์ `scripts/run-qemu.ps1` และ `scripts/run-qemu.sh`
   - สร้าง Unit/Integration tests ใน `tests/` เพื่อตรวจสอบว่าทุกคอนฟิกและสคริปต์มีความถูกต้อง 100%

---

## 5. Testing Plan

### Automated Tests:
1. **Config Syntax Validation:** ตรวจสอบไวยากรณ์ของ `grub.cfg`, `os-release`, `sysctl.conf` และ systemd units
2. **Mode Switcher Logic Test:** รัน Unit Test ตรวจสอบว่า `xii-mode` สลับโปรไฟล์ระหว่าง Lite, Standard และ Performance ได้ถูกต้องตามสเปก
3. **Package Manifest Completeness:** ตรวจสอบว่ารายการแพ็กเกจพื้นฐานไม่มี dependency ที่ขัดแย้งกัน

### Simulation / Virtual Machine Tests:
1. **QEMU Boot Emulation:** รันสคริปต์ทดสอบใน QEMU ตรวจสอบ GRUB screen และการโหลดเคอร์เนล
2. **RAM Footprint Verification:** วัดขนาดการใช้ RAM ใน headless base ต้องไม่เกิน 150 MB
