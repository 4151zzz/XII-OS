"""
XII OS — Phase 10 Live Installer & Hybrid ISO Tests
tests/test_installer_iso.py

Validates:
  - installer_backend.py (Disk discovery, validation, simulation)
  - xii-installer.py (GTK4 Wizard, step handling)
  - installer styling and desktop launcher
  - verify-iso.py tool
  - build-iso.sh script properties

Run with: python -m pytest tests/test_installer_iso.py -v
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
def installer_dir(project_root) -> Path:
    return project_root / "installer"

@pytest.fixture
def scripts_dir(project_root) -> Path:
    return project_root / "scripts"


# ─────────────────────────────────────────────────────────────
# 1. File Structure Checks
# ─────────────────────────────────────────────────────────────
class TestInstallerFiles:
    def test_backend_exists(self, installer_dir):
        assert (installer_dir / "installer_backend.py").is_file()

    def test_gui_exists(self, installer_dir):
        assert (installer_dir / "xii-installer.py").is_file()

    def test_css_exists(self, installer_dir):
        assert (installer_dir / "xii-installer.css").is_file()

    def test_desktop_file_exists(self, installer_dir):
        assert (installer_dir / "xii-installer.desktop").is_file()

    def test_verify_iso_exists(self, scripts_dir):
        assert (scripts_dir / "verify-iso.py").is_file()

    def test_build_iso_exists(self, scripts_dir):
        assert (scripts_dir / "build-iso.sh").is_file()


# ─────────────────────────────────────────────────────────────
# 2. Installer Backend AST & Functionality
# ─────────────────────────────────────────────────────────────
class TestInstallerBackend:
    @pytest.fixture
    def backend_mod(self, installer_dir):
        import importlib.util
        spec = importlib.util.spec_from_file_location("installer_backend", installer_dir / "installer_backend.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_ast_classes(self, installer_dir):
        code = (installer_dir / "installer_backend.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "DiskDevice" in classes
        assert "InstallerBackend" in classes

    def test_disk_discovery(self, backend_mod):
        backend = backend_mod.InstallerBackend()
        disks = backend.list_disks()
        assert len(disks) >= 1
        assert isinstance(disks[0], backend_mod.DiskDevice)
        assert disks[0].size_gb > 0

    def test_config_validation(self, backend_mod):
        backend = backend_mod.InstallerBackend()
        # Missing disk
        res = backend.validate_configuration()
        assert res["valid"] is False

        # Set disk and credentials
        backend.target_disk = backend.list_disks()[0]
        backend.username = "testuser"
        backend.password = "secret"
        backend.hostname = "my-xii"
        res = backend.validate_configuration()
        assert res["valid"] is True

    def test_simulation_progress(self, backend_mod):
        backend = backend_mod.InstallerBackend()
        progress_records = []
        def on_prog(pct, msg):
            progress_records.append((pct, msg))

        ok = backend.simulate_install(progress_callback=on_prog)
        assert ok is True
        assert len(progress_records) >= 5
        assert progress_records[-1][0] == 100


# ─────────────────────────────────────────────────────────────
# 3. GUI Installer AST & Config
# ─────────────────────────────────────────────────────────────
class TestInstallerGUI:
    @pytest.fixture
    def tree(self, installer_dir) -> ast.AST:
        code = (installer_dir / "xii-installer.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_gui_classes(self, tree):
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "XIIInstallerApp" in classes
        assert "XIIInstallerWindow" in classes

    def test_desktop_file_content(self, installer_dir):
        df = (installer_dir / "xii-installer.desktop").read_text(encoding="utf-8")
        assert "[Desktop Entry]" in df
        assert "Name=Install XII OS 1.0" in df
        assert "Exec=" in df

    def test_css_classes(self, installer_dir):
        css = (installer_dir / "xii-installer.css").read_text(encoding="utf-8")
        assert ".installer-hero" in css
        assert ".btn-primary" in css
        assert ".progress-bar-custom" in css


# ─────────────────────────────────────────────────────────────
# 4. ISO Verification & Build Script Checks
# ─────────────────────────────────────────────────────────────
class TestISOScripts:
    def test_verify_iso_ast(self, scripts_dir):
        code = (scripts_dir / "verify-iso.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "verify_iso" in funcs

    def test_build_iso_content(self, scripts_dir):
        sh = (scripts_dir / "build-iso.sh").read_text(encoding="utf-8")
        assert "xorriso" in sh
        assert "grub-efi" in sh or "UEFI" in sh
        assert "mksquashfs" in sh or "SQUASH" in sh
