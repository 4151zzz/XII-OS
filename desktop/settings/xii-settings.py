#!/usr/bin/env python3
"""
XII OS — Settings Center (XII Settings)
desktop/settings/xii-settings.py

A comprehensive system settings application for XII OS.
Built on GTK4 + Adwaita (NavigationSplitView).

Settings Panels:
  01. Appearance      — Wallpaper, Dark mode, Accent color, Font
  02. Display         — Resolution, Refresh rate, Scale, Night light
  03. Sound           — Output/Input device, Volume, Equalizer
  04. Network         — Wi-Fi, Ethernet, VPN
  05. Bluetooth       — Paired devices, visibility
  06. Battery & Power — Power profiles, suspend, brightness
  07. XII Mode        — Performance Mode (Lite / Standard / Performance)
  08. Keyboard        — Layout, shortcuts, input method
  09. Mouse & Touchpad — Speed, gestures, natural scroll
  10. Users           — Accounts, avatar, password
  11. Privacy         — Location, camera, microphone
  12. About XII OS    — Version, updates, system info

Requirements:
  apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1

Usage:
  xii-settings [--panel <panel-id>]
"""

import gi
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Callable

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Adw, Gio, Gdk, GLib


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
APP_ID      = "org.xiios.Settings"
CSS_PATH    = "/usr/share/xii-os/desktop/settings/xii-settings.css"
XII_MODE_FILE = "/etc/xii-os/current-mode"
XII_MODES   = ["lite", "standard", "performance"]

PANELS = [
    ("appearance",  "Appearance",       "preferences-desktop-appearance-symbolic"),
    ("display",     "Display",          "video-display-symbolic"),
    ("sound",       "Sound",            "audio-speakers-symbolic"),
    ("network",     "Network",          "network-wireless-symbolic"),
    ("bluetooth",   "Bluetooth",        "bluetooth-symbolic"),
    ("battery",     "Battery & Power",  "battery-good-symbolic"),
    ("xii-mode",    "XII Mode",         "system-run-symbolic"),
    ("keyboard",    "Keyboard",         "input-keyboard-symbolic"),
    ("mouse",       "Mouse & Touchpad", "input-mouse-symbolic"),
    ("users",       "Users",            "system-users-symbolic"),
    ("privacy",     "Privacy",          "security-high-symbolic"),
    ("about",       "About XII OS",     "dialog-information-symbolic"),
]


# ─────────────────────────────────────────────────────────────
# Panel builders — each returns an Adw.PreferencesPage
# ─────────────────────────────────────────────────────────────

def _group(title: str, desc: str = "") -> Adw.PreferencesGroup:
    g = Adw.PreferencesGroup()
    g.set_title(title)
    if desc:
        g.set_description(desc)
    return g


def _switch_row(title: str, subtitle: str = "", value: bool = False) -> Adw.SwitchRow:
    row = Adw.SwitchRow()
    row.set_title(title)
    if subtitle:
        row.set_subtitle(subtitle)
    row.set_active(value)
    return row


def _combo_row(title: str, options: list[str], selected: int = 0) -> Adw.ComboRow:
    row = Adw.ComboRow()
    row.set_title(title)
    store = Gtk.StringList.new(options)
    row.set_model(store)
    row.set_selected(selected)
    return row


def _action_row(title: str, subtitle: str = "", suffix: Gtk.Widget = None) -> Adw.ActionRow:
    row = Adw.ActionRow()
    row.set_title(title)
    if subtitle:
        row.set_subtitle(subtitle)
    if suffix:
        row.add_suffix(suffix)
        row.set_activatable_widget(suffix)
    return row


def _spin_row(title: str, subtitle: str, min_v: float, max_v: float,
              step: float, value: float) -> Adw.SpinRow:
    row = Adw.SpinRow.new_with_range(min_v, max_v, step)
    row.set_title(title)
    if subtitle:
        row.set_subtitle(subtitle)
    row.set_value(value)
    return row


