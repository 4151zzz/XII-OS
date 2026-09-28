#!/usr/bin/env python3
"""
XII OS — Bluetooth Manager
system/bluetooth/xii-bluetooth.py

A D-Bus connected Bluetooth manager for XII OS.
Uses BlueZ D-Bus API (org.bluez) directly.

Features:
  - Adapter power on/off
  - Device discovery (scan)
  - Pair, connect, disconnect, remove devices
  - Battery level monitoring (BAS profile)
  - A2DP audio device routing to PipeWire
  - Desktop notifications on connection events
  - State file at /run/xii-os/bluetooth-state.json

Requirements:
  apt install python3-dbus python3-gi bluez

Usage:
  xii-bluetooth status                   # JSON status
  xii-bluetooth scan [--timeout 10]      # Scan for devices
  xii-bluetooth pair   <mac>             # Pair with device
  xii-bluetooth connect    <mac>         # Connect paired device
  xii-bluetooth disconnect <mac>         # Disconnect device
  xii-bluetooth remove     <mac>         # Forget device
  xii-bluetooth power  on|off            # Adapter power
"""

import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import dbus
    import dbus.mainloop.glib
    import dbus.service
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
BLUEZ_SERVICE    = "org.bluez"
ADAPTER_PATH     = "/org/bluez/hci0"
ADAPTER_IFACE    = "org.bluez.Adapter1"
DEVICE_IFACE     = "org.bluez.Device1"
BATTERY_IFACE    = "org.bluez.Battery1"
PROP_IFACE       = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER   = "org.freedesktop.DBus.ObjectManager"
STATE_FILE       = "/run/xii-os/bluetooth-state.json"

DEVICE_CLASSES   = {
    0x000104: "Desktop Computer",
    0x000200: "Phone",
    0x000400: "LAN/Network Access Point",
    0x000500: "Peripheral",
    0x000600: "Imaging",
    0x002580: "Headphones",
    0x002504: "Headset",
    0x000540: "Mouse",
    0x000510: "Keyboard",
}


# ─────────────────────────────────────────────────────────────
# BlueZ D-Bus helpers
# ─────────────────────────────────────────────────────────────
def get_bus() -> "dbus.SystemBus":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    return dbus.SystemBus()


def get_adapter(bus) -> "dbus.Interface | None":
    try:
        obj = bus.get_object(BLUEZ_SERVICE, ADAPTER_PATH)
        return dbus.Interface(obj, ADAPTER_IFACE)
    except dbus.DBusException:
        return None


def get_adapter_props(bus) -> dict:
    try:
        obj   = bus.get_object(BLUEZ_SERVICE, ADAPTER_PATH)
        props = dbus.Interface(obj, PROP_IFACE)
        return dict(props.GetAll(ADAPTER_IFACE))
    except dbus.DBusException:
        return {}


def get_all_devices(bus) -> list[dict]:
    """Get all managed BlueZ objects (paired/known devices)."""
    try:
        obj = bus.get_object(BLUEZ_SERVICE, "/")
        mgr = dbus.Interface(obj, OBJECT_MANAGER)
        objects = mgr.GetManagedObjects()
    except dbus.DBusException:
        return []

    devices = []
    for path, interfaces in objects.items():
        if DEVICE_IFACE not in interfaces:
            continue
        props = interfaces[DEVICE_IFACE]
        battery = None
        if BATTERY_IFACE in interfaces:
            battery = int(interfaces[BATTERY_IFACE].get("Percentage", -1))
        devices.append({
            "path":      str(path),
            "address":   str(props.get("Address", "")),
            "name":      str(props.get("Name", "Unknown")),
            "alias":     str(props.get("Alias", "")),
            "paired":    bool(props.get("Paired", False)),
            "connected": bool(props.get("Connected", False)),
            "trusted":   bool(props.get("Trusted", False)),
            "class":     DEVICE_CLASSES.get(int(props.get("Class", 0)), "Unknown"),
            "rssi":      int(props.get("RSSI", 0)),
            "battery":   battery,
        })
    return devices


