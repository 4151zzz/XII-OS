#!/usr/bin/env python3
"""
XII OS — Reactive Dock Daemon
desktop/dock/xii-dock.py

A glassmorphic, magnification-reactive application dock for XII OS.
Built on GTK4 + Wayland (gtk4-layer-shell).

Features:
  - Magnification on hover (macOS-style spring physics)
  - Running app indicators (active dot)
  - Window grouping with popover on click
  - Notification badge overlay
  - Smooth show/hide animation
  - Performance mode adaptation (icon size, blur level)

Requirements:
  pip install PyGObject
  apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
              gtk4-layer-shell python3-xlib

Usage:
  xii-dock [--config /etc/xii-os/desktop/dock/dock-config.json]
           [--mode lite|standard|performance]
"""

import gi
import os
import sys
import json
import math
import signal
import subprocess
import threading
import argparse
from pathlib import Path
from typing import Optional

gi.require_version("Gtk",  "4.0")
gi.require_version("Adw",  "1")
gi.require_version("GLib", "2.0")
gi.require_version("Gdk",  "4.0")
gi.require_version("Gio",  "2.0")

from gi.repository import Gtk, Adw, GLib, Gdk, Gio

# Layer shell — positions window as a Wayland surface layer
try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

# D-Bus for window tracking
try:
    import dbus
    import dbus.mainloop.glib
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
CONFIG_PATH    = "/etc/xii-os/desktop/dock/dock-config.json"
CSS_PATH       = "/usr/share/xii-os/desktop/dock/xii-dock.css"
XII_MODE_FILE  = "/etc/xii-os/current-mode"
MAGNIFY_RANGE  = 120    # px radius of magnification effect
UPDATE_INTERVAL_MS = 2000  # Running app refresh interval


