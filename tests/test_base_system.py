"""
XII OS — Phase 1 Base System Automated Tests
tests/test_base_system.py

Tests the structure and correctness of all XII OS Phase 1 system files:
  - os-release identification
  - XII OS version file
  - xii-mode CLI completeness
  - sysctl configuration values
  - systemd service units
  - ZRAM configuration
  - base-packages.txt manifest

Run with: pytest tests/test_base_system.py -v
"""

import os
import re
import stat
import pytest
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def project_root() -> Path:
    """Returns the XII OS project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def system_dir(project_root) -> Path:
    return project_root / "system"


@pytest.fixture
def kernel_dir(project_root) -> Path:
    return project_root / "kernel"


@pytest.fixture
def build_dir(project_root) -> Path:
    return project_root / "build"


@pytest.fixture
def scripts_dir(project_root) -> Path:
    return project_root / "scripts"


# ─────────────────────────────────────────────────────────────
# 1. os-release Tests
# ─────────────────────────────────────────────────────────────
class TestOsRelease:
    def test_file_exists(self, system_dir):
        """os-release file must exist."""
        assert (system_dir / "os-release").is_file(), \
            "system/os-release is missing"

    def test_required_fields(self, system_dir):
        """os-release must contain all required fields."""
        content = (system_dir / "os-release").read_text()
        required_fields = ["NAME", "PRETTY_NAME", "ID", "VERSION", "VERSION_ID",
                           "VERSION_CODENAME", "HOME_URL"]
        for field in required_fields:
            assert f"{field}=" in content, f"os-release missing field: {field}"

    def test_name_is_xii_os(self, system_dir):
        """NAME must be 'XII OS'."""
        content = (system_dir / "os-release").read_text()
        assert 'NAME="XII OS"' in content, "os-release NAME is not 'XII OS'"

    def test_id_is_lowercase_with_hyphen(self, system_dir):
        """ID must be lowercase 'xii-os'."""
        content = (system_dir / "os-release").read_text()
        assert "ID=xii-os" in content, "os-release ID must be 'xii-os'"

    def test_id_like_is_debian(self, system_dir):
        """ID_LIKE must reference debian."""
        content = (system_dir / "os-release").read_text()
        assert "debian" in content.lower(), \
            "os-release ID_LIKE should reference 'debian'"

    def test_version_codename_is_genesis(self, system_dir):
        """Version codename must be 'genesis' (Phase 1 release name)."""
        content = (system_dir / "os-release").read_text()
        assert "genesis" in content.lower(), \
            "os-release VERSION_CODENAME should be 'genesis'"


# ─────────────────────────────────────────────────────────────
# 2. sysctl Configuration Tests
# ─────────────────────────────────────────────────────────────
class TestSysctlConfig:
    @pytest.fixture
    def sysctl_conf(self, kernel_dir) -> str:
        path = kernel_dir / "sysctl.d" / "99-xii-performance.conf"
        assert path.is_file(), "sysctl config not found"
        return path.read_text()

    def test_file_exists(self, kernel_dir):
        assert (kernel_dir / "sysctl.d" / "99-xii-performance.conf").is_file()

    def test_swappiness_is_low(self, sysctl_conf):
        """vm.swappiness must be ≤ 20 for desktop responsiveness."""
        match = re.search(r'vm\.swappiness\s*=\s*(\d+)', sysctl_conf)
        assert match, "vm.swappiness not found in sysctl config"
        value = int(match.group(1))
        assert value <= 20, f"vm.swappiness should be ≤ 20 for desktop use, got {value}"

    def test_dirty_ratio_set(self, sysctl_conf):
        """vm.dirty_ratio must be set."""
        assert "vm.dirty_ratio" in sysctl_conf, "vm.dirty_ratio not found"

    def test_dirty_background_ratio_set(self, sysctl_conf):
        """vm.dirty_background_ratio must be set."""
        assert "vm.dirty_background_ratio" in sysctl_conf, \
            "vm.dirty_background_ratio not found"

    def test_inotify_watches_large_enough(self, sysctl_conf):
        """fs.inotify.max_user_watches must be ≥ 262144."""
        match = re.search(r'fs\.inotify\.max_user_watches\s*=\s*(\d+)', sysctl_conf)
        assert match, "fs.inotify.max_user_watches not found"
        value = int(match.group(1))
        assert value >= 262144, \
            f"fs.inotify.max_user_watches should be ≥ 262144, got {value}"

    def test_vfs_cache_pressure_set(self, sysctl_conf):
        """vm.vfs_cache_pressure must be set."""
        assert "vm.vfs_cache_pressure" in sysctl_conf, \
            "vm.vfs_cache_pressure not found"


# ─────────────────────────────────────────────────────────────
# 3. xii-mode CLI Tests
# ─────────────────────────────────────────────────────────────
class TestXiiModeCli:
    @pytest.fixture
    def xii_mode_path(self, system_dir) -> Path:
        path = system_dir / "services" / "xii-mode"
        assert path.is_file(), "xii-mode CLI not found"
        return path

    @pytest.fixture
    def xii_mode_content(self, xii_mode_path) -> str:
        return xii_mode_path.read_text()

    def test_file_exists(self, xii_mode_path):
        assert xii_mode_path.is_file()

    def test_has_bash_shebang(self, xii_mode_content):
        """Script must start with a bash shebang."""
        assert xii_mode_content.startswith("#!/usr/bin/env bash") or \
               xii_mode_content.startswith("#!/bin/bash"), \
               "xii-mode must have a bash shebang"

    def test_supports_get_command(self, xii_mode_content):
        assert "get)" in xii_mode_content or "cmd_get" in xii_mode_content, \
            "xii-mode must implement 'get' command"

    def test_supports_set_command(self, xii_mode_content):
        assert "set)" in xii_mode_content or "cmd_set" in xii_mode_content, \
            "xii-mode must implement 'set' command"

    def test_supports_list_command(self, xii_mode_content):
        assert "list)" in xii_mode_content or "cmd_list" in xii_mode_content, \
            "xii-mode must implement 'list' command"

    def test_supports_status_command(self, xii_mode_content):
        assert "status)" in xii_mode_content or "cmd_status" in xii_mode_content, \
            "xii-mode must implement 'status' command"

    def test_validates_all_three_modes(self, xii_mode_content):
        """Script must recognize all 3 valid modes."""
        for mode in ["lite", "standard", "performance"]:
            assert mode in xii_mode_content, \
                f"xii-mode must handle mode: '{mode}'"

    def test_requires_root_for_set(self, xii_mode_content):
        """Setting mode must require root (EUID check)."""
        assert "EUID" in xii_mode_content, \
            "xii-mode must check EUID before applying mode changes"

    def test_mode_file_path_defined(self, xii_mode_content):
        """XII_MODE_FILE variable must be set."""
        assert "XII_MODE_FILE" in xii_mode_content, \
            "xii-mode must define XII_MODE_FILE path"

    def test_dbus_notification_present(self, xii_mode_content):
        """D-Bus notification should be sent on mode change."""
        assert "dbus-send" in xii_mode_content, \
            "xii-mode should send D-Bus signal on mode change"


# ─────────────────────────────────────────────────────────────
# 4. systemd Service Unit Tests
# ─────────────────────────────────────────────────────────────
class TestSystemdServices:
    def _read_unit(self, system_dir: Path, name: str) -> str:
        path = system_dir / "services" / name
        assert path.is_file(), f"Service unit not found: {name}"
        return path.read_text()

    def test_xii_init_service_exists(self, system_dir):
        assert (system_dir / "services" / "xii-init.service").is_file()

    def test_xii_mode_service_exists(self, system_dir):
        assert (system_dir / "services" / "xii-mode.service").is_file()

    def test_xii_init_has_unit_section(self, system_dir):
        content = self._read_unit(system_dir, "xii-init.service")
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content

    def test_xii_init_type_is_oneshot(self, system_dir):
        content = self._read_unit(system_dir, "xii-init.service")
        assert "Type=oneshot" in content, \
            "xii-init.service should be Type=oneshot"

    def test_xii_init_wanted_by_multi_user(self, system_dir):
        content = self._read_unit(system_dir, "xii-init.service")
        assert "multi-user.target" in content

    def test_xii_mode_service_exec_xii_mode(self, system_dir):
        content = self._read_unit(system_dir, "xii-mode.service")
        assert "xii-mode" in content, \
            "xii-mode.service must call the xii-mode tool"

    def test_xii_mode_service_reads_cmdline(self, system_dir):
        content = self._read_unit(system_dir, "xii-mode.service")
        assert "cmdline" in content or "xii.mode" in content, \
            "xii-mode.service should read kernel cmdline for mode"


# ─────────────────────────────────────────────────────────────
# 5. Build Manifest Tests
# ─────────────────────────────────────────────────────────────
class TestBasePackages:
    @pytest.fixture
    def manifest_content(self, build_dir) -> str:
        path = build_dir / "manifests" / "base-packages.txt"
        assert path.is_file(), "base-packages.txt not found"
        return path.read_text(encoding="utf-8")

    def test_manifest_exists(self, build_dir):
        assert (build_dir / "manifests" / "base-packages.txt").is_file()

    def test_essential_packages_present(self, manifest_content):
        """Critical packages must be in manifest."""
        essential = [
            "linux-image-amd64", "systemd", "grub-efi-amd64",
            "bash", "coreutils", "sudo", "iproute2",
            "zram-tools", "python3"
        ]
        packages = [
            line.strip() for line in manifest_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        for pkg in essential:
            assert pkg in packages, f"Essential package missing from manifest: {pkg}"

    def test_no_duplicate_packages(self, manifest_content):
        """Manifest must not contain duplicate package entries."""
        packages = [
            line.strip() for line in manifest_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        duplicates = [p for p in packages if packages.count(p) > 1]
        assert len(duplicates) == 0, f"Duplicate packages in manifest: {set(duplicates)}"

    def test_package_names_are_valid(self, manifest_content):
        """Package names must follow valid dpkg naming (lowercase, alphanumeric+hyphens)."""
        packages = [
            line.strip() for line in manifest_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        invalid = [p for p in packages if not re.match(r'^[a-z0-9][a-z0-9+.\-]+$', p)]
        assert len(invalid) == 0, f"Invalid package names in manifest: {invalid}"


# ─────────────────────────────────────────────────────────────
# 6. Script Files Tests
# ─────────────────────────────────────────────────────────────
class TestScriptFiles:
    def test_bootstrap_script_exists(self, scripts_dir):
        assert (scripts_dir / "bootstrap-base.sh").is_file()

    def test_build_iso_script_exists(self, scripts_dir):
        assert (scripts_dir / "build-iso.sh").is_file()

    def test_run_qemu_sh_exists(self, scripts_dir):
        assert (scripts_dir / "run-qemu.sh").is_file()

    def test_run_qemu_ps1_exists(self, scripts_dir):
        assert (scripts_dir / "run-qemu.ps1").is_file()

    def test_bootstrap_has_shebang(self, scripts_dir):
        content = (scripts_dir / "bootstrap-base.sh").read_text()
        assert content.startswith("#!/"), "bootstrap-base.sh must have a shebang"

    def test_build_iso_has_shebang(self, scripts_dir):
        content = (scripts_dir / "build-iso.sh").read_text()
        assert content.startswith("#!/"), "build-iso.sh must have a shebang"

    def test_run_qemu_has_shebang(self, scripts_dir):
        content = (scripts_dir / "run-qemu.sh").read_text()
        assert content.startswith("#!/"), "run-qemu.sh must have a shebang"

    def test_bootstrap_references_manifest(self, scripts_dir):
        content = (scripts_dir / "bootstrap-base.sh").read_text()
        assert "base-packages.txt" in content, \
            "bootstrap-base.sh must reference base-packages.txt"

    def test_build_iso_references_squashfs(self, scripts_dir):
        content = (scripts_dir / "build-iso.sh").read_text()
        assert "squashfs" in content.lower() or "mksquashfs" in content, \
            "build-iso.sh must use mksquashfs"

    def test_run_qemu_references_iso(self, scripts_dir):
        content = (scripts_dir / "run-qemu.sh").read_text()
        assert ".iso" in content, "run-qemu.sh must reference an ISO file"

    def test_ps1_runner_has_param_block(self, scripts_dir):
        content = (scripts_dir / "run-qemu.ps1").read_text()
        assert "param(" in content or "[CmdletBinding()]" in content, \
            "run-qemu.ps1 must have a PowerShell param block"


# ─────────────────────────────────────────────────────────────
# 7. Boot Configuration Tests
# ─────────────────────────────────────────────────────────────
class TestBootConfig:
    @pytest.fixture
    def boot_dir(self, project_root) -> Path:
        return project_root / "boot"

    def test_grub_cfg_exists(self, boot_dir):
        assert (boot_dir / "grub" / "grub.cfg").is_file()

    def test_grub_theme_exists(self, boot_dir):
        assert (boot_dir / "grub" / "xii-theme.txt").is_file()

    def test_boot_logo_exists(self, boot_dir):
        assert (boot_dir / "splash" / "xii-boot-logo.svg").is_file()

    def test_cmdline_conf_exists(self, project_root):
        assert (project_root / "kernel" / "cmdline.conf").is_file()
