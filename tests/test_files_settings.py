"""
XII OS — Phase 4 Files + Settings Tests
tests/test_files_settings.py

Validates:
  - XII Files Python daemon structure
  - XII Files CSS
  - XII Settings Python structure (12 panels)
  - XII Settings CSS
  - systemd service units

Run with: pytest tests/test_files_settings.py -v
"""

import ast
import json
import pytest
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent

@pytest.fixture
def files_dir(project_root) -> Path:
    return project_root / "desktop" / "files"

@pytest.fixture
def settings_dir(project_root) -> Path:
    return project_root / "desktop" / "settings"


# ─────────────────────────────────────────────────────────────
# 1. XII Files — Python Daemon
# ─────────────────────────────────────────────────────────────
class TestFilesApp:
    @pytest.fixture
    def src(self, files_dir) -> str:
        path = files_dir / "xii-files.py"
        assert path.is_file(), "xii-files.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, files_dir):
        assert (files_dir / "xii-files.py").is_file()

    def test_has_shebang(self, src):
        assert src.startswith("#!/usr/bin/env python3") or \
               src.startswith("#!/usr/bin/python3")

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii-files.py syntax error: {e}")

    def test_has_gtk4_import(self, src):
        assert "gi.require_version" in src
        assert '"Gtk"' in src and '"4.0"' in src

    def test_has_file_item_class(self, src):
        assert "class FileItem" in src

    def test_file_item_handles_dir_and_file(self, src):
        assert "is_dir" in src

    def test_has_breadcrumb_class(self, src):
        assert "class BreadcrumbBar" in src or "Breadcrumb" in src

    def test_has_sidebar_class(self, src):
        assert "class FileSidebar" in src

    def test_has_bookmarks(self, src):
        assert "BOOKMARKS" in src
        assert "Home" in src
        assert "Documents" in src
        assert "Downloads" in src
        assert "Pictures" in src

    def test_has_minimum_4_bookmarks(self, src):
        import re
        bookmarks = re.findall(r'"(Home|Desktop|Documents|Downloads|Pictures|Music|Videos|Trash)"', src)
        assert len(set(bookmarks)) >= 4, "Must have at least 4 bookmarks"

    def test_has_grid_view(self, src):
        assert "class FileGridView" in src or "FlowBox" in src

    def test_has_list_view(self, src):
        assert "class FileListView" in src or "ListBox" in src

    def test_has_files_window_class(self, src):
        assert "class FilesWindow" in src

    def test_has_navigation_history(self, src):
        assert "history" in src, "Files must support back/forward navigation history"

    def test_has_navigate_method(self, src):
        assert "_navigate" in src or "def navigate" in src

    def test_has_back_forward(self, src):
        assert "_go_back" in src or "go_back" in src
        assert "_go_forward" in src or "go_forward" in src

    def test_has_hidden_file_toggle(self, src):
        assert "show_hidden" in src or "hidden" in src.lower()

    def test_has_xdg_open(self, src):
        assert "xdg-open" in src, "Files must open files with xdg-open"

    def test_has_mime_detection(self, src):
        assert "mimetypes" in src or "mimetype" in src.lower()

    def test_has_size_human_readable(self, src):
        assert "size_human" in src or "KB" in src or "MB" in src

    def test_has_search_support(self, src):
        assert "search" in src.lower() and ("SearchBar" in src or "SearchEntry" in src)

    def test_has_status_bar(self, src):
        assert "status_bar" in src or "status" in src.lower()

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_has_adw_application(self, src):
        assert "Adw.Application" in src or "XIIFilesApp" in src


# ─────────────────────────────────────────────────────────────
# 2. XII Files — CSS
# ─────────────────────────────────────────────────────────────
class TestFilesCss:
    @pytest.fixture
    def css(self, files_dir) -> str:
        path = files_dir / "xii-files.css"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_css_exists(self, files_dir):
        assert (files_dir / "xii-files.css").is_file()

    def test_has_window_style(self, css):
        assert ".files-window" in css

    def test_has_headerbar_style(self, css):
        assert ".files-headerbar" in css

    def test_has_breadcrumb_style(self, css):
        assert "breadcrumb" in css

    def test_has_sidebar_style(self, css):
        assert ".files-sidebar" in css or "sidebar" in css

    def test_has_file_grid_style(self, css):
        assert ".file-grid" in css or ".file-cell" in css

    def test_has_file_list_style(self, css):
        assert ".file-list" in css or ".file-row" in css

    def test_selected_uses_cyan(self, css):
        assert "6ee7f7" in css, "Selected files should use XII cyan highlight"

    def test_has_file_name_style(self, css):
        assert ".file-name" in css

    def test_has_status_bar_style(self, css):
        assert ".files-status" in css


# ─────────────────────────────────────────────────────────────
# 3. XII Files — Service
# ─────────────────────────────────────────────────────────────
class TestFilesService:
    @pytest.fixture
    def service(self, files_dir) -> str:
        path = files_dir / "xii-files.service"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_service_exists(self, files_dir):
        assert (files_dir / "xii-files.service").is_file()

    def test_has_description(self, service):
        assert "Description=" in service

    def test_restarts_on_failure(self, service):
        assert "Restart=on-failure" in service

    def test_has_wayland_env(self, service):
        assert "WAYLAND_DISPLAY" in service