# ── Panel: Appearance ─────────────────────────────────────────
def build_appearance() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Appearance")
    page.set_icon_name("preferences-desktop-appearance-symbolic")

    # Wallpaper
    g1 = _group("Wallpaper")
    wallpaper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    wallpaper_box.set_margin_start(12)
    wallpaper_box.set_margin_end(12)
    wallpaper_box.set_margin_top(12)
    wallpaper_box.set_margin_bottom(12)

    preview = Gtk.Box()
    preview.set_css_classes(["wallpaper-preview"])
    preview.set_size_request(280, 158)
    wallpaper_box.append(preview)

    btn_choose = Gtk.Button(label="Choose Wallpaper…")
    btn_choose.set_css_classes(["suggested-action"])
    btn_choose.set_halign(Gtk.Align.CENTER)
    wallpaper_box.append(btn_choose)

    row_wallpaper = Adw.ActionRow()
    row_wallpaper.set_child(wallpaper_box)
    g1.add(row_wallpaper)
    page.add(g1)

    # Style
    g2 = _group("Style", "Choose how XII OS looks")
    g2.add(_combo_row("Color Scheme", ["Dark (XII OS)", "Light", "System Default"], 0))
    g2.add(_combo_row("Accent Color", ["Cyan (default)", "Purple", "Rose", "Green", "Orange"], 0))
    g2.add(_switch_row("Transparent Effects", "Glassmorphism (requires compositor)", True))
    g2.add(_switch_row("XII Animations", "Spring physics & micro-animations", True))
    page.add(g2)

    # Font
    g3 = _group("Typography")
    btn_font = Gtk.Button(label="Inter 14")
    g3.add(_action_row("System Font", "Used in all XII OS interfaces", btn_font))
    btn_mono = Gtk.Button(label="JetBrains Mono 13")
    g3.add(_action_row("Monospace Font", "Used in XII Terminal and code", btn_mono))
    page.add(g3)

    return page


# ── Panel: Display ────────────────────────────────────────────
def build_display() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Display")
    page.set_icon_name("video-display-symbolic")

    g1 = _group("Monitor", "Configure your displays")
    g1.add(_combo_row("Resolution",    ["3840 × 2160 (4K)", "2560 × 1440", "1920 × 1080"], 1))
    g1.add(_combo_row("Refresh Rate",  ["165 Hz", "144 Hz", "120 Hz", "60 Hz"], 0))
    g1.add(_combo_row("Scale",         ["100%", "125%", "150%", "200%"], 0))
    g1.add(_combo_row("Orientation",   ["Landscape", "Portrait", "Landscape (flipped)"], 0))
    page.add(g1)

    g2 = _group("Night Light", "Reduce blue light in the evening")
    g2.add(_switch_row("Enable Night Light", "Warms screen color after sunset", False))
    g2.add(_spin_row("Color Temperature", "Kelvin", 2500, 6500, 100, 4000))
    page.add(g2)

    g3 = _group("Power Saving")
    g3.add(_spin_row("Screen Blank Delay", "Minutes (0 = never)", 0, 60, 1, 5))
    g3.add(_switch_row("Automatic Brightness", "Adjust based on ambient sensor", False))
    page.add(g3)

    return page


# ── Panel: Sound ──────────────────────────────────────────────
def build_sound() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Sound")
    page.set_icon_name("audio-speakers-symbolic")

    g1 = _group("Output")
    g1.add(_combo_row("Output Device", ["Built-in Speakers", "HDMI Audio", "Bluetooth Headset"], 0))
    vol_row = Adw.ActionRow()
    vol_row.set_title("Volume")
    vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    vol_scale.set_value(70)
    vol_scale.set_hexpand(True)
    vol_scale.set_size_request(200, -1)
    vol_row.add_suffix(vol_scale)
    g1.add(vol_row)
    g1.add(_switch_row("Allow Overdrive", "Allow volume above 100%", False))
    page.add(g1)

    g2 = _group("Input")
    g2.add(_combo_row("Input Device",  ["Built-in Microphone", "USB Microphone", "Bluetooth"], 0))
    mic_row = Adw.ActionRow()
    mic_row.set_title("Input Level")
    mic_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    mic_scale.set_value(80)
    mic_scale.set_hexpand(True)
    mic_scale.set_size_request(200, -1)
    mic_row.add_suffix(mic_scale)
    g2.add(mic_row)
    page.add(g2)

    g3 = _group("System Sounds")
    g3.add(_switch_row("Event Sounds",    "Play sounds for system events", True))
    g3.add(_switch_row("Overamplification", "Allow louder volumes", False))
    page.add(g3)

    return page


