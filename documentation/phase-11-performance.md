# XII OS — Phase 11: Performance Optimization & Benchmarking Specification

## 1. Overview

Phase 11 มุ่งเน้นการปรับจูนประสิทธิภาพความเร็วขั้นสูงสุดและการตรวจสอบเทียบเกณฑ์ Service Level Agreement (SLA):
- **Boot Time SLA:** เวลาบูตระบบต้องต่ำกว่า 8.0 วินาทีบน NVMe/SSD
- **Memory Footprint SLA:** หน่วยความจำ Idle RAM ในโหมด `XII Lite` ต้องต่ำกว่า 350 MB
- **3-Tier Profiles (`profiles.json`):** กำหนดพารามิเตอร์ของ CPU Governor, Swappiness, ZRAM Ratio, และแอนิเมชันสำหรับทั้ง 3 โหมด (Lite / Standard / Performance)
- **Benchmarking Suite (`xii-bench.py`):** วิเคราะห์เวลาบูต, วัดการใช้ RAM, ทดสอบ Memory Bandwidth
- **Dynamic Optimizer (`xii-optimizer.py`):** ปรับจูน runtime sysctl และ CPU frequency แบบไดนามิกตามโหมดที่เลือก

---

## 2. Performance SLA Targets

| Metric | Target SLA | XII Lite | XII Standard | XII Performance |
|---|---|---|---|---|
| **Idle RAM** | < 350 MB (Lite) | **< 350 MB** | < 650 MB | Unlimited |
| **Boot Time** | < 8.0s | **< 6.5s** | < 7.5s | < 8.0s |
| **CPU Governor** | - | `powersave` | `schedutil` | `performance` |
| **Compositor Blur** | - | 0 passes (Disabled) | 3 passes (16px) | 4 passes (24px glow) |
| **Animations** | - | 150ms | 250ms | 300ms (Spring) |
| **ZRAM Ratio** | - | 0.5 | 0.3 | 0.2 |

---

## 3. Files Created

- `system/performance/profiles.json` — Profile specifications for Lite, Standard, and Performance
- `system/performance/xii-bench.py` — Benchmark & SLA validation tool
- `system/performance/xii-optimizer.py` — Dynamic kernel and CPU scheduler optimizer
- `tests/test_performance.py` — Test suite for Phase 11
