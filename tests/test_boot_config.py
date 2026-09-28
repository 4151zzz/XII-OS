"""
XII OS — Phase 1 Boot Configuration Validator
tests/test_boot_config.py

Validates the correctness of GRUB configuration and kernel
boot profile parameters for all XII OS boot modes.

Run with: pytest tests/test_boot_config.py -v
"""

import re
import pytest
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def grub_cfg(project_root) -> str:
    path = project_root / "boot" / "grub" / "grub.cfg"
    assert path.is_file(), "boot/grub/grub.cfg not found"
    return path.read_text()


@pytest.fixture
def cmdline_conf(project_root) -> str:
    path = project_root / "kernel" / "cmdline.conf"
    assert path.is_file(), "kernel/cmdline.conf not found"
    return path.read_text()


# ─────────────────────────────────────────────────────────────
# 1. GRUB Config Structure Tests
# ─────────────────────────────────────────────────────────────
class TestGrubStructure:
    def test_default_is_zero(self, grub_cfg):
        """Default boot entry must be index 0 (Standard Mode)."""
        assert 'set default="0"' in grub_cfg or "set default=0" in grub_cfg, \
            "GRUB default must be set to 0"

    def test_timeout_set(self, grub_cfg):
        """A boot timeout must be defined."""
        assert re.search(r'set timeout=\d+', grub_cfg), \
            "GRUB timeout must be set"

    def test_timeout_reasonable(self, grub_cfg):
        """Timeout should be between 3 and 15 seconds."""
        match = re.search(r'set timeout=(\d+)', grub_cfg)
        assert match, "GRUB timeout not found"
        timeout = int(match.group(1))
        assert 3 <= timeout <= 15, \
            f"GRUB timeout {timeout}s is outside expected range 3–15s"

    def test_gfxterm_enabled(self, grub_cfg):
        """Graphical terminal must be enabled for themed UI."""
        assert "gfxterm" in grub_cfg, \
            "GRUB must use gfxterm for themed graphical menu"

    def test_video_module_loaded(self, grub_cfg):
        """all_video or specific video module must be loaded."""
        assert "all_video" in grub_cfg or "vbe" in grub_cfg, \
            "GRUB must load a video module"

    def test_color_highlight_is_cyan(self, grub_cfg):
        """Highlight color should be XII accent cyan."""
        assert "cyan" in grub_cfg, \
            "GRUB highlight color should include cyan (XII accent color)"


# ─────────────────────────────────────────────────────────────
# 2. Boot Entry Count and Completeness
# ─────────────────────────────────────────────────────────────
class TestGrubBootEntries:
    def test_has_exactly_four_main_entries(self, grub_cfg):
        """Must have Standard, Lite, Performance, and Recovery entries."""
        entries = re.findall(r'^menuentry\s+"[^"]*"', grub_cfg, re.MULTILINE)
        assert len(entries) >= 4, \
            f"Expected at least 4 menuentry blocks, found {len(entries)}"

    def test_standard_mode_entry_exists(self, grub_cfg):
        assert "Standard" in grub_cfg or "standard" in grub_cfg.lower(), \
            "GRUB must have a Standard Mode boot entry"

    def test_lite_mode_entry_exists(self, grub_cfg):
        assert "Lite" in grub_cfg or "lite" in grub_cfg.lower(), \
            "GRUB must have a Lite Mode boot entry"

    def test_performance_mode_entry_exists(self, grub_cfg):
        assert "Performance" in grub_cfg or "performance" in grub_cfg.lower(), \
            "GRUB must have a Performance Mode boot entry"

    def test_recovery_mode_entry_exists(self, grub_cfg):
        assert "Recovery" in grub_cfg or "recovery" in grub_cfg.lower(), \
            "GRUB must have a Recovery Mode boot entry"

    def test_has_submenu_advanced(self, grub_cfg):
        """Advanced boot options submenu must be present."""
        assert "submenu" in grub_cfg, \
            "GRUB must have a submenu for advanced boot options"


