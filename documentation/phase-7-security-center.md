# XII OS — Phase 7: Security Center Specification & Architecture

## 1. Overview

Phase 7 ส่งมอบระบบความปลอดภัยรอบด้าน (Comprehensive Security Architecture) สำหรับ XII OS:
- **CLI Security Daemon:** `xii-security` สำหรับสแกน ตรวจสอบ และเฝ้าระวังอัตโนมัติ
- **GUI Security Center:** `xii-security-center` (GTK4/Libadwaita) สำหรับผู้ใช้งานทั่วไป
- **Stateful Firewall:** `nftables.conf` นโยบาย Least Privilege สำหรับเครื่อง Workstation
- **Application Sandbox & MAC:** AppArmor profile สำหรับโปรแกรมเดสก์ท็อป
- **File Integrity Monitor:** SHA-256 baseline ตรวจจับการแก้ไขไฟล์ระบบที่ผิดปกติ
- **Permission & SetUID Audit:** ตรวจสอบสิทธิ์ไฟล์อ่อนไหวและสิทธิ์แปลกปลอม

---

## 2. Security Architecture

```
┌────────────────────────────────────────────────────────┐
│               XII Security Center (GUI)                │
│    Health Score • Firewall • Integrity • Sandboxing    │
└───────────────────────────▲────────────────────────────┘
                            │ D-Bus / Subprocess
┌───────────────────────────┴────────────────────────────┐
│              XII Security Daemon (CLI / Service)       │
│  xii-security scan • integrity • audit • firewall log  │
└───────▲───────────────▲────────────────▲───────────────┘
        │               │                │
┌───────┴───────┐┌──────┴────────┐┌──────┴────────┐
│ nftables / UFW││ AppArmor MAC  ││ SHA-256 Engine│
│ Least-Privilege││ Sandboxing    ││ Integrity Base│
└───────────────┘└───────────────┘└───────────────┘
```

---

## 3. Files Created

- `system/security/xii-security.py` — Security daemon and CLI scanner
- `system/security/xii-security.service` — systemd daemon unit
- `system/security/nftables.conf` — Least-privilege workstation firewall ruleset
- `system/security/apparmor/usr.bin.xii-apps` — AppArmor application sandbox policy
- `desktop/security/xii-security-center.py` — GTK4 Security Center application
- `desktop/security/xii-security-center.css` — Glassmorphic styling matching XII Design System
- `desktop/security/xii-security-center.desktop` — Desktop menu launcher entry
- `desktop/security/xii-security-center.service` — systemd user service
- `tests/test_security.py` — Automated test suite (pytest)

---

## 4. Verification Gate

- ✅ `pytest tests/test_security.py` ผ่าน 100%
- ✅ AST & Syntax validation ถูกต้องทุกไฟล์
- ✅ Threat score algorithm คำนวณถูกต้องตามเกณฑ์ความรุนแรง
- ✅ Firewall configuration ปฏิบัติตามมาตรฐาน Least-Privilege
