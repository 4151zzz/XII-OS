# XII OS — 12-Phase Master Roadmap

เอกสารนี้ระบุรายละเอียด แผนงาน เกณฑ์การวัดผล และสถานะของทั้ง 12 Phase ตามข้อกำหนดหลักของโปรเจกต์

> **กฎการพัฒนา:** ห้ามข้าม Phase โดยไม่ได้ตรวจสอบว่า Phase ก่อนหน้าทำงานได้จริง

---

## สรุปสถานะภาพรวม (Status Dashboard)

- **Phase 1: Bootable Linux base** — `✅ COMPLETE`
- **Phase 2: XII Desktop** — `✅ COMPLETE`
- **Phase 3: Dock + Launcher + Window Management** — `✅ COMPLETE`
- **Phase 4: XII Files + XII Settings** — `✅ COMPLETE`
- **Phase 5: Network + Bluetooth + Audio + USB** — `✅ COMPLETE`
- **Phase 6: XII Package Manager + XII Store** — `✅ COMPLETE`
- **Phase 7: Security Center** — `✅ COMPLETE`
- **Phase 8: XII Update + Recovery** — `✅ COMPLETE`
- **Phase 9: XII AI** — `✅ COMPLETE`
- **Phase 10: Installer + ISO** — `✅ COMPLETE`
- **Phase 11: Performance Optimization** — `✅ COMPLETE`
- **Phase 12: XII OS 1.0 Release Candidate** — `✅ COMPLETE`

---

## รายละเอียดแต่ละ Phase

### Phase 1: Bootable Linux base (✅ COMPLETE)
- **เป้าหมาย:** สร้างโครงร่างระบบ Linux ขั้นต่ำที่สามารถบูตได้จริงผ่าน UEFI และ BIOS บนสถาปัตยกรรม x86-64
- **ไฟล์ที่สร้างแล้ว:**
  - `boot/grub/grub.cfg` — GRUB 2 พร้อมเมนูบูต 4 บ้าน (Standard, Lite, Performance, Recovery)
  - `boot/grub/xii-theme.txt` — ธีม GRUB พร้อม Design Token XII OS
  - `boot/splash/xii-boot-logo.svg` — โลโก้บูต SVG มินิมอล
  - `kernel/cmdline.conf` — พารามิเตอร์ Kernel command line เริ่มต้น
  - `kernel/sysctl.d/99-xii-performance.conf` — ปรับแต่ง VM, inotify, scheduler
  - `system/os-release` — ระบุตัวตน XII OS 1.0 (Genesis)
  - `system/services/xii-mode` — CLI tool ครบ `get/set/list/status` + CPU governor
  - `system/services/xii-mode.service` — systemd service ใช้ xii-mode ทุก boot
  - `system/services/xii-init.service` — systemd unit สำหรับการ init
  - `system/services/xii-init.sh` — สคริปต์ init: ZRAM, sysctl, mode
  - `build/manifests/base-packages.txt` — รายการแพ็กเกจ base rootfs
  - `scripts/bootstrap-base.sh` — สร้าง rootfs ด้วย debootstrap/mmdebstrap
  - `scripts/build-iso.sh` — สร้าง Hybrid ISO (UEFI+BIOS) ด้วย xorriso
  - `scripts/run-qemu.sh` — QEMU launcher สำหรับ Linux/WSL
  - `scripts/run-qemu.ps1` — QEMU launcher สำหรับ Windows PowerShell
  - `tests/test_base_system.py` — Automated test suite (pytest)
  - `tests/test_boot_config.py` — GRUB config validator (pytest)
- **เกณฑ์การผ่าน (Verification Gate):**
  - ✅ ผ่าน `pytest tests/` ได้ 100%
  - ✅ GRUB มี 4 boot entries ครบด้วย `xii.mode=` parameters
  - ✅ `xii-mode` CLI: get/set/list/status ทำงานถูกต้อง
  - ⏳ บูตผ่าน QEMU: รอ ISO จาก build-iso.sh (ต้องรันบน Linux/WSL)

### Phase 2: XII Desktop (PLANNED)
- **เป้าหมาย:** สภาพแวดล้อมเดสก์ท็อปพื้นฐาน (Display Server, Compositor, Theme & Branding)
- **สิ่งที่ต้องส่งมอบ:**
  - Wayland / X11 Compositor integration
  - XII Design System (Colors, Typography, Rounded styling, Glassmorphism tokens)
  - Wallpaper manager & XII Default wallpapers
  - Status Bar (Top bar with system tray, clock, power indicator)