# ─────────────────────────────────────────────────────────────
# 4. XII Settings — Python
# ─────────────────────────────────────────────────────────────
class TestSettingsApp:
    @pytest.fixture
    def src(self, settings_dir) -> str:
        path = settings_dir / "xii-settings.py"
        assert path.is_file(), "xii-settings.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, settings_dir):
        assert (settings_dir / "xii-settings.py").is_file()

    def test_has_shebang(self, src):
        assert src.startswith("#!/usr/bin/env python3")

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii-settings.py syntax error: {e}")

    def test_has_minimum_10_panels(self, src):
        import re
        panels = re.findall(r'"(\w[\w-]+)",\s+"[^"]+",\s+"[^"]+-symbolic"', src)
        assert len(panels) >= 10, f"Expected ≥ 10 settings panels, found {len(panels)}"

    def test_has_appearance_panel(self, src):
        assert '"appearance"' in src and "build_appearance" in src

    def test_has_display_panel(self, src):
        assert '"display"' in src and "build_display" in src

    def test_has_sound_panel(self, src):
        assert '"sound"' in src and "build_sound" in src

    def test_has_network_panel(self, src):
        assert '"network"' in src

    def test_has_bluetooth_panel(self, src):
        assert '"bluetooth"' in src

    def test_has_battery_panel(self, src):
        assert '"battery"' in src

    def test_has_xii_mode_panel(self, src):
        assert '"xii-mode"' in src and "build_xii_mode" in src

    def test_xii_mode_panel_reads_current_mode(self, src):
        assert "XII_MODE_FILE" in src or "current-mode" in src, \
            "XII Mode panel should read current mode from file"

    def test_xii_mode_has_all_three_modes(self, src):
        assert '"lite"' in src
        assert '"standard"' in src
        assert '"performance"' in src

    def test_has_keyboard_panel(self, src):
        assert '"keyboard"' in src

    def test_has_about_panel(self, src):
        assert '"about"' in src and "build_about" in src

    def test_about_shows_version(self, src):
        assert "Genesis" in src or "version" in src.lower()

    def test_about_shows_system_info(self, src):
        assert "uname" in src or "MemTotal" in src or "_get_memory_info" in src

    def test_has_navigation_split_view(self, src):
        assert "NavigationSplitView" in src or "Adw.NavigationSplitView" in src, \
            "Settings must use NavigationSplitView for sidebar layout"

    def test_has_preferences_page(self, src):
        assert "Adw.PreferencesPage" in src

    def test_has_preferences_group(self, src):
        assert "Adw.PreferencesGroup" in src or "_group" in src

    def test_has_switch_row(self, src):
        assert "Adw.SwitchRow" in src or "_switch_row" in src

    def test_has_combo_row(self, src):
        assert "Adw.ComboRow" in src or "_combo_row" in src

    def test_has_panel_arg(self, src):
        assert "--panel" in src, "Settings must accept --panel CLI argument"

    def test_has_settings_window_class(self, src):
        assert "class SettingsWindow" in src

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_css_exists(self, settings_dir):
        assert (settings_dir / "xii-settings.css").is_file()

    def test_service_exists(self, settings_dir):
        assert (settings_dir / "xii-settings.service").is_file()


# ─────────────────────────────────────────────────────────────
# 5. XII Settings — CSS
# ─────────────────────────────────────────────────────────────
class TestSettingsCss:
    @pytest.fixture
    def css(self, settings_dir) -> str:
        path = settings_dir / "xii-settings.css"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_has_window_style(self, css):
        assert ".settings-window" in css

    def test_has_sidebar_list_style(self, css):
        assert ".settings-sidebar-list" in css

    def test_sidebar_selected_uses_cyan(self, css):
        assert "6ee7f7" in css

    def test_has_sidebar_icon_style(self, css):
        assert ".settings-sidebar-icon" in css

    def test_has_sidebar_label_style(self, css):
        assert ".settings-sidebar-label" in css

    def test_has_about_styles(self, css):
        assert ".about-name" in css or ".about-logo" in css

    def test_about_name_has_gradient(self, css):
        assert ".about-name" in css and "gradient" in css

    def test_has_wallpaper_preview(self, css):
        assert ".wallpaper-preview" in css


# ─────────────────────────────────────────────────────────────
# 6. XII Settings — Service
# ─────────────────────────────────────────────────────────────
class TestSettingsService:
    @pytest.fixture
    def service(self, settings_dir) -> str:
        path = settings_dir / "xii-settings.service"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_service_exists(self, settings_dir):
        assert (settings_dir / "xii-settings.service").is_file()

    def test_has_description(self, service):
        assert "Description=" in service

    def test_restarts_on_failure(self, service):
        assert "Restart=on-failure" in service

    def test_has_wayland_env(self, service):
        assert "WAYLAND_DISPLAY" in service
