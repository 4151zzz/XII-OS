"""
XII OS — Phase 7 Security Center Tests
tests/test_security.py

Validates:
  - xii-security.py CLI daemon & scanner
  - xii-security.service systemd unit
  - nftables.conf ruleset & least privilege
  - AppArmor sandbox profile
  - xii-security-center.py GUI application
  - xii-security-center.css stylesheet
  - xii-security-center.desktop entry & service

Run with: python -m pytest tests/test_security.py -v
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
def security_sys_dir(project_root) -> Path:
    return project_root / "system" / "security"

@pytest.fixture
def security_desk_dir(project_root) -> Path:
    return project_root / "desktop" / "security"


# ─────────────────────────────────────────────────────────────
# 1. File Structure Checks
# ─────────────────────────────────────────────────────────────
class TestSecurityFiles:
    def test_daemon_script_exists(self, security_sys_dir):
        assert (security_sys_dir / "xii-security.py").is_file()

    def test_daemon_service_exists(self, security_sys_dir):
        assert (security_sys_dir / "xii-security.service").is_file()

    def test_nftables_conf_exists(self, security_sys_dir):
        assert (security_sys_dir / "nftables.conf").is_file()

    def test_apparmor_profile_exists(self, security_sys_dir):
        profile = security_sys_dir / "apparmor" / "usr.bin.xii-apps"
        assert profile.is_file()

    def test_gui_script_exists(self, security_desk_dir):
        assert (security_desk_dir / "xii-security-center.py").is_file()

    def test_gui_css_exists(self, security_desk_dir):
        assert (security_desk_dir / "xii-security-center.css").is_file()

    def test_gui_desktop_exists(self, security_desk_dir):
        assert (security_desk_dir / "xii-security-center.desktop").is_file()

    def test_gui_service_exists(self, security_desk_dir):
        assert (security_desk_dir / "xii-security-center.service").is_file()


# ─────────────────────────────────────────────────────────────
# 2. Daemon Script AST & Class Validation
# ─────────────────────────────────────────────────────────────
class TestDaemonAST:
    @pytest.fixture
    def tree(self, security_sys_dir) -> ast.AST:
        code = (security_sys_dir / "xii-security.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_classes_exist(self, tree):
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        expected = [
            "Finding",
            "FirewallMonitor",
            "IntegrityChecker",
            "PermissionAuditor",
            "LoginMonitor",
            "AppArmorChecker",
            "XIISecurityScanner",
        ]
        for exp in expected:
            assert exp in classes, f"Class {exp} missing in xii-security.py"

    def test_scanner_methods(self, tree):
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "XIISecurityScanner":
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
        assert "full_scan" in methods
        assert "write_report" in methods
        assert "notify_critical" in methods

    def test_integrity_methods(self, tree):
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "IntegrityChecker":
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
        assert "create_baseline" in methods
        assert "check" in methods


# ─────────────────────────────────────────────────────────────
# 3. Firewall Ruleset Validation
# ─────────────────────────────────────────────────────────────
class TestFirewallConfig:
    @pytest.fixture
    def nft_text(self, security_sys_dir) -> str:
        return (security_sys_dir / "nftables.conf").read_text(encoding="utf-8")

    def test_table_definition(self, nft_text):
        assert "table inet xii_filter" in nft_text

    def test_inbound_chain_drop_policy(self, nft_text):
        assert "chain inbound" in nft_text
        assert "policy drop" in nft_text

    def test_loopback_allowed(self, nft_text):
        assert 'iifname "lo" accept' in nft_text

    def test_established_allowed(self, nft_text):
        assert "ct state established,related accept" in nft_text

    def test_forward_chain_dropped(self, nft_text):
        assert "chain forward" in nft_text
        assert "policy drop" in nft_text


# ─────────────────────────────────────────────────────────────
# 4. AppArmor Profile Validation
# ─────────────────────────────────────────────────────────────
class TestAppArmorProfile:
    @pytest.fixture
    def profile_text(self, security_sys_dir) -> str:
        path = security_sys_dir / "apparmor" / "usr.bin.xii-apps"
        return path.read_text(encoding="utf-8")

    def test_denies_shadow_access(self, profile_text):
        assert "deny /etc/shadow" in profile_text

    def test_denies_sudoers_access(self, profile_text):
        assert "deny /etc/sudoers" in profile_text

    def test_allows_wayland_pipewire(self, profile_text):
        assert "wayland-*" in profile_text
        assert "pipewire-*" in profile_text


# ─────────────────────────────────────────────────────────────
# 5. GUI Application AST & Components
# ─────────────────────────────────────────────────────────────
class TestSecurityCenterGUI:
    @pytest.fixture
    def tree(self, security_desk_dir) -> ast.AST:
        code = (security_desk_dir / "xii-security-center.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_gui_classes_exist(self, tree):
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "SecurityDataBackend" in classes
        assert "XIISecurityCenterApp" in classes
        assert "XIISecurityWindow" in classes

    def test_backend_methods(self, tree):
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "SecurityDataBackend":
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
        assert "run_scan" in methods
        assert "get_firewall_status" in methods
        assert "toggle_firewall" in methods
        assert "update_integrity_baseline" in methods

    def test_css_content(self, security_desk_dir):
        css = (security_desk_dir / "xii-security-center.css").read_text(encoding="utf-8")
        assert ".security-score-card" in css
        assert ".finding-critical" in css
        assert ".btn-scan" in css

    def test_desktop_file_content(self, security_desk_dir):
        df = (security_desk_dir / "xii-security-center.desktop").read_text(encoding="utf-8")
        assert "[Desktop Entry]" in df
        assert "Name=XII Security Center" in df
        assert "Exec=" in df
        assert "Categories=" in df
