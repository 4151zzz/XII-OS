# XII OS — System Architecture Specification

## 1. High-Level Vision

XII OS ถูกออกแบบภายใต้หลักการ 3 ประการ:
1. **Beautiful:** สุนทรียภาพทางสายตาที่ประณีต เรียบหรู ไม่ซ้ำทางใคร มีเอกลักษณ์ของตนเอง
2. **Lightweight:** ควบคุมการใช้ทรัพยากรตั้งแต่ระดับ kernel boot parameters ไปจนถึง UI compositor ให้กิน RAM และ CPU น้อยที่สุด
3. **Intelligent:** ผสาน AI Assistant เข้ากับ Core OS เพื่อช่วยเหลือผู้ใช้ โดยอยู่ภายใต้โมเดลความปลอดภัย **Least Privilege & Explicit Confirmation**

---

## 2. Layered Architecture

```
+-------------------------------------------------------------------------+
|                          XII Desktop Shell                              |
|  - Wayland Compositor / XII Compositor Protocol                         |
|  - XII Dock (Adaptive Magnification & App State)                        |
|  - XII App Launcher (Categorized, Quick Launch, Universal Search)        |
|  - XII Window Manager (Snapping, Floating, Workspaces)                  |
|  - XII Notification & Quick Settings Center (Volume, Wi-Fi, BT, Power)  |
+-------------------------------------------------------------------------+
|                        XII Applications Layer                           |
|  - XII Files        - XII Settings       - XII Terminal                 |
|  - XII Text         - XII Calculator     - XII Image Viewer             |
|  - XII Media Player - XII System Monitor - XII Software Center          |
|  - XII Security Center                   - XII AI Assistant             |
+-------------------------------------------------------------------------+
|                     XII Core System Services (D-Bus)                    |
|  - org.xiios.ModeManager       (Lite / Standard / Performance)          |
|  - org.xiios.SecurityDaemon    (Sandbox, Permission Gate, App Verifier) |
|  - org.xiios.PackageManager    (apt / Flatpak / AppImage unified API)   |
|  - org.xiios.UpdateManager     (Atomic Snapshot & Rollback)             |
|  - org.xiios.AiDaemon          (Local NLP, Safe Command Broker)         |
+-------------------------------------------------------------------------+
|                     Linux User Space Infrastructure                     |
|  - systemd (init, journald, logind, udev)                               |
|  - PipeWire & WirePlumber (Modern Low-Latency Audio/Video)              |
|  - NetworkManager & BlueZ (Network & Bluetooth)                         |
|  - Mesa / DRM / KMS (Direct Rendering & Hardware Acceleration)          |
|  - PAM & Polkit (Authentication & Privilege Separation)                 |
+-------------------------------------------------------------------------+
|                       Linux Kernel & Drivers                            |
|  - Long-Term Support (LTS) 6.x+ x86-64 Kernel                           |
|  - ZRAM Swap with zstd compression enabled                              |
|  - Memory-optimized sysctl parameters                                   |
|  - Broad hardware driver modules (GPU, Wi-Fi, NVMe, Audio, Touchpad)    |
+-------------------------------------------------------------------------+
|                       Hardware & Firmware Layer                         |
|  - UEFI 64-bit & Legacy BIOS Compatibility                              |
|  - ACPI Power Management & Battery Optimization                         |
+-------------------------------------------------------------------------+
```

---

## 3. Performance Mode Engine (`org.xiios.ModeManager`)

XII OS รองรับ 3 โหมดการทำงานที่ปรับเปลี่ยนได้ทันที:

| Parameter | XII Lite | XII Standard (Default) | XII Performance |
|---|---|---|---|
| **Target Hardware** | RAM < 4GB, CPU เก่า/2 cores | RAM 4GB - 16GB, ทั่วไป | RAM > 16GB, GPU แยก, เกม/งานหนัก |
| **Compositor Effects** | Blur ปิด, Transparency ต่ำ, No shadows | Blur อ่อน, Subtle shadows, 60fps | High-quality blur, Dynamic physics, 144Hz+ |
| **ZRAM Compression** | สูงสุด (zstd, 50% RAM pool) | ปานกลาง (zstd, 25% RAM pool) | ต่ำ / ปิด ZRAM ใช้ Physical RAM |
| **CPU Governor** | `powersave` หรือ `conservative` | `schedutil` (Dynamic balance) | `performance` |
| **Background Services**| ระงับ indexer & animations | ทำงานตามมาตรฐาน | ทำงานเต็มประสิทธิภาพ |
| **Target Idle RAM** | **~280 MB - 380 MB** | **~500 MB - 650 MB** | **~800 MB - 1 GB** |

---

## 4. Security & Isolation Architecture

1. **Principle of Least Privilege (PoLP):** ห้ามไม่ให้แอพพลิเคชันและ XII AI Assistant รันเป็น root โดยตรงเด็ดขาด ทุกการกระทำที่แตะต้องระดับระบบต้องผ่าน Polkit และ Prompt แสดงรายละเอียด
2. **App Verification & Safety Gate:** เมื่อผู้ใช้เปิดไฟล์ `.deb`, Flatpak หรือ AppImage จากภายนอก ระบบจะตรวจสอบ:
   - Checksum & Digital Signature
   - รายการ Permissions ที่ขอ (Network, Filesystem, Root, Device access)
   - แหล่งที่มา (Repository ที่รู้จัก vs เว็บไซต์ภายนอก)
   - แจ้งเตือนความเสี่ยงอย่างโปร่งใส ให้ผู้ใช้เป็นผู้มีอำนาจตัดสินใจ
3. **Sandboxing:** แอพพลิเคชันที่รองรับ Flatpak จะถูกกักกันด้วย Bubblewrap Sandbox แยก Filesystem และ IPC ออกจากกัน

---

## 5. Technology Stack Decisions

- **Base Distribution:** Debian Minimal (Stable LTS) — ให้ความเสถียรสูงสุด, มี repository ขนาดใหญ่ที่สุด, อัปเดตความปลอดภัยต่อเนื่องยาวนาน และรองรับ `.deb` แท้
- **Init System:** `systemd` — มาตรฐานอุตสาหกรรม จัดการ services, udev, cgroups, timer และ power management
- **Display Protocol:** Wayland (ผ่าน wlroots/weston หรือ Mutter-based custom compositor) พร้อม XWayland fallback
- **Audio Subsystem:** PipeWire + WirePlumber — ตัดปัญหา PulseAudio vs ALSA เข้ากันได้กับฮาร์ดแวร์ยุคใหม่
- **Package Management:** Native `dpkg`/`apt` + `flatpak` + AppImage integration ผ่าน `xii-pkg`
- **Application Framework:** Lightweight native UI (GTK4 / Libadwaita พร้อม custom XII CSS theme หรือ Web-native responsive viewports)