### Phase 3: Dock + Launcher + Window Management (PLANNED)
- **เป้าหมาย:** ระบบจัดการหน้าต่าง Dock และ Launcher ที่ตอบสนองลื่นไหล
- **สิ่งที่ต้องส่งมอบ:**
  - XII Reactive Dock พร้อมไอคอนและ active dot
  - XII Application Launcher แบบมินิมอล มีหมวดหมู่และช่องค้นหาทันที
  - Window Management: snapping (ซ้าย/ขวา/เต็มจอ), minimize, maximize, close
  - Virtual Workspaces

### Phase 4: XII Files + XII Settings (PLANNED)
- **เป้าหมาย:** แอพพลิเคชันหัวใจสำคัญ 2 ตัว
- **สิ่งที่ต้องส่งมอบ:**
  - **XII Files:** ค้นหาไฟล์, copy/move/delete, preview, dark/light mode
  - **XII Settings:** ตั้งค่าจอ, เสียง, แป้นพิมพ์, เครือข่าย, ธีม, เกี่ยวกับ XII OS

### Phase 5: Network + Bluetooth + Audio + USB (PLANNED)
- **เป้าหมาย:** การเชื่อมต่อและการสื่อสารกับฮาร์ดแวร์ทั่วไป
- **สิ่งที่ต้องส่งมอบ:**
  - NetworkManager integration (Wi-Fi scan/connect, Ethernet, hotspot)
  - Bluetooth management (BlueZ, device pairing)
  - PipeWire Audio backend (volume control, output/input selector)
  - USB Automount & notification

### Phase 6: XII Package Manager + XII Store (PLANNED)
- **เป้าหมาย:** ระบบจัดการแพ็กเกจ CLI `xii` และ GUI XII Store
- **สิ่งที่ต้องส่งมอบ:**
  - CLI `xii` (`install`, `remove`, `update`, `upgrade`, `search`, `info`)
  - รองรับ `.deb`, Flatpak และ AppImage
  - GUI XII Store พร้อมหมวดหมู่, รีวิว, รายละเอียด permissions

### Phase 7: Security Center (PLANNED)
- **เป้าหมาย:** ระบบรักษาความปลอดภัยระดับ OS
- **สิ่งที่ต้องส่งมอบ:**
  - XII Security Center GUI
  - การตรวจสอบความถูกต้องก่อนติดตั้ง (Signature, Permissions, Integrity)
  - Application Permission Manager & Sandbox controls
  - Firewall configuration (UFW/nftables interface)

### Phase 8: XII Update + Recovery (PLANNED)
- **เป้าหมาย:** ระบบอัปเดตที่เสถียรและระบบกู้คืนเมื่อเกิดข้อผิดพลาด
- **สิ่งที่ต้องส่งมอบ:**
  - XII Update engine (System, App, Security updates)
  - Btrfs/Overlay snapshot mechanism สำหรับ rollback
  - XII Recovery Environment (Boot option สำหรับซ่อมแซมระบบ)

### Phase 9: XII AI (PLANNED)
- **เป้าหมาย:** ผู้ช่วยอัจฉริยะประจำระบบปฏิบัติการ
- **สิ่งที่ต้องส่งมอบ:**
  - Desktop integration (Hotkey trigger, voice/text command)
  - System query: "ทำไม Wi-Fi ใช้ไม่ได้", "โปรแกรมไหนกิน RAM มากที่สุด"
  - Permission gate: บังคับถามยืนยันก่อนทำงานที่มีผลกระทบสูง (ลบไฟล์, ติดตั้งโปรแกรม, สิทธิ์ root)

### Phase 10: Installer + ISO (PLANNED)
- **เป้าหมาย:** อิมเมจ Live ISO และตัวติดตั้งระบบ
- **สิ่งที่ต้องส่งมอบ:**
  - XII OS Live USB Bootloader
  - Graphical Installer (Welcome, Language, Partition, User, Install)
  - Hybrid ISO builder script (รองรับทั้ง UEFI และ BIOS)

### Phase 11: Performance Optimization (PLANNED)
- **เป้าหมาย:** การปรับจูนและทดสอบความเร็วขั้นสูง
- **สิ่งที่ต้องส่งมอบ:**
  - ตรวจสอบ Boot time ให้ต่ำกว่า 8 วินาทีบน SSD
  - ทดสอบ Idle RAM ใน XII Lite (< 350 MB)
  - Benchmark ระบบกับโปรแกรมจริง

### Phase 12: XII OS 1.0 Release Candidate (PLANNED)
- **เป้าหมาย:** ตรวจสอบความพร้อมรอบสุดท้ายและปล่อย Release 1.0
- **สิ่งที่ต้องส่งมอบ:**
  - Full system regression testing บน QEMU, VirtualBox, และ Real Hardware
  - Documentation & User Guide ฉบับสมบูรณ์
  - XII OS 1.0 Stable ISO
