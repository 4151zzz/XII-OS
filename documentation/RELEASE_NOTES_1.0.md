# XII OS 1.0 (Genesis) — Official Release Notes

**Release Date:** September 28, 2026  
**Codename:** Genesis  
**Architecture:** x86-64 (UEFI + BIOS)  
**Kernel:** Linux 6.8.x LTS  

---

## 🚀 Highlights of XII OS 1.0

XII OS 1.0 (Genesis) เป็นการปล่อยรุ่นสมบูรณ์รุ่นแรกของระบบปฏิบัติการ XII OS ที่พัฒนาตาม Road map 12 เฟสอย่างครบถ้วน:

### 1. Modern Desktop Environment
- **Compositor:** Hyprland dynamic tiling & floating Wayland compositor
- **Design Tokens:** ชุดสีเฉพาะตัว (Deep space, Cyan `#6ee7f7`, Neon Purple `#a78bfa`), Glassmorphism blur, และ Spring physics animations
- **Status Shell:** Waybar status bar พร้อมแสดงผลโมดูลแบตเตอรี่, สถานะโหมด, เสียง PipeWire, เครือข่าย, และเวลา

### 2. Built-in Core Applications
- **XII Files:** ตัวจัดการไฟล์มินิมอล รองรับ Dark/Light mode, path breadcrumbs, file search
- **XII Settings:** หน้าต่างตั้งค่าแบบครบครัน (จอภาพ, ระบบเสียง, การเชื่อมต่อ, ธีม, เกี่ยวกับระบบ)
- **XII Dock & Launcher:** แถบ Dock อนิเมชันนุ่มนวล พร้อม Launcher สไตล์มินิมอลค้นหาทันที

### 3. Comprehensive Package Ecosystem
- **`xii` CLI:** คำสั่งเดียวจัดการได้ทั้ง `.deb`, Flatpak และ AppImage
- **XII Store:** แคตตาล็อกซอฟต์แวร์กราฟิก พร้อมแท็ก "XII Verified"

### 4. Advanced Security Architecture
- **nftables Least-Privilege Firewall:** ค่าเริ่มต้นปิดกั้นพอร์ตขาเข้า ปลอดภัยจากภายนอก
- **AppArmor Application Sandbox:** จำกัดขอบเขตการเข้าถึงไฟล์ระบบ
- **File Integrity Monitor:** ตรวจสอบ SHA-256 ป้องกันการดัดแปลงไฟล์ระบบ

### 5. Resilient Snapshots & Disaster Recovery
- **Btrfs Pre-update Snapshots:** สร้างจุดคืนค่าระบบอัตโนมัติก่อนอัปเดต
- **Emergency Recovery Console:** เมนูกู้คืนระบบผ่าน GRUB (ซ่อมบูต, กู้คืน snapshot, ตรวจเช็ก fsck)

### 6. Intelligent AI Assistant
- **Desktop HUD (`Super + A`):** วิดเจ็ตผู้ช่วยอัจฉริยะแบบลอยตัว
- **Least-Privilege Confirmation Gate:** บังคับขอสิทธิ์ยืนยันก่อนปฏิบัติการที่มีความเสี่ยงสูง

### 7. Performance & Optimization SLAs
- **Boot Time:** < 8.0 วินาทีบน SSD/NVMe
- **Idle RAM:** < 350 MB ในโหมด XII Lite
- **3 Dynamic Modes:** Lite, Standard, และ Performance สลับได้ทันที

---

## 📦 System Requirements

- **Processor:** 64-bit Dual-Core x86-64 (Intel Core i3 / AMD Ryzen 3 or newer)
- **Memory:** 2 GB RAM (XII Lite) | 4 GB+ (Recommended for XII Standard/Performance)
- **Storage:** 20 GB available disk space (SSD/NVMe recommended)
- **Graphics:** Intel HD Graphics, AMD Radeon, or NVIDIA (Nouveau/Proprietary)