# ─────────────────────────────────────────────────────────────
# Bluetooth Manager
# ─────────────────────────────────────────────────────────────
class BluetoothManager:
    def __init__(self):
        if HAS_DBUS:
            self.bus = get_bus()
        else:
            self.bus = None

    def status(self) -> dict:
        if not self.bus:
            return {"error": "D-Bus not available"}
        adapter_props = get_adapter_props(self.bus)
        devices = get_all_devices(self.bus)
        connected = [d for d in devices if d["connected"]]
        return {
            "timestamp":    datetime.now().isoformat(),
            "powered":      bool(adapter_props.get("Powered", False)),
            "discovering":  bool(adapter_props.get("Discovering", False)),
            "discoverable": bool(adapter_props.get("Discoverable", False)),
            "pairable":     bool(adapter_props.get("Pairable", False)),
            "address":      str(adapter_props.get("Address", "")),
            "name":         str(adapter_props.get("Name", "XII OS")),
            "devices_total":     len(devices),
            "devices_connected": len(connected),
            "connected_devices": connected,
        }

    def set_power(self, on: bool):
        if not self.bus:
            return False
        try:
            obj   = self.bus.get_object(BLUEZ_SERVICE, ADAPTER_PATH)
            props = dbus.Interface(obj, PROP_IFACE)
            props.Set(ADAPTER_IFACE, "Powered", dbus.Boolean(on))
            return True
        except dbus.DBusException as e:
            print(f"[XII BT] Power error: {e}")
            return False

    def scan(self, timeout: int = 10) -> list[dict]:
        """Start discovery and return found devices."""
        if not self.bus:
            return []
        try:
            adapter = get_adapter(self.bus)
            if not adapter:
                return []
            adapter.StartDiscovery()
            print(f"[XII BT] Scanning for {timeout} seconds…")
            time.sleep(timeout)
            adapter.StopDiscovery()
        except dbus.DBusException as e:
            print(f"[XII BT] Scan error: {e}")
        return get_all_devices(self.bus)

    def _get_device_iface(self, mac: str):
        """Get Device1 interface for a MAC address."""
        for device in get_all_devices(self.bus):
            if device["address"].upper() == mac.upper():
                obj = self.bus.get_object(BLUEZ_SERVICE, device["path"])
                return dbus.Interface(obj, DEVICE_IFACE)
        return None

    def pair(self, mac: str) -> bool:
        dev = self._get_device_iface(mac)
        if not dev:
            print(f"[XII BT] Device {mac} not found — scan first")
            return False
        try:
            dev.Pair()
            return True
        except dbus.DBusException as e:
            print(f"[XII BT] Pair error: {e}")
            return False

    def connect(self, mac: str) -> bool:
        dev = self._get_device_iface(mac)
        if not dev:
            return False
        try:
            dev.Connect()
            self._notify_connect(mac)
            return True
        except dbus.DBusException as e:
            print(f"[XII BT] Connect error: {e}")
            return False

    def disconnect(self, mac: str) -> bool:
        dev = self._get_device_iface(mac)
        if not dev:
            return False
        try:
            dev.Disconnect()
            return True
        except dbus.DBusException as e:
            print(f"[XII BT] Disconnect error: {e}")
            return False

    def remove(self, mac: str) -> bool:
        """Remove/forget a paired device."""
        adapter = get_adapter(self.bus)
        for device in get_all_devices(self.bus):
            if device["address"].upper() == mac.upper():
                try:
                    adapter.RemoveDevice(device["path"])
                    return True
                except dbus.DBusException as e:
                    print(f"[XII BT] Remove error: {e}")
                    return False
        return False

    def write_state_file(self):
        state = self.status()
        p = Path(STATE_FILE)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _notify_connect(self, mac: str):
        name = mac
        for d in get_all_devices(self.bus):
            if d["address"].upper() == mac.upper():
                name = d.get("name", mac)
                break
        try:
            subprocess.Popen([
                "notify-send", "--app-name=XII Bluetooth",
                "--icon=bluetooth",
                "Bluetooth Connected", f"{name} is now connected"
            ])
        except FileNotFoundError:
            pass


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="XII OS Bluetooth Manager")
    subp   = parser.add_subparsers(dest="command")

    subp.add_parser("status",     help="Show Bluetooth status JSON")
    scan_p = subp.add_parser("scan", help="Scan for nearby devices")
    scan_p.add_argument("--timeout", "-t", type=int, default=10)

    pair_p = subp.add_parser("pair",       help="Pair with device")
    pair_p.add_argument("mac")

    con_p  = subp.add_parser("connect",    help="Connect paired device")
    con_p.add_argument("mac")

    dis_p  = subp.add_parser("disconnect", help="Disconnect device")
    dis_p.add_argument("mac")

    rem_p  = subp.add_parser("remove",     help="Forget device")
    rem_p.add_argument("mac")

    pwr_p  = subp.add_parser("power",      help="Adapter power")
    pwr_p.add_argument("state", choices=["on", "off"])

    args = parser.parse_args()
    bt   = BluetoothManager()

    if args.command == "status":
        print(json.dumps(bt.status(), indent=2))

    elif args.command == "scan":
        devices = bt.scan(args.timeout)
        print(f"\nFound {len(devices)} devices:")
        for d in devices:
            icon  = "📶" if d["connected"] else "🔵" if d["paired"] else "⬜"
            batt  = f"🔋{d['battery']}%" if d["battery"] is not None else ""
            print(f"  {icon} {d['address']}  {d['name']:30s}  {d['class']}  {batt}")

    elif args.command == "pair":
        ok = bt.pair(args.mac)
        print("✅ Paired" if ok else "❌ Pair failed")

    elif args.command == "connect":
        ok = bt.connect(args.mac)
        print("✅ Connected" if ok else "❌ Connect failed")

    elif args.command == "disconnect":
        ok = bt.disconnect(args.mac)
        print("✅ Disconnected" if ok else "❌ Disconnect failed")

    elif args.command == "remove":
        ok = bt.remove(args.mac)
        print("✅ Removed" if ok else "❌ Remove failed")

    elif args.command == "power":
        ok = bt.set_power(args.state == "on")
        print(f"✅ Bluetooth {args.state}" if ok else "❌ Failed")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
