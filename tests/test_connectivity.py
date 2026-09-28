"""
XII OS — Phase 5 Connectivity Tests
tests/test_connectivity.py

Validates all Phase 5 components:
  - Network daemon (xii-network.py)
  - NetworkManager configuration
  - Bluetooth manager (xii-bluetooth.py)
  - BlueZ configuration
  - PipeWire audio configuration
  - Audio control script (xii-audio.sh)
  - udev rules
  - Hardware hotplug script
  - systemd services

Run with: pytest tests/test_connectivity.py -v
"""

import ast
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
def network_dir(project_root) -> Path:
    return project_root / "system" / "network"

@pytest.fixture
def bluetooth_dir(project_root) -> Path:
    return project_root / "system" / "bluetooth"

@pytest.fixture
def audio_dir(project_root) -> Path:
    return project_root / "system" / "audio"

@pytest.fixture
def hardware_dir(project_root) -> Path:
    return project_root / "system" / "hardware"


# ─────────────────────────────────────────────────────────────
# 1. Network — Python Daemon
# ─────────────────────────────────────────────────────────────
class TestNetworkDaemon:
    @pytest.fixture
    def src(self, network_dir) -> str:
        path = network_dir / "xii-network.py"
        assert path.is_file(), "xii-network.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, network_dir):
        assert (network_dir / "xii-network.py").is_file()

    def test_has_shebang(self, src):
        assert src.startswith("#!/usr/bin/env python3")

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii-network.py syntax error: {e}")

    def test_has_nm_import(self, src):
        assert '"NM"' in src or "NM" in src

    def test_has_network_status_class(self, src):
        assert "class NetworkStatus" in src

    def test_has_get_state_method(self, src):
        assert "def get_state" in src

    def test_has_wifi_scan(self, src):
        assert "scan_wifi" in src or "scan" in src.lower()

    def test_has_wifi_connect(self, src):
        assert "connect_wifi" in src or "connect" in src.lower()

    def test_has_wifi_disconnect(self, src):
        assert "disconnect_wifi" in src or "disconnect" in src.lower()

    def test_has_state_file_writer(self, src):
        assert "write_state_file" in src or "network-state.json" in src

    def test_has_daemon_class(self, src):
        assert "class NetworkDaemon" in src or "daemon" in src.lower()

    def test_daemon_uses_nm_signals(self, src):
        assert "state-changed" in src or "connect(" in src

    def test_daemon_sends_notifications(self, src):
        assert "notify-send" in src

    def test_has_cli_subcommands(self, src):
        assert "subparsers" in src or "subp" in src

    def test_has_status_command(self, src):
        assert '"status"' in src

    def test_has_wifi_command(self, src):
        assert '"wifi"' in src

    def test_has_daemon_command(self, src):
        assert '"daemon"' in src

    def test_has_state_map(self, src):
        assert "NM_STATE_MAP" in src or "state_map" in src.lower()

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_service_exists(self, network_dir):
        assert (network_dir / "xii-network.service").is_file()

    def test_service_requires_nm(self, network_dir):
        content = (network_dir / "xii-network.service").read_text(encoding="utf-8")
        assert "NetworkManager" in content


# ─────────────────────────────────────────────────────────────
# 2. NetworkManager Config
# ─────────────────────────────────────────────────────────────
class TestNetworkManagerConf:
    @pytest.fixture
    def conf(self, network_dir) -> str:
        path = network_dir / "NetworkManager.conf"
        assert path.is_file(), "NetworkManager.conf not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, network_dir):
        assert (network_dir / "NetworkManager.conf").is_file()

    def test_has_main_section(self, conf):
        assert "[main]" in conf

    def test_uses_systemd_resolved(self, conf):
        assert "dns=systemd-resolved" in conf

    def test_has_wifi_mac_randomization(self, conf):
        assert "mac-address-randomization" in conf

    def test_uses_iwd_backend(self, conf):
        assert "iwd" in conf, "NM should use IWD as Wi-Fi backend"

    def test_has_connectivity_check(self, conf):
        assert "[connectivity]" in conf
        assert "uri=" in conf

    def test_has_device_section(self, conf):
        assert "[device]" in conf

    def test_has_keyfile_plugin(self, conf):
        assert "plugins=keyfile" in conf


