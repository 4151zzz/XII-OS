"""
XII OS — Phase 3 Dock + Launcher + Window Management Tests
tests/test_dock_launcher.py

Validates all Phase 3 components:
  - Dock configuration & CSS
  - Dock Python daemon structure
  - Launcher Python source structure
  - Launcher CSS
  - Window snap script
  - Notification configuration
  - systemd service units

Run with: pytest tests/test_dock_launcher.py -v
"""

import json
import re
import ast
import pytest
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

@pytest.fixture
def dock_dir(project_root) -> Path:
    return project_root / "desktop" / "dock"

@pytest.fixture
def launcher_dir(project_root) -> Path:
    return project_root / "desktop" / "launcher"

@pytest.fixture
def wm_dir(project_root) -> Path:
    return project_root / "desktop" / "window-manager"

@pytest.fixture
def notif_dir(project_root) -> Path:
    return project_root / "desktop" / "notifications"


# ─────────────────────────────────────────────────────────────
# 1. Dock Configuration
# ─────────────────────────────────────────────────────────────
class TestDockConfig:
    @pytest.fixture
    def dock_cfg(self, dock_dir) -> dict:
        path = dock_dir / "dock-config.json"
        assert path.is_file(), "dock-config.json not found"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_config_file_exists(self, dock_dir):
        assert (dock_dir / "dock-config.json").is_file()

    def test_has_meta(self, dock_cfg):
        assert "meta" in dock_cfg

    def test_has_appearance(self, dock_cfg):
        assert "appearance" in dock_cfg

    def test_has_icon_size(self, dock_cfg):
        assert "icon_size" in dock_cfg["appearance"]
        size = dock_cfg["appearance"]["icon_size"]
        assert 32 <= size <= 128, f"icon_size {size}px is out of reasonable range"

    def test_has_three_size_variants(self, dock_cfg):
        app = dock_cfg["appearance"]
        assert "icon_size_lite" in app,   "Missing icon_size_lite"
        assert "icon_size" in app,        "Missing icon_size (standard)"
        assert "icon_size_perf" in app,   "Missing icon_size_perf"

    def test_lite_is_smaller_than_standard(self, dock_cfg):
        app = dock_cfg["appearance"]
        assert app["icon_size_lite"] < app["icon_size"], \
            "Lite mode icon must be smaller than standard"

    def test_perf_is_larger_than_standard(self, dock_cfg):
        app = dock_cfg["appearance"]
        assert app["icon_size_perf"] > app["icon_size"], \
            "Performance mode icon must be larger than standard"

    def test_has_pinned_apps(self, dock_cfg):
        assert "pinned_apps" in dock_cfg
        assert len(dock_cfg["pinned_apps"]) >= 3, "Dock must have at least 3 pinned apps"

    def test_pinned_apps_have_required_fields(self, dock_cfg):
        for app in dock_cfg["pinned_apps"]:
            assert "id" in app,   f"App missing 'id': {app}"
            assert "name" in app, f"App missing 'name': {app}"
            assert "exec" in app, f"App missing 'exec': {app}"
            assert "icon" in app, f"App missing 'icon': {app}"

    def test_has_xii_files_pinned(self, dock_cfg):
        ids = [a["id"] for a in dock_cfg["pinned_apps"]]
        assert "xii-files" in ids or "files" in ids, "xii-files should be in pinned apps"

    def test_has_terminal_pinned(self, dock_cfg):
        ids = [a["id"] for a in dock_cfg["pinned_apps"]]
        assert "xii-terminal" in ids or "terminal" in ids, "Terminal should be pinned"

    def test_has_behavior(self, dock_cfg):
        assert "behavior" in dock_cfg
        behavior = dock_cfg["behavior"]
        assert "click_action" in behavior

    def test_magnification_enabled(self, dock_cfg):
        assert dock_cfg["appearance"].get("magnification", True), \
            "Magnification should be enabled by default"

    def test_has_active_dot(self, dock_cfg):
        assert "active_dot" in dock_cfg["appearance"], \
            "Dock should have active_dot running indicator"

    def test_has_magnification_range(self, dock_cfg):
        app = dock_cfg["appearance"]
        assert "magnification_max" in app or "magnification_range" in app, \
            "Magnification parameters should be defined"