# ── Panel: XII Mode ───────────────────────────────────────────
def build_xii_mode() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("XII Mode")
    page.set_icon_name("system-run-symbolic")

    # Read current mode
    try:
        current = Path(XII_MODE_FILE).read_text().strip()
    except FileNotFoundError:
        current = "standard"
    if current not in XII_MODES:
        current = "standard"

    g1 = _group("Performance Mode",
                "Select how XII OS balances performance and battery life.")

    modes = {
        "lite":        ("Lite Mode",        "Minimal RAM (< 200 MB), no effects, maximum battery.\nIdeal for older hardware or extreme battery saving."),
        "standard":    ("Standard Mode",    "Balanced performance and quality.\nXII glassmorphism effects, smooth animations."),
        "performance": ("Performance Mode", "Maximum CPU/GPU utilization.\nFull visual effects, 165 Hz refresh, enhanced glows."),
    }

    for mode_id, (label, desc) in modes.items():
        btn = Gtk.CheckButton()
        btn.set_active(mode_id == current)
        btn.set_css_classes(["selection-mode"])
        row = _action_row(label, desc, btn)
        row.set_css_classes([f"xii-mode-row-{mode_id}"])
        g1.add(row)

    page.add(g1)

    g2 = _group("Advanced")
    g2.add(_switch_row("Auto Mode Switching",
                       "Switch to Lite when on battery, Performance when plugged in", False))
    g2.add(_switch_row("Show Mode in Status Bar", "Display current mode in the top bar", True))
    page.add(g2)

    g3 = _group("Current Status")
    cpu_row = Adw.ActionRow()
    cpu_row.set_title("CPU Governor")
    cpu_label = Gtk.Label(label="schedutil")
    cpu_label.set_css_classes(["dim-label"])
    cpu_row.add_suffix(cpu_label)
    g3.add(cpu_row)

    zram_row = Adw.ActionRow()
    zram_row.set_title("ZRAM Compression")
    zram_label = Gtk.Label(label="lz4 / 4 GB")
    zram_label.set_css_classes(["dim-label"])
    zram_row.add_suffix(zram_label)
    g3.add(zram_row)

    page.add(g3)
    return page


# ── Panel: Keyboard ───────────────────────────────────────────
def build_keyboard() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Keyboard")
    page.set_icon_name("input-keyboard-symbolic")

    g1 = _group("Keyboard Layout")
    g1.add(_combo_row("Layout",    ["English (US)", "Thai (Kedmanee)", "Thai (Pattachote)"], 0))
    g1.add(_combo_row("Variant",   ["Default", "International"], 0))
    g1.add(_switch_row("Caps Lock → Escape", "Remap Caps Lock key to Escape", True))
    page.add(g1)

    g2 = _group("Typing")
    g2.add(_spin_row("Key Repeat Delay",  "Milliseconds before key starts repeating", 100, 1000, 50, 300))
    g2.add(_spin_row("Key Repeat Rate",   "Repetitions per second", 5, 50, 1, 30))
    page.add(g2)

    g3 = _group("XII Keyboard Shortcuts",
                "View and customize XII OS keyboard shortcuts")
    row_shortcuts = Adw.ActionRow()
    row_shortcuts.set_title("Customize Shortcuts")
    row_shortcuts.set_subtitle("Open keyboard shortcut editor")
    row_shortcuts.set_activatable(True)
    row_shortcuts.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
    g3.add(row_shortcuts)
    page.add(g3)

    return page


# ── Panel: Battery & Power ────────────────────────────────────
def build_battery() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Battery & Power")
    page.set_icon_name("battery-good-symbolic")

    g1 = _group("Battery")
    batt_row = Adw.ActionRow()
    batt_row.set_title("Battery Health")
    batt_label = Gtk.Label(label="87%  (Cycle count: 124)")
    batt_label.set_css_classes(["dim-label"])
    batt_row.add_suffix(batt_label)
    g1.add(batt_row)
    g1.add(_switch_row("Battery Percentage in Status Bar", "", True))
    g1.add(_switch_row("Show Battery Time Remaining",     "", True))
    page.add(g1)

    g2 = _group("Power Saving")
    g2.add(_spin_row("Suspend After",       "Minutes of inactivity (0 = never)", 0, 120, 5, 15))
    g2.add(_spin_row("Screen Off After",    "Minutes", 0, 60, 1, 5))
    g2.add(_switch_row("Power Button Action is Suspend", "", True))
    page.add(g2)

    g3 = _group("Charging")
    g3.add(_switch_row("Charge Limit",
                       "Stop charging at 80% to extend battery lifespan", False))
    page.add(g3)

    return page


