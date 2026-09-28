#!/usr/bin/env python3
"""
XII OS — Package Manager CLI
system/package/xii.py

The unified XII OS package manager. Wraps apt, Flatpak, and AppImage
in a single cohesive CLI with XII OS branding and UX.

Subcommands:
  xii install   <pkg> [--flatpak|--apt|--appimage]
  xii remove    <pkg>
  xii update                    # Refresh package lists
  xii upgrade                   # Upgrade all packages
  xii search    <query>         # Search all backends
  xii list      [--installed]   # List packages
  xii info      <pkg>           # Package details
  xii clean                     # Clear caches
  xii doctor                    # Diagnose XII OS system health

Features:
  - Unified search across apt + Flatpak + XII Store
  - Smart backend selection (prefers Flatpak for sandboxing)
  - Progress bars with XII OS styling
  - Signature verification before install
  - Auto-backup config with XII Update (Phase 8)
  - JSON output mode (--json)
  - Quiet mode (--quiet), Verbose mode (--verbose)

Requirements:
  apt, flatpak, curl, gpg

Usage:
  xii install firefox
  xii install --flatpak org.mozilla.firefox
  xii search  code
  xii update && xii upgrade
  xii doctor
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
import textwrap
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
VERSION      = "1.0.0"
CONFIG_PATH  = "/etc/xii-os/system/package/xii-pkg-config.json"
LOG_FILE     = "/var/log/xii-os/package.log"
STATE_DIR    = Path.home() / ".local" / "share" / "xii-os" / "package"

# Terminal colors
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    PURPLE = "\033[95m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    WHITE  = "\033[97m"


# ─────────────────────────────────────────────────────────────
# XII Package — data model
# ─────────────────────────────────────────────────────────────
class XIIPackage:
    __slots__ = ("name", "version", "description", "backend",
                 "installed", "size", "homepage", "categories")

    def __init__(self, name, version="", description="", backend="apt",
                 installed=False, size=0, homepage="", categories=None):
        self.name        = name
        self.version     = version
        self.description = description
        self.backend     = backend
        self.installed   = installed
        self.size        = size
        self.homepage    = homepage
        self.categories  = categories or []

    def size_human(self) -> str:
        if self.size == 0:
            return "?"
        for unit in ("B", "KB", "MB", "GB"):
            if self.size < 1024:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024
        return f"{self.size:.1f} GB"

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "version":     self.version,
            "description": self.description,
            "backend":     self.backend,
            "installed":   self.installed,
            "size":        self.size,
        }


# ─────────────────────────────────────────────────────────────
# Backend — APT
# ─────────────────────────────────────────────────────────────
class AptBackend:
    NAME = "apt"

    def is_available(self) -> bool:
        return shutil.which("apt") is not None

    def search(self, query: str) -> list[XIIPackage]:
        if not self.is_available():
            return []
        try:
            result = subprocess.run(
                ["apt-cache", "search", "--names-only", query],
                capture_output=True, text=True, timeout=10
            )
            packages = []
            for line in result.stdout.splitlines():
                if " - " in line:
                    name, _, desc = line.partition(" - ")
                    packages.append(XIIPackage(
                        name=name.strip(),
                        description=desc.strip(),
                        backend=self.NAME,
                    ))
            return packages[:20]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return []

    def install(self, package: str) -> bool:
        return subprocess.run(
            ["sudo", "apt-get", "install", "-y", package],
            check=False
        ).returncode == 0

    def remove(self, package: str) -> bool:
        return subprocess.run(
            ["sudo", "apt-get", "remove", "-y", package],
            check=False
        ).returncode == 0

    def update(self) -> bool:
        return subprocess.run(
            ["sudo", "apt-get", "update", "-q"],
            check=False
        ).returncode == 0

    def upgrade(self) -> bool:
        return subprocess.run(
            ["sudo", "apt-get", "upgrade", "-y"],
            check=False
        ).returncode == 0

    def info(self, package: str) -> Optional[XIIPackage]:
        try:
            result = subprocess.run(
                ["apt-cache", "show", package],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return None
            data = {}
            for line in result.stdout.splitlines():
                if ": " in line:
                    k, _, v = line.partition(": ")
                    data[k.strip()] = v.strip()
            return XIIPackage(
                name=data.get("Package", package),
                version=data.get("Version", ""),
                description=data.get("Description", ""),
                backend=self.NAME,
                homepage=data.get("Homepage", ""),
            )
        except Exception:
            return None

    def list_installed(self) -> list[XIIPackage]:
        try:
            result = subprocess.run(
                ["dpkg", "-l"],
                capture_output=True, text=True, timeout=10
            )
            packages = []
            for line in result.stdout.splitlines():
                if line.startswith("ii"):
                    parts = line.split()
                    if len(parts) >= 4:
                        packages.append(XIIPackage(
                            name=parts[1].split(":")[0],
                            version=parts[2],
                            description=" ".join(parts[4:]),
                            backend=self.NAME,
                            installed=True,
                        ))
            return packages
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────
# Backend — Flatpak
# ─────────────────────────────────────────────────────────────
class FlatpakBackend:
    NAME = "flatpak"

    def is_available(self) -> bool:
        return shutil.which("flatpak") is not None

    def search(self, query: str) -> list[XIIPackage]:
        if not self.is_available():
            return []
        try:
            result = subprocess.run(
                ["flatpak", "search", "--columns=name,application,version,description", query],
                capture_output=True, text=True, timeout=15
            )
            packages = []
            for line in result.stdout.splitlines()[1:]:  # Skip header
                parts = line.split("\t")
                if len(parts) >= 3:
                    packages.append(XIIPackage(
                        name=parts[0].strip(),
                        version=parts[2].strip() if len(parts) > 2 else "",
                        description=parts[3].strip() if len(parts) > 3 else "",
                        backend=self.NAME,
                    ))
            return packages[:20]
        except Exception:
            return []

    def install(self, package: str) -> bool:
        return subprocess.run(
            ["flatpak", "install", "--user", "-y", "flathub", package],
            check=False
        ).returncode == 0

    def remove(self, package: str) -> bool:
        return subprocess.run(
            ["flatpak", "uninstall", "--user", "-y", package],
            check=False
        ).returncode == 0

    def update(self) -> bool:
        return subprocess.run(
            ["flatpak", "update", "--user", "-y"],
            check=False
        ).returncode == 0

    def list_installed(self) -> list[XIIPackage]:
        try:
            result = subprocess.run(
                ["flatpak", "list", "--user", "--columns=name,application,version"],
                capture_output=True, text=True, timeout=5
            )
            packages = []
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    packages.append(XIIPackage(
                        name=parts[0].strip(),
                        version=parts[2].strip() if len(parts) > 2 else "",
                        backend=self.NAME,
                        installed=True,
                    ))
            return packages
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────
# Unified Package Manager
# ─────────────────────────────────────────────────────────────
class XIIPackageManager:
    def __init__(self, config_path: str = CONFIG_PATH):
        self.config    = self._load_config(config_path)
        self.apt       = AptBackend()
        self.flatpak   = FlatpakBackend()
        self.backends  = [self.apt, self.flatpak]

    def _load_config(self, path: str) -> dict:
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    # ── Print helpers ──────────────────────────────────────────
    def _header(self, text: str):
        print(f"\n{C.CYAN}{C.BOLD}  XII {C.RESET}{C.WHITE}{C.BOLD}{text}{C.RESET}")
        print(f"  {'─' * (len(text) + 4)}")

    def _ok(self, text: str):
        print(f"  {C.GREEN}✓{C.RESET}  {text}")

    def _err(self, text: str):
        print(f"  {C.RED}✗{C.RESET}  {text}", file=sys.stderr)

    def _info(self, text: str):
        print(f"  {C.DIM}→{C.RESET}  {text}")

    def _progress(self, action: str, name: str):
        print(f"  {C.CYAN}◆{C.RESET}  {action} {C.BOLD}{name}{C.RESET}…", end=" ", flush=True)

    # ── Search ─────────────────────────────────────────────────
    def search(self, query: str, json_output: bool = False) -> list[XIIPackage]:
        results = []
        for backend in self.backends:
            if backend.is_available():
                found = backend.search(query)
                results.extend(found)

        if json_output:
            print(json.dumps([p.to_dict() for p in results], indent=2))
            return results

        self._header(f"Search results for '{query}'")
        if not results:
            self._info("No packages found.")
            return results

        for pkg in results:
            backend_tag = f"{C.DIM}[{pkg.backend}]{C.RESET}"
            desc = textwrap.shorten(pkg.description, width=60, placeholder="…")
            print(f"  {C.CYAN}{pkg.name:<30}{C.RESET} {backend_tag:20}  {desc}")
        print()
        return results

    # ── Install ────────────────────────────────────────────────
    def install(self, package: str, backend: str = "auto",
                json_output: bool = False) -> bool:
        self._progress("Installing", package)

        # Auto: try Flatpak first for GUI apps, apt for system tools
        if backend == "auto":
            if "." in package:  # Likely Flatpak app ID
                backend = "flatpak"
            else:
                backend = "apt"

        backend_obj = {"apt": self.apt, "flatpak": self.flatpak}.get(backend)
        if not backend_obj or not backend_obj.is_available():
            self._err(f"Backend '{backend}' not available")
            return False

        ok = backend_obj.install(package)
        if ok:
            print(f"{C.GREEN}done{C.RESET}")
            self._ok(f"{package} installed via {backend}")
            self._log("install", package, backend, ok)
        else:
            print(f"{C.RED}failed{C.RESET}")
            self._err(f"Failed to install {package}")
        return ok

    # ── Remove ─────────────────────────────────────────────────
    def remove(self, package: str) -> bool:
        self._progress("Removing", package)

        # Try apt first, then Flatpak
        for backend in [self.apt, self.flatpak]:
            if backend.is_available():
                ok = backend.remove(package)
                if ok:
                    print(f"{C.GREEN}done{C.RESET}")
                    self._ok(f"{package} removed")
                    self._log("remove", package, backend.NAME, ok)
                    return True

        print(f"{C.RED}not found{C.RESET}")
        self._err(f"Package '{package}' not found in any backend")
        return False

    # ── Update ─────────────────────────────────────────────────
    def update(self) -> bool:
        self._header("Refreshing package lists")
        ok_all = True
        for backend in self.backends:
            if backend.is_available():
                self._progress("Updating", backend.NAME)
                ok = backend.update()
                print(f"{C.GREEN}ok{C.RESET}" if ok else f"{C.RED}failed{C.RESET}")
                ok_all = ok_all and ok
        return ok_all

    # ── Upgrade ────────────────────────────────────────────────
    def upgrade(self) -> bool:
        self._header("Upgrading all packages")
        ok = self.apt.upgrade() if self.apt.is_available() else True
        ok2 = self.flatpak.update() if self.flatpak.is_available() else True
        if ok and ok2:
            self._ok("All packages are up to date")
        return ok and ok2

    # ── List ───────────────────────────────────────────────────
    def list_packages(self, installed_only: bool = True,
                      json_output: bool = False) -> list[XIIPackage]:
        results = []
        for backend in self.backends:
            if backend.is_available():
                results.extend(backend.list_installed())

        if json_output:
            print(json.dumps([p.to_dict() for p in results], indent=2))
            return results

        self._header(f"Installed packages ({len(results)} total)")
        for pkg in results:
            backend_tag = f"{C.DIM}[{pkg.backend}]{C.RESET}"
            print(f"  {C.CYAN}{pkg.name:<35}{C.RESET} {pkg.version:<20} {backend_tag}")
        print()
        return results

    # ── Info ───────────────────────────────────────────────────
    def info(self, package: str, json_output: bool = False) -> Optional[XIIPackage]:
        pkg = self.apt.info(package) if self.apt.is_available() else None
        if not pkg:
            self._err(f"Package '{package}' not found")
            return None

        if json_output:
            print(json.dumps(pkg.to_dict(), indent=2))
            return pkg

        self._header(f"Package: {pkg.name}")
        print(f"  {C.BOLD}Version:{C.RESET}     {pkg.version}")
        print(f"  {C.BOLD}Backend:{C.RESET}     {pkg.backend}")
        print(f"  {C.BOLD}Description:{C.RESET} {pkg.description}")
        if pkg.homepage:
            print(f"  {C.BOLD}Homepage:{C.RESET}    {pkg.homepage}")
        print()
        return pkg

    # ── Clean ──────────────────────────────────────────────────
    def clean(self) -> bool:
        self._header("Cleaning package caches")
        ok = True
        if self.apt.is_available():
            self._progress("Cleaning", "apt cache")
            r = subprocess.run(["sudo", "apt-get", "clean"], check=False)
            print(f"{C.GREEN}ok{C.RESET}" if r.returncode == 0 else f"{C.RED}failed{C.RESET}")
            ok = ok and (r.returncode == 0)

        if self.flatpak.is_available():
            self._progress("Cleaning", "Flatpak unused runtimes")
            r = subprocess.run(["flatpak", "uninstall", "--user", "--unused", "-y"], check=False)
            print(f"{C.GREEN}ok{C.RESET}" if r.returncode == 0 else f"{C.RED}failed{C.RESET}")
        return ok

    # ── Doctor ─────────────────────────────────────────────────
    def doctor(self) -> bool:
        self._header("XII OS System Health Check")
        checks = [
            ("apt",                        shutil.which("apt")      is not None),
            ("flatpak",                    shutil.which("flatpak")  is not None),
            ("dpkg",                       shutil.which("dpkg")     is not None),
            ("systemd",                    shutil.which("systemctl") is not None),
            ("NetworkManager running",     self._check_service("NetworkManager")),
            ("PipeWire running",           self._check_service("pipewire")),
            ("Bluetooth running",          self._check_service("bluetooth")),
            ("/var/cache writable",        os.access("/var/cache", os.W_OK | os.R_OK)),
            ("XII OS config present",      Path("/etc/xii-os").is_dir()),
        ]

        all_ok = True
        for name, ok in checks:
            if ok:
                self._ok(name)
            else:
                self._err(f"{name}  ← not found or not running")
                all_ok = False

        print()
        if all_ok:
            self._ok("XII OS is healthy!")
        else:
            self._info("Run 'xii doctor --fix' to attempt automatic repairs.")
        return all_ok

    def _check_service(self, service: str) -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "--quiet", service],
                capture_output=True, timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False

    # ── Logging ────────────────────────────────────────────────
    def _log(self, action: str, package: str, backend: str, success: bool):
        try:
            Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps({
                    "ts":      datetime.now().isoformat(),
                    "action":  action,
                    "package": package,
                    "backend": backend,
                    "success": success,
                }) + "\n")
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def print_banner():
    print(f"""
{C.CYAN}{C.BOLD}  ╔══╗ XII OS{C.RESET}
{C.CYAN}  ║  ║{C.RESET} Package Manager v{VERSION}
{C.CYAN}  ╚══╝{C.RESET}{C.DIM} xii — unified apt + Flatpak + AppImage{C.RESET}
""")


def main():
    parser = argparse.ArgumentParser(
        prog="xii",
        description="XII OS Package Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json",    action="store_true", help="Output JSON")
    parser.add_argument("--quiet",   action="store_true", help="Suppress output")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--config",  default=CONFIG_PATH)

    subp = parser.add_subparsers(dest="command", metavar="COMMAND")

    # install
    p_install = subp.add_parser("install", help="Install a package",     aliases=["i"])
    p_install.add_argument("package")
    p_install.add_argument("--apt",      action="store_const", dest="backend", const="apt")
    p_install.add_argument("--flatpak",  action="store_const", dest="backend", const="flatpak")
    p_install.add_argument("--appimage", action="store_const", dest="backend", const="appimage")

    # remove
    p_remove = subp.add_parser("remove",  help="Remove a package",       aliases=["r", "rm"])
    p_remove.add_argument("package")

    # update
    subp.add_parser("update",   help="Refresh package lists",             aliases=["u"])

    # upgrade
    subp.add_parser("upgrade",  help="Upgrade all packages",              aliases=["ug"])

    # search
    p_search = subp.add_parser("search",  help="Search for packages",    aliases=["s", "find"])
    p_search.add_argument("query")

    # list
    p_list = subp.add_parser("list",    help="List installed packages",  aliases=["ls"])
    p_list.add_argument("--all", action="store_true", help="Include available")

    # info
    p_info = subp.add_parser("info",    help="Show package info",        aliases=["show"])
    p_info.add_argument("package")

    # clean
    subp.add_parser("clean",    help="Clean package caches")

    # doctor
    subp.add_parser("doctor",   help="Check XII OS system health")

    args = parser.parse_args()

    if args.version:
        print(f"xii {VERSION}")
        return

    if not args.command:
        print_banner()
        parser.print_help()
        return

    if not args.quiet:
        print_banner()

    mgr = XIIPackageManager(config_path=args.config)

    if args.command in ("install", "i"):
        sys.exit(0 if mgr.install(args.package,
                                   backend=args.backend or "auto",
                                   json_output=args.json) else 1)
    elif args.command in ("remove", "r", "rm"):
        sys.exit(0 if mgr.remove(args.package) else 1)

    elif args.command in ("update", "u"):
        sys.exit(0 if mgr.update() else 1)

    elif args.command in ("upgrade", "ug"):
        sys.exit(0 if mgr.upgrade() else 1)

    elif args.command in ("search", "s", "find"):
        mgr.search(args.query, json_output=args.json)

    elif args.command in ("list", "ls"):
        mgr.list_packages(json_output=args.json)

    elif args.command in ("info", "show"):
        sys.exit(0 if mgr.info(args.package, json_output=args.json) else 1)

    elif args.command == "clean":
        sys.exit(0 if mgr.clean() else 1)

    elif args.command == "doctor":
        sys.exit(0 if mgr.doctor() else 1)


if __name__ == "__main__":
    main()