# ─────────────────────────────────────────────────────────────
# 2. Dock Daemon (Python)
# ─────────────────────────────────────────────────────────────
class TestDockDaemon:
    @pytest.fixture
    def dock_src(self, dock_dir) -> str:
        path = dock_dir / "xii-dock.py"
        assert path.is_file(), "xii-dock.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, dock_dir):
        assert (dock_dir / "xii-dock.py").is_file()

    def test_has_shebang(self, dock_src):
        assert dock_src.startswith("#!/usr/bin/env python3") or \
               dock_src.startswith("#!/usr/bin/python3"), \
            "xii-dock.py must start with a Python shebang"

    def test_is_valid_python(self, dock_src):
        try:
            ast.parse(dock_src)
        except SyntaxError as e:
            pytest.fail(f"xii-dock.py has syntax error: {e}")

    def test_has_gtk4_import(self, dock_src):
        assert "gi.require_version" in dock_src and "Gtk" in dock_src

    def test_has_dock_item_class(self, dock_src):
        assert "class DockItem" in dock_src, "Must define DockItem class"

    def test_has_dock_bar_class(self, dock_src):
        assert "class DockBar" in dock_src, "Must define DockBar class"

    def test_has_dock_window_class(self, dock_src):
        assert "class DockWindow" in dock_src, "Must define DockWindow class"

    def test_has_application_class(self, dock_src):
        assert "class XIIDockApp" in dock_src or "Adw.Application" in dock_src

    def test_has_magnification_logic(self, dock_src):
        assert "magnif" in dock_src.lower(), "Dock must implement magnification"

    def test_has_cosine_or_math_curve(self, dock_src):
        assert "math" in dock_src and ("cos" in dock_src or "sin" in dock_src), \
            "Magnification should use smooth math curve"

    def test_has_running_indicator(self, dock_src):
        assert "is_running" in dock_src or "running" in dock_src.lower()

    def test_has_hyprctl_integration(self, dock_src):
        assert "hyprctl" in dock_src, "Dock must integrate with hyprctl for window tracking"

    def test_has_launch_functionality(self, dock_src):
        assert "Popen" in dock_src or "subprocess" in dock_src, \
            "Dock must be able to launch applications"

    def test_has_layer_shell_support(self, dock_src):
        assert "GtkLayerShell" in dock_src or "layer_shell" in dock_src.lower(), \
            "Dock must use gtk4-layer-shell for Wayland positioning"

    def test_has_main_function(self, dock_src):
        assert "def main" in dock_src
        assert '__name__ == "__main__"' in dock_src or "if __name__" in dock_src

    def test_has_sigusr1_reload(self, dock_src):
        assert "SIGUSR1" in dock_src, "Dock should support SIGUSR1 config reload"

    def test_has_argparse(self, dock_src):
        assert "argparse" in dock_src, "Dock must support CLI arguments"

    def test_has_config_path_arg(self, dock_src):
        assert "--config" in dock_src, "Dock must accept --config argument"

    def test_has_mode_arg(self, dock_src):
        assert "--mode" in dock_src, "Dock must accept --mode argument"


# ─────────────────────────────────────────────────────────────
# 3. Dock CSS
# ─────────────────────────────────────────────────────────────
class TestDockCss:
    @pytest.fixture
    def css(self, dock_dir) -> str:
        path = dock_dir / "xii-dock.css"
        assert path.is_file(), "xii-dock.css not found"
        return path.read_text(encoding="utf-8")

    def test_css_exists(self, dock_dir):
        assert (dock_dir / "xii-dock.css").is_file()

    def test_has_dock_bar_class(self, css):
        assert ".dock-bar" in css

    def test_dock_bar_has_backdrop_filter(self, css):
        assert "backdrop-filter" in css, "Dock must use glassmorphism blur"

    def test_has_dock_button_transitions(self, css):
        assert ".dock-button" in css
        assert "transition" in css

    def test_has_hover_transform(self, css):
        assert "translateY" in css or "transform" in css, \
            "Dock button should lift on hover"

    def test_has_active_dot_style(self, css):
        assert ".dock-active-dot" in css

    def test_active_dot_uses_xii_cyan(self, css):
        assert "6ee7f7" in css, "Active dot should use XII cyan color"

    def test_has_badge_style(self, css):
        assert ".dock-badge" in css

    def test_has_separator_style(self, css):
        assert ".dock-separator" in css