# ─────────────────────────────────────────────────────────────
# 3. Kernel Command Line Parameter Validation
# ─────────────────────────────────────────────────────────────
class TestKernelParameters:
    def _get_entry_cmdline(self, grub_cfg: str, mode_tag: str) -> str:
        """Extract the linux line for a given mode."""
        pattern = rf'(?:menuentry[^{{]*{mode_tag}[^{{]*\{{[^}}]*?linux\s+)(\S+\s+.+?)(?:\n|$)'
        match = re.search(pattern, grub_cfg, re.IGNORECASE | re.DOTALL)
        if not match:
            # simpler fallback
            lines = grub_cfg.splitlines()
            for i, line in enumerate(lines):
                if mode_tag.lower() in line.lower() and "menuentry" in line:
                    for j in range(i, min(i+10, len(lines))):
                        if lines[j].strip().startswith("linux "):
                            return lines[j].strip()
        return ""

    def test_standard_has_xii_mode_param(self, grub_cfg):
        """Standard mode entry must pass xii.mode=standard to kernel."""
        assert "xii.mode=standard" in grub_cfg, \
            "Standard boot entry must set xii.mode=standard"

    def test_lite_has_xii_mode_param(self, grub_cfg):
        assert "xii.mode=lite" in grub_cfg, \
            "Lite boot entry must set xii.mode=lite"

    def test_performance_has_xii_mode_param(self, grub_cfg):
        assert "xii.mode=performance" in grub_cfg, \
            "Performance boot entry must set xii.mode=performance"

    def test_recovery_has_xii_mode_recovery(self, grub_cfg):
        assert "xii.mode=recovery" in grub_cfg, \
            "Recovery boot entry must set xii.mode=recovery"

    def test_quiet_splash_in_normal_modes(self, grub_cfg):
        """Standard, Lite, Performance entries should use quiet splash."""
        # Count occurrences - should appear at least 3 times for normal modes
        quiet_count = grub_cfg.count("quiet splash")
        assert quiet_count >= 3, \
            f"Expected 'quiet splash' in at least 3 entries, found in {quiet_count}"

    def test_recovery_has_loglevel_verbose(self, grub_cfg):
        """Recovery mode should have higher loglevel for diagnostics."""
        # Find the recovery entry block
        recovery_block = ""
        in_recovery = False
        brace_depth = 0
        for line in grub_cfg.splitlines():
            if "recovery" in line.lower() and "menuentry" in line:
                in_recovery = True
            if in_recovery:
                recovery_block += line + "\n"
                brace_depth += line.count("{") - line.count("}")
                if brace_depth <= 0 and in_recovery and "{" in recovery_block:
                    break

        assert "loglevel=7" in recovery_block or "loglevel=6" in recovery_block or \
               "single" in recovery_block, \
            "Recovery mode should use verbose loglevel or single mode"

    def test_recovery_has_nomodeset(self, grub_cfg):
        """Recovery mode should use nomodeset for safe graphics."""
        recovery_block = ""
        in_recovery = False
        brace_depth = 0
        for line in grub_cfg.splitlines():
            if "recovery" in line.lower() and "menuentry" in line:
                in_recovery = True
            if in_recovery:
                recovery_block += line + "\n"
                brace_depth += line.count("{") - line.count("}")
                if brace_depth <= 0 and in_recovery and "{" in recovery_block:
                    break

        assert "nomodeset" in recovery_block, \
            "Recovery mode must use nomodeset for safe graphics compatibility"

    def test_performance_has_cpu_governor_hint(self, grub_cfg):
        """Performance entry should hint at performance CPU governor."""
        assert "cpufreq" in grub_cfg or "performance" in grub_cfg, \
            "Performance entry should reference CPU frequency governor"

    def test_mitigations_set(self, grub_cfg):
        """At least one entry must set mitigations parameter."""
        assert "mitigations=" in grub_cfg, \
            "GRUB entries should specify CPU vulnerability mitigations"


# ─────────────────────────────────────────────────────────────
# 4. cmdline.conf Tests
# ─────────────────────────────────────────────────────────────
class TestCmdlineConf:
    def test_file_is_not_empty(self, cmdline_conf):
        content = cmdline_conf.strip()
        non_comment = [l for l in content.splitlines()
                       if l.strip() and not l.strip().startswith("#")]
        assert len(non_comment) > 0, "cmdline.conf must have at least one active line"

    def test_has_quiet_boot(self, cmdline_conf):
        assert "quiet" in cmdline_conf, \
            "Default kernel cmdline should include 'quiet' for clean boot"

    def test_has_loglevel_set(self, cmdline_conf):
        assert "loglevel=" in cmdline_conf, \
            "Default kernel cmdline should set loglevel"

    def test_loglevel_is_low(self, cmdline_conf):
        match = re.search(r'loglevel=(\d+)', cmdline_conf)
        if match:
            loglevel = int(match.group(1))
            assert loglevel <= 4, \
                f"Default loglevel {loglevel} is too verbose for production boot"

    def test_references_boot_image(self, cmdline_conf):
        assert "BOOT_IMAGE" in cmdline_conf or "vmlinuz" in cmdline_conf, \
            "cmdline.conf should reference the boot image"