# ── Panel: About ──────────────────────────────────────────────
def build_about() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("About XII OS")
    page.set_icon_name("dialog-information-symbolic")

    # Logo + name
    hero_group = Adw.PreferencesGroup()
    hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    hero_box.set_halign(Gtk.Align.CENTER)
    hero_box.set_margin_top(24)
    hero_box.set_margin_bottom(16)

    logo = Gtk.Image.new_from_icon_name("preferences-system-symbolic")
    logo.set_pixel_size(96)
    logo.set_css_classes(["about-logo"])
    hero_box.append(logo)

    name_label = Gtk.Label(label="XII OS")
    name_label.set_css_classes(["about-name"])
    hero_box.append(name_label)

    version_label = Gtk.Label(label="Version 1.0 “Genesis”")
    version_label.set_css_classes(["about-version", "dim-label"])
    hero_box.append(version_label)

    hero_row = Adw.ActionRow()
    hero_row.set_child(hero_box)
    hero_group.add(hero_row)
    page.add(hero_group)

    # System info
    g1 = _group("System Information")
    infos = [
        ("Operating System",  "XII OS 1.0 (Genesis)"),
        ("Kernel",            subprocess.getoutput("uname -r") or "Linux 6.x"),
        ("Desktop",           "XII Desktop (Hyprland 0.44)"),
        ("Architecture",      subprocess.getoutput("uname -m") or "x86_64"),
        ("Memory",            _get_memory_info()),
        ("Storage",           _get_storage_info()),
    ]
    for label, value in infos:
        row = Adw.ActionRow()
        row.set_title(label)
        val_lbl = Gtk.Label(label=value)
        val_lbl.set_css_classes(["dim-label"])
        row.add_suffix(val_lbl)
        g1.add(row)
    page.add(g1)

    # Updates
    g2 = _group("Software")
    btn_update = Gtk.Button(label="Check for Updates")
    btn_update.set_css_classes(["suggested-action"])
    btn_update.set_valign(Gtk.Align.CENTER)
    g2.add(_action_row("XII OS Updates", "Last checked: Today", btn_update))
    page.add(g2)

    return page


def _get_memory_info() -> str:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return f"{kb // 1024 // 1024} GB RAM"
    except Exception:
        pass
    return "N/A"


def _get_storage_info() -> str:
    try:
        result = subprocess.getoutput("df -h / | tail -1")
        parts = result.split()
        return f"{parts[1]} total, {parts[3]} free"
    except Exception:
        return "N/A"


# ── Panel: Network ────────────────────────────────────────────
def build_network() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Network")
    page.set_icon_name("network-wireless-symbolic")

    g1 = _group("Wi-Fi")
    g1.add(_switch_row("Wi-Fi", "Enable wireless networking", True))
    for ssid, signal in [("XII-Home-5G", "Excellent"), ("Office-WiFi", "Good"), ("Guest", "Fair")]:
        row = Adw.ActionRow()
        row.set_title(ssid)
        row.set_subtitle(f"Signal: {signal}")
        row.set_activatable(True)
        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        g1.add(row)
    page.add(g1)

    g2 = _group("Ethernet")
    g2.add(_switch_row("Wired Connection", "eth0 (1Gbps)", False))
    page.add(g2)

    g3 = _group("VPN")
    g3.add(_action_row("Add VPN Connection…", "WireGuard, OpenVPN"))
    page.add(g3)

    return page


# ── Panel: Bluetooth ─────────────────────────────────────────
def build_bluetooth() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Bluetooth")
    page.set_icon_name("bluetooth-symbolic")

    g1 = _group("Bluetooth")
    g1.add(_switch_row("Bluetooth",  "Enable Bluetooth", True))
    g1.add(_switch_row("Discoverable", "Allow other devices to find this device", False))
    page.add(g1)

    g2 = _group("Paired Devices")
    for name, type_ in [("AirPods Pro", "Headphones"), ("Magic Mouse", "Mouse")]:
        row = Adw.ActionRow()
        row.set_title(name)
        row.set_subtitle(type_)
        row.set_activatable(True)
        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        g2.add(row)
    page.add(g2)

    return page