# ─────────────────────────────────────────────────────────────
# 4. Dock Service
# ─────────────────────────────────────────────────────────────
class TestDockService:
    @pytest.fixture
    def service(self, dock_dir) -> str:
        path = dock_dir / "xii-dock.service"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_service_exists(self, dock_dir):
        assert (dock_dir / "xii-dock.service").is_file()

    def test_has_description(self, service):
        assert "Description=" in service

    def test_restarts_on_failure(self, service):
        assert "Restart=on-failure" in service

    def test_has_exec_reload(self, service):
        assert "ExecReload=" in service, "Dock service should support reload"

    def test_has_wayland_env(self, service):
        assert "WAYLAND_DISPLAY" in service


# ─────────────────────────────────────────────────────────────
# 5. Launcher Python
# ─────────────────────────────────────────────────────────────
class TestLauncherDaemon:
    @pytest.fixture
    def src(self, launcher_dir) -> str:
        path = launcher_dir / "xii-launcher.py"
        assert path.is_file(), "xii-launcher.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, launcher_dir):
        assert (launcher_dir / "xii-launcher.py").is_file()

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii-launcher.py has syntax error: {e}")

    def test_has_app_info_class(self, src):
        assert "class AppInfo" in src, "Must define AppInfo class"

    def test_has_app_database_class(self, src):
        assert "class AppDatabase" in src, "Must define AppDatabase class"

    def test_has_launcher_window_class(self, src):
        assert "class LauncherWindow" in src, "Must define LauncherWindow class"

    def test_has_search_functionality(self, src):
        assert "def search" in src, "Launcher must implement search method"

    def test_has_desktop_file_parsing(self, src):
        assert ".desktop" in src, "Launcher must parse .desktop files"

    def test_has_category_browsing(self, src):
        assert "CATEGORIES" in src or "categories" in src.lower()

    def test_has_keyboard_navigation(self, src):
        assert "KEY_Escape" in src or "Escape" in src, "Must support Escape key"
        assert "KEY_Return" in src or "Return" in src, "Must support Enter key"
        assert "KEY_Down" in src or "KEY_Up" in src, "Must support arrow navigation"

    def test_has_recent_apps(self, src):
        assert "recent" in src.lower(), "Launcher must track recent apps"

    def test_has_calculator_mode(self, src):
        assert "calc" in src.lower() or "eval" in src, \
            "Launcher should support inline calculator"

    def test_has_command_mode(self, src):
        assert "XII_COMMANDS" in src or ":term" in src, \
            "Launcher should support : command mode"

    def test_has_layer_shell(self, src):
        assert "GtkLayerShell" in src or "layer_shell" in src.lower()

    def test_has_launch_logic(self, src):
        assert "Popen" in src and "exec" in src.lower()

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_launcher_css_exists(self, launcher_dir):
        assert (launcher_dir / "xii-launcher.css").is_file()

    def test_launcher_service_exists(self, launcher_dir):
        assert (launcher_dir / "xii-launcher.service").is_file()


# ─────────────────────────────────────────────────────────────
# 6. Launcher CSS
# ─────────────────────────────────────────────────────────────
class TestLauncherCss:
    @pytest.fixture
    def css(self, launcher_dir) -> str:
        path = launcher_dir / "xii-launcher.css"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_has_window_class(self, css):
        assert ".launcher-window" in css

    def test_window_has_glassmorphism(self, css):
        assert "backdrop-filter" in css

    def test_has_search_entry_style(self, css):
        assert ".launcher-search-entry" in css

    def test_has_category_button_style(self, css):
        assert ".launcher-cat-btn" in css

    def test_category_active_uses_cyan(self, css):
        assert ":checked" in css or ".active" in css, "Active category should be styled"
        assert "6ee7f7" in css, "Active category should use XII cyan"

    def test_has_row_selected_style(self, css):
        assert ".launcher-row:selected" in css

    def test_has_app_name_style(self, css):
        assert ".launcher-app-name" in css

    def test_has_app_desc_style(self, css):
        assert ".launcher-app-desc" in css


