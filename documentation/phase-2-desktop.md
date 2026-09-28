# XII OS — Phase 2 Desktop: Specification & Plan

## 1. Phase Overview

Phase 2 มุ่งเน้นการสร้าง **XII Desktop Environment** — สภาพแวดล้อมเดสก์ท็อปที่สวยงาม รวดเร็ว และบูตได้ (เป็น Wayland session) บนฐาน Phase 1

> **Compositor เลือก: Hyprland** — Dynamic tiling Wayland compositor บน wlroots ที่มีระบบ animation และ plugin ที่ยืดหยุ่นสูง พร้อม community ที่แข็งแรง

---

## 2. Phase 2 Architecture

```
+-------------------------------------------------------------+
|                    XII Desktop Session                      |
|                                                             |
|  ┌──────────────────────────────────────────────────────┐  |
|  │              XII Status Bar (Waybar)                  │  |
|  │  [XII OS logo] [Workspaces] [Title] | Clock | Tray   │  |
|  └──────────────────────────────────────────────────────┘  |
|                                                             |
|  ┌──────────────────────────────────────────────────────┐  |
|  │           XII Wayland Desktop Area                    │  |
|  │  (Hyprland Compositor: Tiling + Floating windows)    │  |
|  │                                                       │  |
|  │   Windows → Rounded corners + Cyan border glow       │  |
|  │   Backgrounds → Glassmorphic blur through panels     │  |
|  │   Animations → Spring physics (xii_spring bezier)   │  |
|  └──────────────────────────────────────────────────────┘  |
|                                                             |
|  ┌──────────────────────────────────────────────────────┐  |
|  │              XII Dock (Phase 3)                       │  |
|  └──────────────────────────────────────────────────────┘  |
+-------------------------------------------------------------+
|              XII Core System Services (D-Bus)               |
|              xii-init  •  xii-mode  •  pipewire             |
+-------------------------------------------------------------+
|                    Linux Kernel 6.x                         |
+-------------------------------------------------------------+
```

---

## 3. Files Created in Phase 2

### Design System (`themes/`)
| ไฟล์ | คำอธิบาย |
|---|---|
| `tokens.json` | Design tokens ครบ: สี, typography, spacing, radius, shadow, animation |
| `xii-global.css` | CSS custom properties + 3 Mode variants (Lite/Standard/Performance) |
| `xii-glassmorphism.css` | Glassmorphism utilities: panel, card, floating, notification, tooltip |
| `xii-gtk4.css` | GTK4/Libadwaita theme override: window, buttons, entries, menus, switches |

### Window Manager (`desktop/window-manager/`)
| ไฟล์ | คำอธิบาย |
|---|---|
| `hyprland.conf` | Hyprland compositor: rounded corners (14px), cyan border glow, spring animations, workspace rules, XII keybindings |

### Status Bar (`desktop/shell/`)
| ไฟล์ | คำอธิบาย |
|---|---|
| `waybar/config.jsonc` | Waybar config: XII logo, workspaces, clock, mode indicator, audio/network/BT/battery, tray |
| `waybar/style.css` | Waybar stylesheet: glassmorphic bar, gradient logo, animated battery, cyan workspace highlight |
| `xii-statusbar.service` | systemd user service for Waybar |

### Wallpapers (`wallpapers/`)
| ไฟล์ | คำอธิบาย |
|---|---|
| `xii-default.svg` | 4K SVG wallpaper: deep space + nebula glows + XII hexagon logo + starfield |
| `generate-wallpaper.py` | Generator: SVG → PNG/JPEG ทุก resolution (FHD/QHD/4K/ultrawide/laptop) |

---

## 4. XII Design System — Color Palette

| Token | Value | Role |
|---|---|---|
| `--xii-bg-deep` | `hsl(240, 15%, 4%)` | Deepest background |
| `--xii-bg-base` | `hsl(240, 12%, 7%)` | Primary surface |
| `--xii-bg-elevated` | `hsl(240, 10%, 11%)` | Cards, panels |
| `--xii-cyan` | `hsl(190, 90%, 70%)` | Primary accent |
| `--xii-purple` | `hsl(260, 80%, 72%)` | Identity color |
| `--xii-rose` | `hsl(330, 75%, 68%)` | Tertiary accent |
| `--xii-text-primary` | `hsl(240, 10%, 92%)` | Main text |
| `--xii-text-muted` | `hsl(240, 6%, 45%)` | Dimmed text |

### Performance Mode — Design Adaptations

| Property | XII Lite | XII Standard | XII Performance |
|---|---|---|---|
| Backdrop blur | 4px | 16px | 24px |
| Shadow depth | Disabled | Medium | Heavy + glow |
| Animation duration | 150ms | 250ms | 300ms |
| Dock icon size | 48px | 52px | 60px |
| Glassmorphism fill | 4% white | 6% white | 6% white + vibrancy |

---

## 5. Hyprland Visual Configuration Summary

```ini
# Rounded corners
decoration.rounding = 14

# XII Cyan ↔ Purple gradient border (animated)
col.active_border   = rgba(6ee7f7ff) rgba(a78bfaff) 45deg
col.inactive_border = rgba(1a1a2e80)

# Glassmorphism blur
blur.size   = 12
blur.passes = 3

# Spring animation
bezier = xii_spring, 0.175, 0.885, 0.32, 1.275
animation = windows, 1, 5, xii_spring
```

---

## 6. Key XII Keybindings

| Key | Action |
|---|---|
| `Super + Space` | XII Launcher |
| `Super + Enter` | XII Terminal |
| `Super + E` | XII Files |
| `Super + ,` | XII Settings |
| `Super + A` | XII AI Assistant |
| `Super + Q` | Close window |
| `Super + F` | Fullscreen |
| `Super + V` | Toggle floating |
| `Super + 1–0` | Switch workspace |
| `Super + Ctrl + 1/2/3` | XII Mode: Lite / Standard / Performance |
| `Print` | Screenshot |

---

## 7. Verification Gate

- ✅ `pytest tests/` ผ่าน 100% (Phase 2 tests)
- ✅ Design tokens ครบ 50+ tokens
- ✅ CSS variables map กับ tokens ทุกตัว
- ✅ GTK4 theme override ครบ widgets หลัก
- ✅ Hyprland config: rounded corners, animations, keybindings ครบ
- ✅ Waybar: Left/Center/Right modules พร้อม click actions
- ✅ Wallpaper SVG 4K + generator script
- ⏳ Visual testing: ต้อง boot XII Desktop บน QEMU (Phase 1 ISO)
- ⏳ Font installation: Inter + JetBrains Mono via `bootstrap-base.sh`