# ── Panel: Mouse & Touchpad ───────────────────────────────────
def build_mouse() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Mouse & Touchpad")
    page.set_icon_name("input-mouse-symbolic")

    g1 = _group("Mouse")
    g1.add(_spin_row("Pointer Speed", "Sensitivity", -1.0, 1.0, 0.1, 0.0))
    g1.add(_switch_row("Natural Scrolling", "Scroll direction follows finger movement", False))
    g1.add(_combo_row("Acceleration Profile", ["Flat (XII default)", "Adaptive"], 0))
    page.add(g1)

    g2 = _group("Touchpad")
    g2.add(_switch_row("Touchpad",            "Enable touchpad input", True))
    g2.add(_switch_row("Natural Scrolling",   "Two-finger scroll follows finger direction", True))
    g2.add(_switch_row("Tap to Click",        "Tap touchpad surface to click", True))
    g2.add(_switch_row("Two-finger Tap",      "Two-finger tap as right click", True))
    g2.add(_switch_row("Disable While Typing","Prevent accidental input while typing", True))
    g2.add(_spin_row("Scroll Speed", "Multiplier", 0.1, 3.0, 0.1, 0.8))
    page.add(g2)

    return page


# ── Panel: Users ──────────────────────────────────────────────
def build_users() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Users")
    page.set_icon_name("system-users-symbolic")

    g1 = _group("Current User")
    avatar_row = Adw.ActionRow()
    avatar_row.set_title(os.environ.get("USER", "xii-user"))
    avatar_row.set_subtitle("Administrator")
    btn_avatar = Gtk.Button(label="Change Photo")
    btn_avatar.set_valign(Gtk.Align.CENTER)
    avatar_row.add_suffix(btn_avatar)
    g1.add(avatar_row)

    btn_pw = Gtk.Button(label="Change")
    btn_pw.set_valign(Gtk.Align.CENTER)
    g1.add(_action_row("Password", "Last changed: never", btn_pw))
    page.add(g1)

    g2 = _group("Login")
    g2.add(_switch_row("Automatic Login",  "Sign in without password at startup", False))
    g2.add(_switch_row("Lock Screen",      "Require password after screen blank", True))
    page.add(g2)

    return page


# ── Panel: Privacy ────────────────────────────────────────────
def build_privacy() -> Adw.PreferencesPage:
    page = Adw.PreferencesPage()
    page.set_title("Privacy")
    page.set_icon_name("security-high-symbolic")

    g1 = _group("Permissions")
    g1.add(_switch_row("Location Services",  "Allow apps to access your location", False))
    g1.add(_switch_row("Camera Access",      "Allow apps to use the camera", True))
    g1.add(_switch_row("Microphone Access",  "Allow apps to use the microphone", True))
    page.add(g1)

    g2 = _group("Activity & History")
    g2.add(_switch_row("Recent Files",       "Keep a log of recently opened files", True))
    g2.add(_switch_row("Crash Reports",      "Send anonymous crash data to XII OS team", False))
    page.add(g2)

    g3 = _group("Security")
    g3.add(_switch_row("Firewall",           "Block unauthorized inbound connections", True))
    g3.add(_switch_row("Automatic Updates",  "Keep XII OS up to date automatically", True))
    page.add(g3)

    return page


# ─────────────────────────────────────────────────────────────
# Panel registry
# ─────────────────────────────────────────────────────────────
PANEL_BUILDERS: dict[str, Callable] = {
    "appearance": build_appearance,
    "display":    build_display,
    "sound":      build_sound,
    "network":    build_network,
    "bluetooth":  build_bluetooth,
    "battery":    build_battery,
    "xii-mode":   build_xii_mode,
    "keyboard":   build_keyboard,
    "mouse":      build_mouse,
    "users":      build_users,
    "privacy":    build_privacy,
    "about":      build_about,
}