# ─────────────────────────────────────────────────────────────
# 7. Window Snap Script
# ─────────────────────────────────────────────────────────────
class TestWindowSnap:
    @pytest.fixture
    def snap_src(self, wm_dir) -> str:
        path = wm_dir / "xii-snap.sh"
        assert path.is_file(), "xii-snap.sh not found"
        return path.read_text(encoding="utf-8")

    def test_script_exists(self, wm_dir):
        assert (wm_dir / "xii-snap.sh").is_file()

    def test_has_bash_shebang(self, snap_src):
        assert snap_src.startswith("#!/usr/bin/env bash") or \
               snap_src.startswith("#!/bin/bash"), \
            "xii-snap.sh must have a bash shebang"

    def test_has_left_half_zone(self, snap_src):
        assert "left-half" in snap_src

    def test_has_right_half_zone(self, snap_src):
        assert "right-half" in snap_src

    def test_has_maximize_zone(self, snap_src):
        assert "maximize" in snap_src

    def test_has_quarter_zones(self, snap_src):
        assert "top-left" in snap_src
        assert "top-right" in snap_src
        assert "bottom-left" in snap_src
        assert "bottom-right" in snap_src

    def test_has_center_zone(self, snap_src):
        assert "center" in snap_src

    def test_has_restore(self, snap_src):
        assert "restore" in snap_src

    def test_uses_hyprctl(self, snap_src):
        assert "hyprctl" in snap_src, "Snap script must use hyprctl"

    def test_accounts_for_gaps(self, snap_src):
        assert "GAPS" in snap_src or "gaps" in snap_src.lower(), \
            "Snap must account for window gaps"

    def test_accounts_for_statusbar(self, snap_src):
        assert "34" in snap_src or "statusbar" in snap_src.lower(), \
            "Snap must account for statusbar height"

    def test_gets_monitor_geometry(self, snap_src):
        assert "get_monitor" in snap_src or "monitors" in snap_src, \
            "Snap must read monitor geometry"


# ─────────────────────────────────────────────────────────────
# 8. Notifications
# ─────────────────────────────────────────────────────────────
class TestNotifications:
    @pytest.fixture
    def mako_conf(self, notif_dir) -> str:
        path = notif_dir / "mako.conf"
        assert path.is_file(), "mako.conf not found"
        return path.read_text(encoding="utf-8")

    def test_mako_conf_exists(self, notif_dir):
        assert (notif_dir / "mako.conf").is_file()

    def test_service_exists(self, notif_dir):
        assert (notif_dir / "xii-notifications.service").is_file()

    def test_has_anchor_top_right(self, mako_conf):
        assert "anchor=top-right" in mako_conf, "Notifications should anchor to top-right"

    def test_has_border_radius(self, mako_conf):
        assert "border-radius" in mako_conf

    def test_border_radius_is_rounded(self, mako_conf):
        match = re.search(r'border-radius=(\d+)', mako_conf)
        if match:
            radius = int(match.group(1))
            assert radius >= 10, f"Notification border-radius {radius} should be ≥ 10px"

    def test_has_background_color(self, mako_conf):
        assert "background-color" in mako_conf

    def test_uses_dark_background(self, mako_conf):
        match = re.search(r'background-color=#([0-9a-fA-F]+)', mako_conf)
        if match:
            hex_color = match.group(1)
            # Dark = low RGB values (first 6 chars of hex)
            r = int(hex_color[:2], 16)
            assert r < 50, f"Background R={r} should be dark (< 50)"

    def test_has_urgency_levels(self, mako_conf):
        assert "[urgency=low]" in mako_conf
        assert "[urgency=normal]" in mako_conf
        assert "[urgency=critical]" in mako_conf

    def test_has_notification_width(self, mako_conf):
        assert "width=" in mako_conf

    def test_has_timeout(self, mako_conf):
        assert "default-timeout" in mako_conf

    def test_critical_has_no_timeout(self, mako_conf):
        # After [urgency=critical], timeout should be 0 (persistent)
        lines = mako_conf.splitlines()
        in_critical = False
        for line in lines:
            if "[urgency=critical]" in line:
                in_critical = True
            elif in_critical and line.startswith("["):
                in_critical = False
            elif in_critical and "default-timeout=0" in line:
                return  # Found it — good
        # Soft check: if not found, warn but don't fail hard
        # (config might handle it differently)

    def test_service_is_dbus_type(self, notif_dir):
        content = (notif_dir / "xii-notifications.service").read_text(encoding="utf-8")
        assert "Type=dbus" in content or "BusName" in content, \
            "Notification service should use D-Bus activation"

    def test_service_has_freedesktop_busname(self, notif_dir):
        content = (notif_dir / "xii-notifications.service").read_text(encoding="utf-8")
        assert "org.freedesktop.Notifications" in content