# ─────────────────────────────────────────────────────────────
# 3. Bluetooth Daemon
# ─────────────────────────────────────────────────────────────
class TestBluetoothDaemon:
    @pytest.fixture
    def src(self, bluetooth_dir) -> str:
        path = bluetooth_dir / "xii-bluetooth.py"
        assert path.is_file(), "xii-bluetooth.py not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, bluetooth_dir):
        assert (bluetooth_dir / "xii-bluetooth.py").is_file()

    def test_has_shebang(self, src):
        assert src.startswith("#!/usr/bin/env python3")

    def test_is_valid_python(self, src):
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"xii-bluetooth.py syntax error: {e}")

    def test_has_dbus_import(self, src):
        assert "dbus" in src

    def test_has_bluez_constants(self, src):
        assert "org.bluez" in src
        assert "ADAPTER_IFACE" in src or "Adapter1" in src

    def test_has_bluetooth_manager_class(self, src):
        assert "class BluetoothManager" in src

    def test_has_status_method(self, src):
        assert "def status" in src

    def test_has_scan_method(self, src):
        assert "def scan" in src

    def test_has_pair_method(self, src):
        assert "def pair" in src

    def test_has_connect_method(self, src):
        assert "def connect" in src

    def test_has_disconnect_method(self, src):
        assert "def disconnect" in src

    def test_has_remove_method(self, src):
        assert "def remove" in src

    def test_has_power_control(self, src):
        assert "set_power" in src or "Powered" in src

    def test_has_battery_monitoring(self, src):
        assert "Battery" in src or "battery" in src.lower()

    def test_has_state_file(self, src):
        assert "bluetooth-state.json" in src

    def test_has_notifications(self, src):
        assert "notify-send" in src

    def test_has_device_class_map(self, src):
        assert "DEVICE_CLASSES" in src

    def test_has_cli_subcommands(self, src):
        for cmd in ["scan", "pair", "connect", "disconnect", "remove", "power"]:
            assert f'"{cmd}"' in src, f"Missing CLI command: {cmd}"

    def test_has_main_function(self, src):
        assert "def main" in src

    def test_service_exists(self, bluetooth_dir):
        assert (bluetooth_dir / "xii-bluetooth.service").is_file()


# ─────────────────────────────────────────────────────────────
# 4. BlueZ Config
# ─────────────────────────────────────────────────────────────
class TestBlueZConf:
    @pytest.fixture
    def conf(self, bluetooth_dir) -> str:
        path = bluetooth_dir / "main.conf"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, bluetooth_dir):
        assert (bluetooth_dir / "main.conf").is_file()

    def test_has_general_section(self, conf):
        assert "[General]" in conf

    def test_has_policy_section(self, conf):
        assert "[Policy]" in conf

    def test_has_le_section(self, conf):
        assert "[LE]" in conf

    def test_auto_enable(self, conf):
        assert "AutoEnable = true" in conf

    def test_has_controller_mode_dual(self, conf):
        assert "ControllerMode = dual" in conf

    def test_has_reconnect_intervals(self, conf):
        assert "ReconnectIntervals" in conf

    def test_has_privacy_setting(self, conf):
        assert "Privacy" in conf


# ─────────────────────────────────────────────────────────────
# 5. PipeWire Config
# ─────────────────────────────────────────────────────────────
class TestPipeWireConf:
    @pytest.fixture
    def conf(self, audio_dir) -> str:
        path = audio_dir / "pipewire.conf"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, audio_dir):
        assert (audio_dir / "pipewire.conf").is_file()

    def test_has_context_properties(self, conf):
        assert "context.properties" in conf

    def test_has_48khz_default(self, conf):
        assert "48000" in conf

    def test_allows_multiple_rates(self, conf):
        assert "44100" in conf and "96000" in conf, \
            "PipeWire should support multiple sample rates"

    def test_has_quantum_setting(self, conf):
        assert "clock.quantum" in conf

    def test_quantum_is_low_latency(self, conf):
        match = re.search(r'default\.clock\.quantum\s*=\s*(\d+)', conf)
        if match:
            quantum = int(match.group(1))
            assert quantum <= 512, f"Quantum {quantum} is too large for low latency"

    def test_has_spa_libs(self, conf):
        assert "context.spa-libs" in conf

    def test_has_alsa_backend(self, conf):
        assert "alsa" in conf

    def test_has_bluetooth_backend(self, conf):
        assert "bluez5" in conf or "bluetooth" in conf.lower()

    def test_has_modules(self, conf):
        assert "context.modules" in conf

    def test_has_rt_scheduling(self, conf):
        assert "libpipewire-module-rt" in conf or "rt.prio" in conf

    def test_has_pulse_compat(self, conf):
        assert "pipewire-pulse" in conf, \
            "Must include PulseAudio compat for legacy app support"


