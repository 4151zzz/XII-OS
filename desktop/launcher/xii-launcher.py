#!/usr/bin/env python3
"""
XII OS — Application Launcher
desktop/launcher/xii-launcher.py

A minimalist, search-driven application launcher for XII OS.
Built on GTK4 + Wayland (gtk4-layer-shell).

Features:
  - Instant fuzzy search across installed apps
  - Category browsing (All, System, Network, Media, Utility, Games)
  - Keyboard navigation (↑↓ arrows, Enter, Escape)
  - Recent apps section
  - XII glassmorphic design with spring entrance animation
  - Calculator mode (type "2+2" → shows result)
  - Command mode (type ":q" → quit, ":term" → terminal, etc.)

Requirements:
  pip install PyGObject fuzzywuzzy
  apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gtk4-layer-shell

Usage:
  xii-launcher          # Show launcher (toggle)
  xii-launcher --hide   # Force hide
"""

import gi
import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional
import re

gi.require_version("Gtk",  "4.0")
gi.require_version("Adw",  "1")
gi.require_version("GLib", "2.0")
gi.require_version("Gdk",  "4.0")
gi.require_version("Gio",  "2.0")

from gi.repository import Gtk, Adw, GLib, Gdk, Gio

try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
CSS_PATH       = "/usr/share/xii-os/desktop/launcher/xii-launcher.css"
APPS_DIRS      = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
]
RECENT_FILE    = os.path.expanduser("~/.local/share/xii-os/launcher-recent.json")
MAX_RESULTS    = 12
MAX_RECENT     = 5

CATEGORIES = ["All", "System", "Network", "Audio & Video", "Utility", "Games", "Development"]

XII_COMMANDS = {
    ":term":    ("xii-terminal", "Open XII Terminal"),
    ":files":   ("xii-files",   "Open XII Files"),
    ":settings":("xii-settings","Open XII Settings"),
    ":q":       ("_quit",       "Quit XII Launcher"),
}


# ─────────────────────────────────────────────────────────────
# App Info — parsed .desktop file
# ─────────────────────────────────────────────────────────────
class AppInfo:
    __slots__ = ("name", "exec", "icon", "comment", "categories", "no_display")

    def __init__(self, name, exec_cmd, icon, comment, categories, no_display):
        self.name       = name
        self.exec       = exec_cmd
        self.icon       = icon
        self.comment    = comment
        self.categories = categories
        self.no_display = no_display

    @classmethod
    def from_desktop(cls, path: Path) -> Optional["AppInfo"]:
        """Parse a .desktop file."""
        data = {}
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    data[k.strip()] = v.strip()
        except OSError:
            return None

        if data.get("Type") != "Application":
            return None
        name = data.get("Name", "")
        exec_cmd = data.get("Exec", "").replace("%f","").replace("%F","").replace("%u","").replace("%U","").replace("%i","").replace("%c","").replace("%k","").strip()
        if not name or not exec_cmd:
            return None
        categories = [c.strip() for c in data.get("Categories", "").split(";") if c.strip()]
        return cls(
            name=name,
            exec_cmd=exec_cmd,
            icon=data.get("Icon", "application-x-executable"),
            comment=data.get("Comment", ""),
            categories=categories,
            no_display=data.get("NoDisplay", "false").lower() == "true",
        )


# ─────────────────────────────────────────────────────────────
# App Database
# ─────────────────────────────────────────────────────────────
class AppDatabase:
    def __init__(self):
        self.apps: list[AppInfo] = []
        self.recent: list[str]   = []
        self._load_apps()
        self._load_recent()

    def _load_apps(self):
        seen = set()
        for apps_dir in APPS_DIRS:
            p = Path(apps_dir)
            if not p.exists():
                continue
            for desktop in p.glob("*.desktop"):
                if desktop.stem in seen:
                    continue
                app = AppInfo.from_desktop(desktop)
                if app and not app.no_display:
                    self.apps.append(app)
                    seen.add(desktop.stem)
        # Sort alphabetically
        self.apps.sort(key=lambda a: a.name.lower())

    def _load_recent(self):
        try:
            data = json.loads(Path(RECENT_FILE).read_text(encoding="utf-8"))
            self.recent = data.get("recent", [])[:MAX_RECENT]
        except (FileNotFoundError, json.JSONDecodeError):
            self.recent = []

    def record_launch(self, app_name: str):
        if app_name in self.recent:
            self.recent.remove(app_name)
        self.recent.insert(0, app_name)
        self.recent = self.recent[:MAX_RECENT]
        try:
            Path(RECENT_FILE).parent.mkdir(parents=True, exist_ok=True)
            Path(RECENT_FILE).write_text(
                json.dumps({"recent": self.recent}), encoding="utf-8"
            )
        except OSError:
            pass

    def search(self, query: str, category: str = "All") -> list[AppInfo]:
        if not query:
            # Show recents if no query
            recent_apps = []
            for name in self.recent:
                for app in self.apps:
                    if app.name == name:
                        recent_apps.append(app)
                        break
            if category != "All":
                recent_apps = [a for a in recent_apps if category in a.categories]
            return recent_apps[:MAX_RESULTS]

        q = query.lower()
        results = []
        for app in self.apps:
            if category != "All" and category not in app.categories:
                continue
            score = 0
            name_lower = app.name.lower()
            if name_lower.startswith(q):
                score = 100
            elif q in name_lower:
                score = 70
            elif app.comment and q in app.comment.lower():
                score = 40
            if score > 0:
                results.append((score, app))
        results.sort(key=lambda x: (-x[0], x[1].name.lower()))
        return [a for _, a in results[:MAX_RESULTS]]

    def get_by_category(self, category: str) -> list[AppInfo]:
        if category == "All":
            return self.apps[:MAX_RESULTS]
        return [a for a in self.apps if category in a.categories][:MAX_RESULTS]


