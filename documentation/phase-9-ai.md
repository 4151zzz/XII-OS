# XII OS — Phase 9: XII AI Assistant Specification

## 1. Overview

Phase 9 พัฒนาระบบผู้ช่วยอัจฉริยะประจำระบบปฏิบัติการ (XII AI Assistant):
- **Core AI Engine (`xii-ai-core.py`):** ประมวลผลคำสั่งภาษาธรรมชาติ ตรวจวินิจฉัยฮาร์ดแวร์/ซอฟต์แวร์
- **Permission Gate (Least Privilege Architecture):** กลไกบังคับขอคำยืนยันจากผู้ใช้ก่อนสั่งการที่มีผลกระทบรุนแรง (High Impact Actions เช่น ติดตั้งแพ็กเกจ, ลบไฟล์, คำสั่ง root)
- **Floating Spotlight HUD (`xii-ai-assistant`):** วิดเจ็ตลอยตัวเปิดด้วยคีย์ลัด `Super + A`
- **Intents Catalog (`xii-ai-intents.json`):** โครงร่างเจตนาคำสั่งทั้งภาษาไทยและอังกฤษ

---

## 2. Permission Gate Flow

```
User Query: "ติดตั้งโปรแกรม blender"
                  │
                  ▼
         [ Intent Matcher ] ──► Matches "install_application"
                  │
                  ▼
        [ Impact Evaluation ]
         Is Impact >= High? ──► YES
                  │
                  ▼
         [ Permission Gate ]
                  │
                  ├──► Render Warning Prompt with Action Token
                  │
                  ▼
          User Clicks "Approve"?
            ├── NO  ──► Abort & Log "User Cancelled"
            └── YES ──► Elevate Privileges & Execute
```

---

## 3. Files Created

- `system/ai/xii-ai-core.py` — Assistant backend and diagnostic engine
- `system/ai/xii-ai-intents.json` — System intent patterns and permissions
- `system/ai/xii-ai.service` — systemd user unit for daemon
- `desktop/ai/xii-ai-assistant.py` — GTK4 Floating Spotlight HUD
- `desktop/ai/xii-ai-assistant.css` — Modern glassmorphism styling
- `desktop/ai/xii-ai-assistant.desktop` — Application shortcut
- `tests/test_ai_assistant.py` — Test suite for AI & Permission Gate