# ─────────────────────────────────────────────────────────────
# 6. Audio Script
# ─────────────────────────────────────────────────────────────
class TestAudioScript:
    @pytest.fixture
    def src(self, audio_dir) -> str:
        path = audio_dir / "xii-audio.sh"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, audio_dir):
        assert (audio_dir / "xii-audio.sh").is_file()

    def test_has_bash_shebang(self, src):
        assert src.startswith("#!/usr/bin/env bash") or \
               src.startswith("#!/bin/bash")

    def test_has_volume_up(self, src):
        assert "volume" in src and "up" in src

    def test_has_volume_down(self, src):
        assert "volume" in src and "down" in src

    def test_has_volume_get(self, src):
        assert "get" in src and "_get_volume" in src

    def test_has_mute_toggle(self, src):
        assert "mute" in src and "toggle" in src

    def test_has_mic_control(self, src):
        assert "mic" in src or "source" in src.lower()

    def test_uses_wpctl(self, src):
        assert "wpctl" in src, "Audio script must use wpctl (WirePlumber)"

    def test_has_xii_mode_support(self, src):
        assert "mode" in src
        assert "lite" in src and "standard" in src and "performance" in src

    def test_mode_adjusts_quantum(self, src):
        assert "clock.quantum" in src or "quantum" in src.lower()

    def test_has_notifications(self, src):
        assert "notify-send" in src or "_notify" in src

    def test_has_sink_list(self, src):
        assert "sink" in src and "list" in src

    def test_has_status_command(self, src):
        assert "status" in src


# ─────────────────────────────────────────────────────────────
# 7. udev Rules
# ─────────────────────────────────────────────────────────────
class TestUdevRules:
    @pytest.fixture
    def rules(self, hardware_dir) -> str:
        path = hardware_dir / "udev-rules" / "99-xii-usb.rules"
        assert path.is_file(), "99-xii-usb.rules not found"
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, hardware_dir):
        assert (hardware_dir / "udev-rules" / "99-xii-usb.rules").is_file()

    def test_has_usb_storage_rule(self, rules):
        assert "ID_BUS" in rules and "usb" in rules.lower()

    def test_has_input_permissions(self, rules):
        assert "SUBSYSTEM==\"input\"" in rules

    def test_has_gamepad_rules(self, rules):
        assert "045e" in rules or "054c" in rules, \
            "Should have gamepad controller rules"

    def test_has_yubikey_rule(self, rules):
        assert "1050" in rules, "Should have YubiKey FIDO2 rule"

    def test_has_uaccess_tag(self, rules):
        assert "uaccess" in rules

    def test_has_display_hotplug_rule(self, rules):
        assert "drm" in rules, "Should have display hotplug rule"

    def test_has_thunderbolt_rule(self, rules):
        assert "thunderbolt" in rules

    def test_has_adb_device_rules(self, rules):
        assert "18d1" in rules or "04e8" in rules, \
            "Should have Android ADB device rules"

    def test_has_usb_power_rule(self, rules):
        assert "power/control" in rules


# ─────────────────────────────────────────────────────────────
# 8. Hotplug Script
# ─────────────────────────────────────────────────────────────
class TestHotplugScript:
    @pytest.fixture
    def src(self, hardware_dir) -> str:
        path = hardware_dir / "xii-hotplug.sh"
        assert path.is_file()
        return path.read_text(encoding="utf-8")

    def test_file_exists(self, hardware_dir):
        assert (hardware_dir / "xii-hotplug.sh").is_file()

    def test_has_bash_shebang(self, src):
        assert src.startswith("#!/usr/bin/env bash")

    def test_has_usb_added_handler(self, src):
        assert "usb-added" in src or "handle_usb_added" in src

    def test_has_removed_handler(self, src):
        assert "removed" in src and "handle_removed" in src

    def test_has_display_added_handler(self, src):
        assert "display-added" in src or "handle_display_added" in src

    def test_has_display_removed_handler(self, src):
        assert "display-removed" in src or "handle_display_removed" in src

    def test_has_udisksctl_mount(self, src):
        assert "udisksctl" in src and "mount" in src

    def test_has_auto_unmount(self, src):
        assert "unmount" in src

    def test_has_xii_files_open(self, src):
        assert "xii-files" in src, \
            "Should open XII Files when USB drive is inserted"

    def test_has_hyprctl_reload_on_display(self, src):
        assert "hyprctl" in src, \
            "Should reload Hyprland when display is connected"

    def test_has_logging(self, src):
        assert "LOG_FILE" in src or "_log" in src

    def test_has_user_notification(self, src):
        assert "_notify_user" in src or "notify-send" in src

    def test_has_desktop_session_detection(self, src):
        assert "loginctl" in src, \
            "Should detect current logged-in user via loginctl"