# ─────────────────────────────────────────────────────────────
# Settings Window
# ─────────────────────────────────────────────────────────────
class SettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, initial_panel: str = "appearance"):
        super().__init__(application=app)
        self.set_title("XII Settings")
        self.set_default_size(950, 660)
        self.set_css_classes(["settings-window"])
        self._build_ui(initial_panel)

    def _build_ui(self, initial_panel: str):
        # NavigationSplitView: sidebar + content
        split = Adw.NavigationSplitView()
        split.set_min_sidebar_width(220)
        split.set_max_sidebar_width(260)

        # ── Sidebar ────────────────────────────────────────────
        sidebar_nav = Adw.NavigationPage()
        sidebar_nav.set_title("XII Settings")

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_css_classes(["settings-sidebar-header"])
        sidebar_header.set_show_end_title_buttons(False)

        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search settings…")
        search_entry.set_hexpand(True)
        search_entry.set_css_classes(["settings-search"])
        sidebar_header.set_title_widget(search_entry)
        sidebar_box.append(sidebar_header)

        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_vexpand(True)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_css_classes(["settings-sidebar-list", "navigation-sidebar"])
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.connect("row-selected", self._on_panel_selected)

        self.panel_rows: dict[str, Gtk.ListBoxRow] = {}
        for panel_id, label, icon in PANELS:
            row = Gtk.ListBoxRow()
            row._panel_id = panel_id

            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            inner.set_margin_start(12)
            inner.set_margin_end(12)
            inner.set_margin_top(8)
            inner.set_margin_bottom(8)

            icon_widget = Gtk.Image.new_from_icon_name(icon)
            icon_widget.set_pixel_size(20)
            icon_widget.set_css_classes(["settings-sidebar-icon"])
            inner.append(icon_widget)

            lbl = Gtk.Label(label=label)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_css_classes(["settings-sidebar-label"])
            inner.append(lbl)

            row.set_child(inner)
            self.sidebar_list.append(row)
            self.panel_rows[panel_id] = row

        sidebar_scroll.set_child(self.sidebar_list)
        sidebar_box.append(sidebar_scroll)
        sidebar_nav.set_child(sidebar_box)
        split.set_sidebar(sidebar_nav)

        # ── Content ────────────────────────────────────────────
        self.content_nav = Adw.NavigationPage()
        self.content_nav.set_title("Settings")

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        content_header = Adw.HeaderBar()
        content_header.set_css_classes(["settings-content-header"])
        content_box.append(content_header)

        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content_scroll.set_vexpand(True)

        self.content_view = Adw.Clamp()
        self.content_view.set_maximum_size(720)
        self.content_view.set_margin_start(16)
        self.content_view.set_margin_end(16)
        self.content_view.set_margin_top(8)
        self.content_view.set_margin_bottom(24)

        self.content_scroll.set_child(self.content_view)
        content_box.append(self.content_scroll)

        self.content_nav.set_child(content_box)
        split.set_content(self.content_nav)

        self.set_content(split)

        # Select initial panel
        if initial_panel in self.panel_rows:
            self.sidebar_list.select_row(self.panel_rows[initial_panel])
        else:
            first = self.sidebar_list.get_row_at_index(0)
            if first:
                self.sidebar_list.select_row(first)

    def _on_panel_selected(self, list_box, row):
        if row is None:
            return
        panel_id = getattr(row, "_panel_id", None)
        if not panel_id:
            return

        builder = PANEL_BUILDERS.get(panel_id)
        if builder:
            page = builder()
            self.content_view.set_child(page)
            # Update content header title
            label = next((l for pid, l, _ in PANELS if pid == panel_id), "Settings")
            self.content_nav.set_title(label)


# ─────────────────────────────────────────────────────────────
# XII Settings Application
# ─────────────────────────────────────────────────────────────
class XIISettingsApp(Adw.Application):
    def __init__(self, panel: str = "appearance"):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.initial_panel = panel
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self._apply_css()
        win = SettingsWindow(self, self.initial_panel)
        win.present()

    def _apply_css(self):
        css_path = Path(CSS_PATH)
        if not css_path.exists():
            css_path = Path(__file__).parent / "xii-settings.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )


def main():
    parser = argparse.ArgumentParser(description="XII OS Settings Center")
    parser.add_argument("--panel", default="appearance",
                        choices=[p[0] for p in PANELS],
                        help="Open directly to a specific settings panel")
    args, _ = parser.parse_known_args()

    app = XIISettingsApp(panel=args.panel)
    sys.exit(app.run(sys.argv[:1]))


if __name__ == "__main__":
    main()