# ─────────────────────────────────────────────────────────────
# Dock Item — single app button
# ─────────────────────────────────────────────────────────────
class DockItem(Gtk.Box):
    """
    A single dock icon button with magnification, running indicator,
    badge count, and click handling.
    """

    def __init__(self, app_config: dict, icon_size: int, cfg: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.app_config  = app_config
        self.base_size   = icon_size
        self.current_size = icon_size
        self.cfg         = cfg
        self.is_running  = False
        self.badge_count = 0
        self.windows     = []

        self.set_css_classes(["dock-item"])
        self._build()

    def _build(self):
        # Icon container (overlay for badge)
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        # App icon button
        self.button = Gtk.Button()
        self.button.set_css_classes(["dock-button"])
        self.button.connect("clicked", self._on_click)

        # Icon image
        self.icon_img = Gtk.Image()
        self.icon_img.set_icon_name(self.app_config.get("icon", "application-x-executable"))
        self.icon_img.set_pixel_size(self.base_size)
        self.icon_img.set_css_classes(["dock-icon"])
        self.button.set_child(self.icon_img)
        self.overlay.set_child(self.button)

        # Badge label (notification count)
        self.badge = Gtk.Label(label="")
        self.badge.set_css_classes(["dock-badge"])
        self.badge.set_halign(Gtk.Align.END)
        self.badge.set_valign(Gtk.Align.START)
        self.badge.set_visible(False)
        self.overlay.add_overlay(self.badge)

        # Running indicator dot
        self.dot = Gtk.Box()
        self.dot.set_css_classes(["dock-active-dot"])
        self.dot.set_visible(False)
        self.append(self.dot)

        # Tooltip
        tooltip = self.app_config.get("name", self.app_config.get("id", "App"))
        self.button.set_tooltip_text(tooltip)

        # Hover motion tracking for magnification
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave",  self._on_leave)
        self.button.add_controller(motion)

    # ── Magnification ──────────────────────────────────────────
    def set_magnified_size(self, distance: float):
        """
        Compute magnified icon size based on cursor distance.
        Uses a cosine curve for smooth falloff.
        """
        if distance > MAGNIFY_RANGE:
            size = self.base_size
        else:
            max_size = self.cfg["appearance"].get("magnification_max", 72)
            t = 1.0 - (distance / MAGNIFY_RANGE)
            # Smooth cosine interpolation
            factor = (1.0 - math.cos(t * math.pi)) / 2.0
            size = int(self.base_size + (max_size - self.base_size) * factor)

        if size != self.current_size:
            self.current_size = size
            self.icon_img.set_pixel_size(size)

    def reset_size(self):
        if self.current_size != self.base_size:
            self.current_size = self.base_size
            self.icon_img.set_pixel_size(self.base_size)

    def _on_motion(self, controller, x, y):
        pass  # Magnification driven by DockBar global cursor handler

    def _on_leave(self, controller):
        self.reset_size()

    # ── Running State ──────────────────────────────────────────
    def set_running(self, is_running: bool):
        if is_running != self.is_running:
            self.is_running = is_running
            show_dot = is_running and self.cfg["appearance"].get("active_dot", True)
            self.dot.set_visible(show_dot)

    # ── Badge ──────────────────────────────────────────────────
    def set_badge(self, count: int):
        self.badge_count = count
        if count > 0:
            self.badge.set_label(str(count) if count < 100 else "99+")
            self.badge.set_visible(True)
        else:
            self.badge.set_visible(False)

    # ── Click Handling ─────────────────────────────────────────
    def _on_click(self, button):
        action = self.cfg["behavior"].get("click_action", "focus_or_launch")

        if action == "focus_or_launch":
            if self.is_running and self.windows:
                # Focus the first window
                self._focus_window(self.windows[0])
            else:
                self._launch()
        else:
            self._launch()

    def _launch(self):
        exec_cmd = self.app_config.get("exec", "")
        if exec_cmd:
            try:
                subprocess.Popen(
                    exec_cmd.split(),
                    start_new_session=True,
                    env={**os.environ, "XII_DOCK_LAUNCHED": "1"},
                )
            except FileNotFoundError:
                print(f"[XII Dock] Cannot launch: {exec_cmd}")

    def _focus_window(self, address: str):
        try:
            subprocess.run(
                ["hyprctl", "dispatch", "focuswindow", f"address:{address}"],
                check=False, capture_output=True
            )
        except FileNotFoundError:
            pass  # hyprctl not available (not running under Hyprland)


# ─────────────────────────────────────────────────────────────
# Dock Bar — the full dock widget
# ─────────────────────────────────────────────────────────────
class DockBar(Gtk.Box):
    """
    The dock container — glassmorphic panel holding all DockItems.
    """

    def __init__(self, config: dict, mode: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.config = config
        self.mode   = mode
        self.items: list[DockItem] = []

        self.set_css_classes(["dock-bar"])
        self._resolve_icon_size()
        self._build_items()
        self._start_window_tracker()

    def _resolve_icon_size(self):
        cfg = self.config["appearance"]
        size_map = {
            "lite":        cfg.get("icon_size_lite",   44),
            "standard":    cfg.get("icon_size",        52),
            "performance": cfg.get("icon_size_perf",   60),
        }
        self.icon_size = size_map.get(self.mode, cfg.get("icon_size", 52))

    def _build_items(self):
        cfg = self.config
        apps = cfg.get("pinned_apps", [])
        separators = set(cfg.get("separators", []))

        padding = cfg["appearance"].get("padding", 10)
        self.set_margin_start(padding)
        self.set_margin_end(padding)
        self.set_margin_top(padding)
        self.set_margin_bottom(padding)

        spacing = cfg["appearance"].get("spacing", 6)

        for i, app_cfg in enumerate(apps):
            if i in separators:
                sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                sep.set_css_classes(["dock-separator"])
                sep.set_margin_start(4)
                sep.set_margin_end(4)
                self.append(sep)

            item = DockItem(app_cfg, self.icon_size, cfg)
            item.set_margin_start(spacing // 2)
            item.set_margin_end(spacing // 2)
            self.items.append(item)
            self.append(item)

    def _start_window_tracker(self):
        """Poll hyprctl for running clients and update dock items."""
        GLib.timeout_add(500, self._first_update)
        GLib.timeout_add(UPDATE_INTERVAL_MS, self._update_running_apps)

    def _first_update(self):
        self._update_running_apps()
        return False  # One-shot

    def _update_running_apps(self):
        """Query Hyprland for open windows and mark running apps."""
        running_classes = set()
        try:
            result = subprocess.run(
                ["hyprctl", "clients", "-j"],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                clients = json.loads(result.stdout)
                for client in clients:
                    cls = client.get("class", "").lower()
                    running_classes.add(cls)
        except (FileNotFoundError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

        for item in self.items:
            app_id = item.app_config.get("id", "").lower()
            app_exec = item.app_config.get("exec", "").lower().split()[0] if item.app_config.get("exec") else ""
            is_running = app_id in running_classes or app_exec in running_classes
            item.set_running(is_running)

        return True  # Keep repeating

    def handle_global_motion(self, x_in_dock: float):
        """Called by DockWindow on cursor motion for magnification."""
        if not self.config["appearance"].get("magnification", True):
            return

        for item in self.items:
            # Get item center x position
            alloc = item.get_allocation()
            center_x = alloc.x + alloc.width / 2
            dist = abs(x_in_dock - center_x)
            item.set_magnified_size(dist)


# ─────────────────────────────────────────────────────────────
# Dock Window — Wayland layer surface
# ─────────────────────────────────────────────────────────────
class DockWindow(Gtk.ApplicationWindow):
    """
    The dock Wayland layer surface window.
    Uses gtk4-layer-shell to anchor to bottom of screen.
    """

    def __init__(self, app: Gtk.Application, config: dict, mode: str):
        super().__init__(application=app)
        self.config = config
        self.mode   = mode

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_css_classes(["dock-window"])

        # Set up as Wayland layer surface
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT,   False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT,  False)
            margin = config["appearance"].get("margin_bottom", 8)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, margin)
            GtkLayerShell.set_exclusive_zone(self, -1)  # Don't reserve space
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        else:
            print("[XII Dock] gtk4-layer-shell not available — running in windowed mode.")

        self.dock_bar = DockBar(config, mode)
        self.set_child(self.dock_bar)

        # Global motion for magnification
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_global_motion)
        motion.connect("leave",  self._on_global_leave)
        self.add_controller(motion)

    def _on_global_motion(self, controller, x, y):
        self.dock_bar.handle_global_motion(x)

    def _on_global_leave(self, controller):
        for item in self.dock_bar.items:
            item.reset_size()


# ─────────────────────────────────────────────────────────────
# XII Dock Application
# ─────────────────────────────────────────────────────────────
class XIIDockApp(Adw.Application):
    def __init__(self, config_path: str, mode: str):
        super().__init__(
            application_id="org.xiios.Dock",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.config_path = config_path
        self.mode        = mode
        self.connect("activate", self.on_activate)

        # Handle SIGUSR1 to reload config
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self._reload)

    def on_activate(self, app):
        config = self._load_config()
        self._apply_css()
        self.window = DockWindow(self, config, self.mode)
        self.window.present()

    def _load_config(self) -> dict:
        path = Path(self.config_path)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"[XII Dock] Config parse error: {e}")
        print(f"[XII Dock] Using default config (file not found: {path})")
        return {"appearance": {}, "pinned_apps": [], "behavior": {}, "separators": []}

    def _apply_css(self):
        css_path = Path(CSS_PATH)
        if not css_path.exists():
            # Fallback: inline minimal CSS
            css_path = Path(__file__).parent / "xii-dock.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )

    def _reload(self):
        print("[XII Dock] Reloading config (SIGUSR1)...")
        self.window.destroy()
        config = self._load_config()
        self.window = DockWindow(self, config, self.mode)
        self.window.present()
        return True


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="XII OS Dock Daemon")
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--mode",   default=None,
                        choices=["lite", "standard", "performance"],
                        help="Performance mode override")
    args = parser.parse_args()

    # Read mode from system if not specified
    mode = args.mode
    if not mode:
        try:
            mode = Path(XII_MODE_FILE).read_text().strip()
        except FileNotFoundError:
            mode = "standard"
    if mode not in ("lite", "standard", "performance"):
        mode = "standard"

    if HAS_DBUS:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    app = XIIDockApp(config_path=args.config, mode=mode)
    sys.exit(app.run(sys.argv[:1]))


if __name__ == "__main__":
    main()
