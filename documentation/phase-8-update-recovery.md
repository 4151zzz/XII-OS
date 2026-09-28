# XII OS — Phase 8: XII Update & Recovery Specification

## 1. Overview

Phase 8 พัฒนาระบบอัปเดตอัตโนมัติที่ปลอดภัยและระบบกู้คืนเมื่อเกิดเหตุฉุกเฉิน (Resilient Update & Disaster Recovery System):
- **XII Snapshot Engine (`xii-snapshot`):** สร้าง snapshot ก่อนอัปเดต รองรับทั้ง Btrfs subvolumes และ local differential storage
- **XII Update Engine (`xii-update`):** ตรวจสอบและอัปเดตแพ็กเกจ (APT, Flatpak, XII Core) พร้อมคัดกรองเฉพาะ Security Updates
- **XII Updater UI (`xii-updater`):** GUI (GTK4/Libadwaita) สำหรับตรวจสอบและกดอัปเดต 1-click และหน้าจัดการจุดคืนค่าระบบ
- **XII Recovery Console (`xii-recovery.sh`):** สภาพแวดล้อมกู้คืนฉุกเฉินผ่าน GRUB Recovery Mode สำหรับ rollback, ซ่อมแซมไฟล์ระบบ, กู้คืน bootloader, รีเซ็ตรหัสผ่าน

---

## 2. Architecture & Rollback Workflow

```
                        [ User / Schedule ]
                                 │
                                 ▼
                     ┌──────────────────────┐
                     │     xii-update       │
                     └──────────┬───────────┘
                                │
                   1. Trigger automatic snapshot
                                │
                                ▼
                     ┌──────────────────────┐
                     │    xii-snapshot      │ ──► Creates /.snapshots/snap_YYYYMMDD
                     └──────────┬───────────┘
                                │
                   2. Apply packages / upgrades
                                │
                                ▼
                   ┌────────────────────────┐
                   │ apt-get / flatpak update│
                   └────────────┬───────────┘
                                │
               Success? ────────┴──────── Error?
                  │                         │
                  ▼                         ▼
            [ Boot Normal ]       [ GRUB Recovery Mode ]
                                            │
                                            ▼
                                   [ xii-recovery.sh ]
                                  (1-Click Rollback)
```

---

## 3. Files Created

- `system/updates/xii-snapshot.py` — Snapshot and rollback manager
- `system/updates/xii-update.py` — Update orchestration engine
- `system/updates/xii-update.service` — systemd unit for automated checks
- `system/updates/xii-update.timer` — systemd daily timer
- `system/recovery/xii-recovery.sh` — Interactive emergency recovery tool
- `desktop/updates/xii-updater.py` — GTK4 visual updater application
- `desktop/updates/xii-updater.css` — Glassmorphic styling
- `desktop/updates/xii-updater.desktop` — Desktop launcher shortcut
- `tests/test_update_recovery.py` — Automated test suite