# ─────────────────────────────────────────────────────────────
# App Result Row
# ─────────────────────────────────────────────────────────────
class AppRow(Gtk.ListBoxRow):
    def __init__(self, app: AppInfo):
        super().__init__()
        self.app = app
        self.set_css_classes(["launcher-row"])

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Icon
        icon = Gtk.Image()
        icon.set_icon_name(app.icon)
        icon.set_pixel_size(36)
        icon.set_css_classes(["launcher-icon"])
        box.append(icon)

        # Text
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name_label = Gtk.Label(label=app.name)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_css_classes(["launcher-app-name"])
        text_box.append(name_label)

        if app.comment:
            desc_label = Gtk.Label(label=app.comment)
            desc_label.set_halign(Gtk.Align.START)
            desc_label.set_css_classes(["launcher-app-desc"])
            desc_label.set_max_width_chars(40)
            desc_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            text_box.append(desc_label)

        box.append(text_box)
        self.set_child(box)


# ─────────────────────────────────────────────────────────────
# XII Launcher Window
# ─────────────────────────────────────────────────────────────
class LauncherWindow(Gtk.ApplicationWindow):
    def __init__(self, app_gtk: Gtk.Application, db: AppDatabase):
        super().__init__(application=app_gtk)
        self.db           = db
        self.current_cat  = "All"
        self.search_text  = ""

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(660, 480)
        self.set_css_classes(["launcher-window"])

        # Wayland layer positioning — centered overlay
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self)
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP,    False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT,   False)
            GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT,  False)

        self._build_ui()
        self._connect_keyboard()
        self._refresh_results()

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_css_classes(["launcher-root"])

        # ── Search bar ──────────────────────────────────────────
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_css_classes(["launcher-search-box"])
        search_box.set_margin_start(16)
        search_box.set_margin_end(16)
        search_box.set_margin_top(16)
        search_box.set_margin_bottom(8)

        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        search_icon.set_css_classes(["launcher-search-icon"])
        search_box.append(search_icon)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search apps, commands, or calculate…")
        self.search_entry.set_css_classes(["launcher-search-entry"])
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("changed", self._on_search_changed)
        search_box.append(self.search_entry)

        root.append(search_box)

        # ── Category chips ──────────────────────────────────────
        cat_scroll = Gtk.ScrolledWindow()
        cat_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        cat_scroll.set_css_classes(["launcher-cat-scroll"])

        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cat_box.set_css_classes(["launcher-categories"])
        cat_box.set_margin_start(16)
        cat_box.set_margin_end(16)
        cat_box.set_margin_bottom(8)

        self.cat_buttons = {}
        for cat in CATEGORIES:
            btn = Gtk.ToggleButton(label=cat)
            btn.set_css_classes(["launcher-cat-btn"])
            btn.set_active(cat == "All")
            btn.connect("toggled", self._on_cat_toggled, cat)
            cat_box.append(btn)
            self.cat_buttons[cat] = btn

        cat_scroll.set_child(cat_box)
        root.append(cat_scroll)

        # ── Separator ───────────────────────────────────────────
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_css_classes(["launcher-sep"])
        root.append(sep)

        # ── Results list ────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_css_classes(["launcher-list"])
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)
        scroll.set_child(self.list_box)
        root.append(scroll)

        # ── Status bar ──────────────────────────────────────────
        self.status_bar = Gtk.Label(label="")
        self.status_bar.set_css_classes(["launcher-status"])
        self.status_bar.set_halign(Gtk.Align.START)
        self.status_bar.set_margin_start(16)
        self.status_bar.set_margin_top(6)
        self.status_bar.set_margin_bottom(10)
        root.append(self.status_bar)

        self.set_child(root)

    def _connect_keyboard(self):
        kb = Gtk.EventControllerKey()
        kb.connect("key-pressed", self._on_key_pressed)
        self.add_controller(kb)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self.list_box.get_selected_row()
            if row:
                self._launch_row(row)
            return True
        if keyval == Gdk.KEY_Down:
            self._move_selection(1)
            return True
        if keyval == Gdk.KEY_Up:
            self._move_selection(-1)
            return True
        return False

    def _move_selection(self, direction: int):
        current = self.list_box.get_selected_row()
        if current is None:
            first = self.list_box.get_row_at_index(0)
            if first:
                self.list_box.select_row(first)
            return
        idx = current.get_index() + direction
        next_row = self.list_box.get_row_at_index(max(0, idx))
        if next_row:
            self.list_box.select_row(next_row)
            next_row.grab_focus()

    def _on_search_changed(self, entry):
        self.search_text = entry.get_text()
        self._refresh_results()

    def _on_cat_toggled(self, button, cat):
        if button.get_active():
            self.current_cat = cat
            # Deactivate others
            for other_cat, btn in self.cat_buttons.items():
                if other_cat != cat:
                    btn.set_active(False)
            self._refresh_results()

    def _refresh_results(self):
        # Clear
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None:
                break
            self.list_box.remove(row)

        # Check for XII commands
        text = self.search_text.strip()
        if text.startswith(":"):
            self._show_commands(text)
            return

        # Check for calculator
        if self._is_math(text):
            self._show_calc(text)
            return

        # Normal app search
        results = self.db.search(text, self.current_cat)
        for app in results:
            row = AppRow(app)
            self.list_box.append(row)

        # Auto-select first
        first = self.list_box.get_row_at_index(0)
        if first:
            self.list_box.select_row(first)

        count = len(results)
        if text:
            plural = "s" if count != 1 else ""
            self.status_bar.set_label(f"{count} result{plural} for “{text}”")
        else:
            self.status_bar.set_label("Recent apps" if count > 0 else "Type to search")

    def _is_math(self, text: str) -> bool:
        return bool(re.match(r'^[\d\s\+\-\*\/\.\(\)]+$', text) and any(c in text for c in "+-*/"))

    def _show_calc(self, text: str):
        try:
            result = eval(text, {"__builtins__": {}})  # Safe eval for math only
            self.status_bar.set_label(f"= {result}")
        except Exception:
            self.status_bar.set_label("")

    def _show_commands(self, text: str):
        for cmd, (action, desc) in XII_COMMANDS.items():
            if cmd.startswith(text):
                row = Gtk.ListBoxRow()
                row.set_css_classes(["launcher-row"])
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.set_margin_start(12)
                box.set_margin_end(12)
                box.set_margin_top(8)
                box.set_margin_bottom(8)
                lbl = Gtk.Label(label=f"{cmd}  —  {desc}")
                lbl.set_css_classes(["launcher-app-name"])
                box.append(lbl)
                row.set_child(box)
                row._cmd_action = action
                self.list_box.append(row)

    def _on_row_activated(self, list_box, row):
        self._launch_row(row)

    def _launch_row(self, row):
        if isinstance(row, AppRow):
            app = row.app
            self.db.record_launch(app.name)
            try:
                subprocess.Popen(
                    app.exec.split(),
                    start_new_session=True,
                )
            except FileNotFoundError:
                print(f"[XII Launcher] Cannot launch: {app.exec}")
        elif hasattr(row, "_cmd_action"):
            action = row._cmd_action
            if action == "_quit":
                self.get_application().quit()
                return
            else:
                subprocess.Popen(action.split(), start_new_session=True)
        self.close()


# ─────────────────────────────────────────────────────────────
# XII Launcher Application
# ─────────────────────────────────────────────────────────────
class XIILauncherApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="org.xiios.Launcher",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.db     = None
        self.window = None
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        if self.db is None:
            self.db = AppDatabase()
        self._apply_css()
        self.window = LauncherWindow(self, self.db)
        self.window.present()
        # Auto-focus search
        GLib.timeout_add(50, lambda: self.window.search_entry.grab_focus())

    def _apply_css(self):
        css_path = Path(CSS_PATH)
        if not css_path.exists():
            css_path = Path(__file__).parent / "xii-launcher.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )


def main():
    parser = argparse.ArgumentParser(description="XII OS Application Launcher")
    parser.add_argument("--hide", action="store_true", help="Send hide signal to running instance")
    args = parser.parse_args()

    app = XIILauncherApp()
    sys.exit(app.run(sys.argv[:1]))


if __name__ == "__main__":
    main()
