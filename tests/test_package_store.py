"""
XII OS — Phase 6 Package Manager + XII Store Tests
tests/test_package_store.py

Validates:
  - xii.py CLI package manager (AptBackend, FlatpakBackend, XIIPackageManager)
  - xii-pkg-config.json
  - systemd service + timer
  - XII Store (xii-store.py)
  - XII Store CSS
  - featured-apps.json catalog

Run with: pytest tests/test_package_store.py -v
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
def pkg_dir(project_root) -> Path:
    return project_root / "system" / "package"

@pytest.fixture
def store_dir(project_root) -> Path:
    return project_root / "desktop" / "store"


# ─────────────────────────────────────────────────────────────
# 1. Package Manager Config
# ─────────────────────────────────────────────────────────────
class TestPkgConfig:
    @pytest.fixture
    def cfg(self, pkg_dir) -> dict:
        path = pkg_dir / "xii-pkg-config.json"
        assert path.is_file()
        return json.loads(path.read_text(encoding="utf-8"))

    def test_config_exists(self, pkg_dir):
        assert (pkg_dir / "xii-pkg-config.json").is_file()

    def test_has_meta(self, cfg):
        assert "meta" in cfg

    def test_has_backends(self, cfg):
        assert "backends" in cfg

    def test_has_apt_backend(self, cfg):
        assert "apt" in cfg["backends"]

    def test_has_flatpak_backend(self, cfg):
        assert "flatpak" in cfg["backends"]

    def test_has_appimage_backend(self, cfg):
        assert "appimage" in cfg["backends"]

    def test_flatpak_has_remotes(self, cfg):
        remotes = cfg["backends"]["flatpak"].get("remotes", [])
        assert len(remotes) >= 1, "Flatpak must have at least one remote"

    def test_flathub_remote_exists(self, cfg):
        remotes = cfg["backends"]["flatpak"].get("remotes", [])
        names = [r["name"] for r in remotes]
        assert "flathub" in names

    def test_has_update_config(self, cfg):
        assert "update" in cfg
        assert "auto_check" in cfg["update"]

    def test_has_security_config(self, cfg):
        assert "security" in cfg
        assert "verify_signatures" in cfg["security"]

    def test_signature_verification_enabled(self, cfg):
        assert cfg["security"]["verify_signatures"] is True

    def test_has_store_config(self, cfg):
        assert "store" in cfg
        assert "catalog_url" in cfg["store"]


# ─────────────────────────────────────────────────────────────
# 2. Package Manager CLI (xii.py)
# ─────────────────────────────────────────────────────────────
class TestPackageManagerCLI:
    @pytest.fixture
    def src(self, pkg_dir) -> str:
        path = pkg_dir / "xii.py"
        assert path.is_file(), "xii.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, pkg_dir):
        assert (pkg_dir / "xii.py").is_file()

    def test_has_shebang(self, src):
        assert src.startswith("#!/usr/bin/env python3")

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii.py syntax error: {e}")

    def test_has_apt_backend(self, src):
        assert "class AptBackend" in src

    def test_has_flatpak_backend(self, src):
        assert "class FlatpakBackend" in src

    def test_has_unified_manager(self, src):
        assert "class XIIPackageManager" in src

    def test_has_install_method(self, src):
        assert "def install" in src

    def test_has_remove_method(self, src):
        assert "def remove" in src

    def test_has_update_method(self, src):
        assert "def update" in src

    def test_has_upgrade_method(self, src):
        assert "def upgrade" in src

    def test_has_search_method(self, src):
        assert "def search" in src

    def test_has_list_method(self, src):
        assert "def list_packages" in src or "list_installed" in src

    def test_has_info_method(self, src):
        assert "def info" in src

    def test_has_clean_method(self, src):
        assert "def clean" in src

    def test_has_doctor_method(self, src):
        assert "def doctor" in src, "XII Package Manager must have a doctor/health-check command"

    def test_has_json_output(self, src):
        assert "json_output" in src or "--json" in src

    def test_has_colored_output(self, src):
        assert "CYAN" in src or "\033[" in src, "Package manager should use colored terminal output"

    def test_has_cli_subcommands(self, src):
        for cmd in ["install", "remove", "update", "upgrade", "search", "list", "info", "clean", "doctor"]:
            assert f'"{cmd}"' in src, f"Missing subcommand: {cmd}"

    def test_has_command_aliases(self, src):
        assert "aliases=" in src, "CLI should have command aliases (i, r, s, etc.)"

    def test_has_backend_flag(self, src):
        assert "--flatpak" in src and "--apt" in src, \
            "Install should support --flatpak and --apt flags"

    def test_has_logging(self, src):
        assert "_log" in src or "LOG_FILE" in src

    def test_has_banner(self, src):
        assert "print_banner" in src or "XII OS" in src

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_has_xii_package_class(self, src):
        assert "class XIIPackage" in src


# ─────────────────────────────────────────────────────────────
# 3. systemd Service + Timer
# ─────────────────────────────────────────────────────────────
class TestUpdateService:
    def test_service_exists(self, pkg_dir):
        assert (pkg_dir / "xii-update.service").is_file()

    def test_timer_exists(self, pkg_dir):
        assert (pkg_dir / "xii-update.timer").is_file()

    def test_service_is_oneshot(self, pkg_dir):
        content = (pkg_dir / "xii-update.service").read_text(encoding="utf-8")
        assert "Type=oneshot" in content

    def test_service_runs_update(self, pkg_dir):
        content = (pkg_dir / "xii-update.service").read_text(encoding="utf-8")
        assert "update" in content.lower()

    def test_service_requires_network(self, pkg_dir):
        content = (pkg_dir / "xii-update.service").read_text(encoding="utf-8")
        assert "network-online" in content

    def test_service_is_low_priority(self, pkg_dir):
        content = (pkg_dir / "xii-update.service").read_text(encoding="utf-8")
        assert "Nice=19" in content or "nice" in content.lower()

    def test_timer_is_daily(self, pkg_dir):
        content = (pkg_dir / "xii-update.timer").read_text(encoding="utf-8")
        assert "daily" in content.lower() or "OnCalendar" in content

    def test_timer_is_persistent(self, pkg_dir):
        content = (pkg_dir / "xii-update.timer").read_text(encoding="utf-8")
        assert "Persistent=true" in content


# ─────────────────────────────────────────────────────────────
# 4. Featured Apps Catalog
# ─────────────────────────────────────────────────────────────
class TestFeaturedCatalog:
    @pytest.fixture
    def catalog(self, store_dir) -> dict:
        path = store_dir / "featured-apps.json"
        assert path.is_file()
        return json.loads(path.read_text(encoding="utf-8"))

    def test_catalog_exists(self, store_dir):
        assert (store_dir / "featured-apps.json").is_file()

    def test_has_meta(self, catalog):
        assert "meta" in catalog

    def test_has_featured_list(self, catalog):
        assert "featured" in catalog
        assert isinstance(catalog["featured"], list)

    def test_has_minimum_5_apps(self, catalog):
        assert len(catalog["featured"]) >= 5, "Store must have at least 5 featured apps"

    def test_apps_have_required_fields(self, catalog):
        for app in catalog["featured"]:
            assert "id" in app,          f"App missing 'id': {app.get('name')}"
            assert "name" in app,        f"App missing 'name'"
            assert "description" in app, f"App missing 'description': {app.get('name')}"
            assert "icon" in app,        f"App missing 'icon': {app.get('name')}"
            assert "category" in app,    f"App missing 'category': {app.get('name')}"
            assert "backend" in app,     f"App missing 'backend': {app.get('name')}"

    def test_apps_have_ratings(self, catalog):
        for app in catalog["featured"]:
            assert "rating" in app, f"App missing rating: {app.get('name')}"
            assert 0 <= app["rating"] <= 5, f"Rating out of range: {app.get('name')}"

    def test_apps_have_verified_field(self, catalog):
        for app in catalog["featured"]:
            assert "xii_verified" in app

    def test_has_browser_app(self, catalog):
        names = [a["name"].lower() for a in catalog["featured"]]
        ids   = [a["id"].lower() for a in catalog["featured"]]
        assert any("firefox" in n for n in names) or any("firefox" in i for i in ids), \
            "Store should feature a browser"

    def test_has_categories_list(self, catalog):
        assert "categories" in catalog
        assert len(catalog["categories"]) >= 5

    def test_flatpak_apps_have_proper_ids(self, catalog):
        for app in catalog["featured"]:
            if app["backend"] == "flatpak":
                parts = app["id"].split(".")
                assert len(parts) >= 3, \
                    f"Flatpak ID '{app['id']}' should be reverse-domain format"


# ─────────────────────────────────────────────────────────────
# 5. XII Store App (Python)
# ─────────────────────────────────────────────────────────────
class TestStoreApp:
    @pytest.fixture
    def src(self, store_dir) -> str:
        path = store_dir / "xii-store.py"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, store_dir):
        assert (store_dir / "xii-store.py").is_file()

    def test_has_shebang(self, src):
        assert src.startswith("#!/usr/bin/env python3")

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii-store.py syntax error: {e}")

    def test_has_app_entry_class(self, src):
        assert "class AppEntry" in src

    def test_has_app_catalog_class(self, src):
        assert "class AppCatalog" in src

    def test_has_app_card_class(self, src):
        assert "class AppCard" in src

    def test_has_store_window_class(self, src):
        assert "class StoreWindow" in src

    def test_has_category_sidebar(self, src):
        assert "CATEGORIES" in src

    def test_has_minimum_categories(self, src):
        import re
        cats = re.findall(r'"([A-Za-z &]+)",\s+"[^"]+-symbolic"', src)
        assert len(cats) >= 5, f"Store needs ≥ 5 categories, found {len(cats)}"

    def test_has_search_functionality(self, src):
        assert "_on_search" in src or "search" in src.lower()

    def test_has_install_threading(self, src):
        assert "threading" in src, "Install must run in background thread"

    def test_has_flatpak_install(self, src):
        assert "flatpak" in src and "install" in src

    def test_has_navigation_split_view(self, src):
        assert "NavigationSplitView" in src

    def test_has_flow_box_grid(self, src):
        assert "FlowBox" in src

    def test_has_app_detail_dialog(self, src):
        assert "Adw.MessageDialog" in src or "dialog" in src.lower()

    def test_has_verified_badge(self, src):
        assert "xii_verified" in src or "verified" in src.lower()

    def test_has_rating_stars(self, src):
        assert "stars" in src and ("★" in src or "rating" in src.lower())

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_css_exists(self, store_dir):
        assert (store_dir / "xii-store.css").is_file()

    def test_service_exists(self, store_dir):
        assert (store_dir / "xii-store.service").is_file()


# ─────────────────────────────────────────────────────────────
# 6. XII Store CSS
# ─────────────────────────────────────────────────────────────
class TestStoreCss:
    @pytest.fixture
    def css(self, store_dir) -> str:
        return (store_dir / "xii-store.css").read_text(encoding="utf-8")

    def test_has_window_style(self, css):
        assert ".store-window" in css

    def test_has_card_style(self, css):
        assert ".store-card" in css

    def test_card_has_hover_effect(self, css):
        assert ".store-card:hover" in css
        assert "transform" in css

    def test_has_install_button_style(self, css):
        assert ".store-install-btn" in css

    def test_has_installed_button_style(self, css):
        assert ".store-installed-btn" in css

    def test_has_verified_badge_style(self, css):
        assert ".store-verified-badge" in css

    def test_verified_badge_uses_cyan(self, css):
        assert "6ee7f7" in css

    def test_has_stars_style(self, css):
        assert ".store-stars" in css

    def test_has_category_selected_style(self, css):
        assert ".store-cat-list > row:selected" in css or "row:selected" in css

    def test_category_selected_uses_cyan(self, css):
        assert "6ee7f7" in css
