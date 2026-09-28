"""
XII OS — Phase 8 Update & Recovery Tests
tests/test_update_recovery.py

Validates:
  - xii-snapshot.py SnapshotEngine
  - xii-update.py UpdateEngine
  - Systemd timer and service units
  - Recovery console script (xii-recovery.sh)
  - XII Updater GTK4 application & styles
  - Desktop entries & configurations

Run with: python -m pytest tests/test_update_recovery.py -v
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
def update_dir(project_root) -> Path:
    return project_root / "system" / "updates"

@pytest.fixture
def recovery_dir(project_root) -> Path:
    return project_root / "system" / "recovery"

@pytest.fixture
def desk_update_dir(project_root) -> Path:
    return project_root / "desktop" / "updates"


# ─────────────────────────────────────────────────────────────
# 1. File Structure Checks
# ─────────────────────────────────────────────────────────────
class TestUpdateRecoveryFiles:
    def test_snapshot_engine_exists(self, update_dir):
        assert (update_dir / "xii-snapshot.py").is_file()

    def test_update_engine_exists(self, update_dir):
        assert (update_dir / "xii-update.py").is_file()

    def test_update_service_exists(self, update_dir):
        assert (update_dir / "xii-update.service").is_file()

    def test_update_timer_exists(self, update_dir):
        assert (update_dir / "xii-update.timer").is_file()

    def test_recovery_script_exists(self, recovery_dir):
        assert (recovery_dir / "xii-recovery.sh").is_file()

    def test_gui_updater_exists(self, desk_update_dir):
        assert (desk_update_dir / "xii-updater.py").is_file()

    def test_gui_css_exists(self, desk_update_dir):
        assert (desk_update_dir / "xii-updater.css").is_file()

    def test_gui_desktop_exists(self, desk_update_dir):
        assert (desk_update_dir / "xii-updater.desktop").is_file()


# ─────────────────────────────────────────────────────────────
# 2. AST Validation: Snapshot & Update Engines
# ─────────────────────────────────────────────────────────────
class TestSnapshotUpdateAST:
    def test_snapshot_classes(self, update_dir):
        code = (update_dir / "xii-snapshot.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "SnapshotEngine" in classes

        methods = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and n.name == "SnapshotEngine":
                methods = [m.name for m in n.body if isinstance(m, ast.FunctionDef)]
        assert "create" in methods
        assert "list_snapshots" in methods
        assert "delete" in methods
        assert "restore" in methods
        assert "prune" in methods

    def test_update_classes(self, update_dir):
        code = (update_dir / "xii-update.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "UpdateEngine" in classes

        methods = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and n.name == "UpdateEngine":
                methods = [m.name for m in n.body if isinstance(m, ast.FunctionDef)]
        assert "check_updates" in methods
        assert "perform_upgrade" in methods


# ─────────────────────────────────────────────────────────────
# 3. Snapshot Engine Functionality (using tempdir)
# ─────────────────────────────────────────────────────────────
class TestSnapshotFunctionality:
    def test_create_and_prune_snapshot(self, tmp_path, monkeypatch):
        import sys
        sys.path.insert(0, str(tmp_path))

        # Import dynamically
        spec_path = Path(__file__).resolve().parent.parent / "system" / "updates" / "xii-snapshot.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("xii_snapshot", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        engine = mod.SnapshotEngine(storage_dir=tmp_path / "snaps")
        s1 = engine.create("First snap", tag="manual")
        s2 = engine.create("Second snap", tag="pre-update")
        s3 = engine.create("Third snap", tag="manual")

        snaps = engine.list_snapshots()
        assert len(snaps) == 3

        pruned = engine.prune(keep=2)
        assert pruned == 1
        assert len(engine.list_snapshots()) == 2


# ─────────────────────────────────────────────────────────────
# 4. Recovery Console Script Tests
# ─────────────────────────────────────────────────────────────
class TestRecoveryScript:
    @pytest.fixture
    def script_content(self, recovery_dir) -> str:
        return (recovery_dir / "xii-recovery.sh").read_text(encoding="utf-8")

    def test_has_shebang(self, script_content):
        assert script_content.startswith("#!/bin/bash")

    def test_has_rollback_function(self, script_content):
        assert "do_snapshot_rollback" in script_content

    def test_has_fsck_function(self, script_content):
        assert "do_fsck" in script_content

    def test_has_grub_repair(self, script_content):
        assert "do_repair_grub" in script_content

    def test_has_password_reset(self, script_content):
        assert "do_reset_password" in script_content


# ─────────────────────────────────────────────────────────────
# 5. Updater GUI Application AST & Config
# ─────────────────────────────────────────────────────────────
class TestUpdaterGUI:
    @pytest.fixture
    def tree(self, desk_update_dir) -> ast.AST:
        code = (desk_update_dir / "xii-updater.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_classes(self, tree):
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "UpdateDataBackend" in classes
        assert "XIIUpdaterApp" in classes
        assert "XIIUpdaterWindow" in classes

    def test_desktop_file(self, desk_update_dir):
        df = (desk_update_dir / "xii-updater.desktop").read_text(encoding="utf-8")
        assert "[Desktop Entry]" in df
        assert "Name=XII Software Update" in df
        assert "Exec=" in df

    def test_systemd_timer(self, update_dir):
        timer = (update_dir / "xii-update.timer").read_text(encoding="utf-8")
        assert "[Timer]" in timer
        assert "OnCalendar=daily" in timer
