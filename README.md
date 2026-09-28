# XII OS — Beautiful. Lightweight. Intelligent.

XII OS เป็นระบบปฏิบัติการเดสก์ท็อปฐาน Linux สำหรับสถาปัตยกรรม x86-64 มุ่งเน้นความสวยงาม เรียบง่าย ทันสมัย น้ำหนักเบา และมีระบบ AI อัจฉริยะในตัว

---

## 🌟 จุดเด่นและปรัชญาของระบบ

- **Beautiful & Modern:** ดีไซน์ UI สะอาด มินิมอล มุมโค้งมน (rounded corners), แสงเงาและมิติที่ประณีต ไม่ลอกเลียนแบบใครตรงๆ พร้อมเอกลักษณ์ภาพลักษณ์เฉพาะตัวของ XII OS
- **Lightweight & Efficient:** ออกแบบมาให้กินทรัพยากรต่ำมาก รองรับตั้งแต่ฮาร์ดแวร์รุ่นเก่า แล็ปท็อปประหยัดพลังงาน ไปจนถึงเวิร์กสเตชันสมรรถนะสูง
- **3 Performance Modes:**
  - `XII Lite` — ปิดเอฟเฟกต์หนัก ลด transparency ลด background services ประหยัด RAM สำหรับคอมพิวเตอร์สเปกเริ่มต้น
  - `XII Standard` — โหมดสมดุลค่าเริ่มต้น สวยงาม นุ่มนวล ตอบสนองฉับไว
  - `XII Performance` — เปิด GPU acceleration เต็มรูปแบบ เอฟเฟกต์ภาพและแอนิเมชันเต็มระดับสำหรับเครื่องแรง
- **Multi-Packaging Support:** รองรับ `.deb`, Flatpak และ AppImage พร้อมระบบตรวจสอบความปลอดภัยดิจิทัล
- **Intelligent Assistant:** ติดตั้ง XII AI Assistant ที่ผสานเข้ากับระบบเดสก์ท็อป พร้อมมาตรการยืนยันสิทธิ์ความปลอดภัย (Least Privilege)
- **Standard Linux Foundation:** ใช้แกนระบบ Linux Kernel และ Drivers มาตรฐาน ไม่สร้างวงล้อใหม่ รักษาระบบให้เสถียรและเข้ากันได้กับฮาร์ดแวร์ x86-64 สูงสุด

---

## 🏛️ สถาปัตยกรรมระบบ (System Architecture)

```
┌────────────────────────────────────────────────────────┐
│                   XII Desktop Shell                    │
│   (Dock • Launcher • Window Manager • Search • Tray)   │
├────────────────────────────────────────────────────────┤
│                 XII Applications & AI                  │
│ (Files • Settings • Terminal • Store • AI Assistant)   │
├────────────────────────────────────────────────────────┤
│                  XII System Services                   │
│   (Mode Switcher • Security Daemon • Package Engine)   │
├────────────────────────────────────────────────────────┤
│                    Linux User Space                    │
│           (systemd • Wayland / PipeWire • D-Bus)       │
├────────────────────────────────────────────────────────┤
│                      Linux Kernel                      │
│                  (Drivers • Modules)                   │
├────────────────────────────────────────────────────────┤
│                 x86-64 Hardware / UEFI                 │
└────────────────────────────────────────────────────────┘
```

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```
xii-os/
├── build/                 # Build scripts, rootfs cache, ISO output
├── boot/                  # GRUB / EFI boot configurations & splash
├── kernel/                # Kernel configurations & sysctl tuning
├── system/                # XII Core System Services
│   ├── services/          # Base systemd services & init
│   ├── security/          # Security center daemons & permission policies
│   ├── updates/           # Update & rollback manager
│   └── power/             # Performance mode profiles (Lite/Standard/Perf)
├── desktop/               # Desktop Environment components
│   ├── shell/             # Desktop workspace & status bar
│   ├── dock/              # Smooth reactive app dock
│   ├── launcher/          # Minimal search-driven app launcher
│   ├── window-manager/    # Window compositor & layout management
│   ├── notifications/     # Glassmorphic notification center
│   └── search/            # Universal desktop search
├── applications/          # Built-in XII Applications
│   ├── files/             # XII Files (File manager)
│   ├── settings/          # XII Settings Center
│   ├── terminal/          # XII Terminal
│   ├── text/              # XII Text Editor
│   ├── calculator/        # XII Calculator
│   ├── image-viewer/      # XII Image Viewer
│   ├── media-player/      # XII Media Player
│   ├── system-monitor/    # XII System Monitor
│   ├── software-center/   # XII Store (App Store GUI)
│   └── security-center/   # XII Security Center GUI
├── package-manager/       # 'xii' CLI tool & package abstraction
├── installer/             # XII OS Live Installer
├── recovery/              # XII Recovery environment & snapshot rollback
├── ai/                    # XII AI Assistant & system permission gates
├── themes/                # XII Design system tokens, styles, colors
├── icons/                 # XII Icon pack
├── wallpapers/            # High-resolution minimalist wallpapers
├── documentation/         # Architecture, design specs & guides
├── tests/                 # Unit, integration & system tests
└── scripts/               # Automation scripts for build, run & test
```

---

## 🗺️ สถานะการพัฒนาตามลำดับ Phase (Development Phases)

| Phase | หัวข้อ | สถานะ | คำอธิบาย |
|---|---|---|---|
| **Phase 1** | **Bootable Linux base** | **✅ COMPLETE** | ฐาน Linux ขั้นต่ำ, initramfs, GRUB EFI/BIOS, Boot Mode Selector, QEMU Harness |
| **Phase 2** | XII Desktop | **✅ COMPLETE** | Desktop shell, theme engine, display server integration |
| **Phase 3** | Dock + Launcher + Window Management | **✅ COMPLETE** | ระบบจัดการหน้าต่าง, Dock อนิเมชันนุ่มนวล, Application Launcher |
| **Phase 4** | XII Files + XII Settings | **✅ COMPLETE** | ตัวจัดการไฟล์และศูนย์กลางการตั้งค่าระบบ |
| **Phase 5** | Network + Bluetooth + Audio + USB | **✅ COMPLETE** | การเชื่อมต่อฮาร์ดแวร์พื้นฐานทั้งหมด |
| **Phase 6** | XII Package Manager + XII Store | **✅ COMPLETE** | CLI `xii` และ GUI XII Store (.deb, Flatpak, AppImage) |
| **Phase 7** | Security Center | **✅ COMPLETE** | การตรวจสอบ permission, sandbox, firewall และ integrity |
| **Phase 8** | XII Update + Recovery | **✅ COMPLETE** | ระบบ Snapshot, Rollback, อัปเดตและกู้คืนระบบ |
| **Phase 9** | XII AI | **✅ COMPLETE** | AI Assistant ช่วยงานระบบ พร้อมกลไก Permission gate |
| **Phase 10** | Installer + ISO | **✅ COMPLETE** | ตัวติดตั้งกราฟิก Live USB / UEFI และเครื่องมือสร้าง ISO |
| **Phase 11** | Performance Optimization | **✅ COMPLETE** | ปรับแต่งความเร็ว CPU/RAM/I/O และเกณฑ์ทดสอบ Benchmark |
| **Phase 12** | XII OS 1.0 Release Candidate | **✅ COMPLETE** | ตรวจสอบความสมบูรณ์รอบสุดท้ายและปล่อยรุ่น Release 1.0 |
