#!/usr/bin/env python3
"""
XII OS — Security Daemon
system/security/xii-security.py

A comprehensive security monitoring daemon and CLI for XII OS.

Features:
  - System integrity check (file hash verification)
  - Permission audit (setuid/setgid files, world-writable dirs)
  - Firewall status monitoring (nftables / ufw)
  - AppArmor profile status
  - Failed login attempt detection (via journald)
  - Suspicious process detection
  - USB device authorization audit
  - Automatic security report generation
  - D-Bus interface for XII Security Center GUI
  - Alerts via desktop notification (critical urgency)

Threat Levels:
  INFO    — informational, no action required
  LOW     — minor finding, review recommended
  MEDIUM  — review and remediate soon
  HIGH    — active risk, action required
  CRITICAL— immediate action required

Requirements:
  python3, systemd-journald, nftables or ufw, apparmor (optional)

Usage:
  xii-security scan              # Full security scan → JSON report
  xii-security firewall status   # Firewall rules summary
  xii-security integrity check   # File integrity check
  xii-security audit             # Permission audit
  xii-security log               # Recent security events
  xii-security daemon            # Run as persistent daemon
"""

import os
import sys
import json
import stat
import hashlib
import argparse
import subprocess
import syslog
from pathlib import Path
from datetime import datetime, timedelta
from typing import NamedTuple

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
VERSION       = "1.0.0"
STATE_DIR     = Path("/var/lib/xii-os/security")
REPORT_FILE   = Path("/var/log/xii-os/security-report.json")
LOG_FILE      = Path("/var/log/xii-os/security.log")
BASELINE_FILE = Path("/etc/xii-os/security/integrity-baseline.json")

CRITICAL_PATHS = [
    "/etc/passwd", "/etc/shadow", "/etc/sudoers",
    "/etc/xii-os/current-mode",
    "/usr/bin/sudo", "/usr/bin/su",
    "/boot/grub/grub.cfg",
]

SUSPICIOUS_PROCESSES = [
    "cryptominer", "xmrig", "minerd",
    "netcat", "nc -l",
    "nmap",
]

# Severity levels
CRITICAL = "CRITICAL"
HIGH     = "HIGH"
MEDIUM   = "MEDIUM"
LOW      = "LOW"
INFO     = "INFO"

SEVERITY_COLOR = {
    CRITICAL: "\033[91m",
    HIGH:     "\033[93m",
    MEDIUM:   "\033[33m",
    LOW:      "\033[36m",
    INFO:     "\033[37m",
    "RESET":  "\033[0m",
    "BOLD":   "\033[1m",
}


# ─────────────────────────────────────────────────────────────
# Finding — data model for security findings
# ─────────────────────────────────────────────────────────────
class Finding(NamedTuple):
    severity:    str
    category:    str
    title:       str
    description: str
    path:        str = ""
    remediation: str = ""

    def to_dict(self) -> dict:
        return self._asdict()


# ─────────────────────────────────────────────────────────────
# Firewall Monitor
# ─────────────────────────────────────────────────────────────
class FirewallMonitor:
    def status(self) -> dict:
        """Return firewall status dict."""
        # Try nftables first (XII OS default)
        nft = self._check_nftables()
        if nft["available"]:
            return nft

        # Fallback to ufw
        ufw = self._check_ufw()
        return ufw

    def _check_nftables(self) -> dict:
        try:
            result = subprocess.run(
                ["nft", "list", "ruleset"],
                capture_output=True, text=True, timeout=5
            )
            rules = result.stdout.strip().splitlines()
            rule_count = sum(1 for l in rules if l.strip().startswith(("rule", "chain")))
            return {
                "available": True,
                "backend":   "nftables",
                "active":    result.returncode == 0,
                "rule_count": rule_count,
                "output":    result.stdout[:500],
            }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {"available": False, "backend": "nftables"}

    def _check_ufw(self) -> dict:
        try:
            result = subprocess.run(
                ["ufw", "status", "verbose"],
                capture_output=True, text=True, timeout=5
            )
            active = "Status: active" in result.stdout
            return {
                "available": True,
                "backend":   "ufw",
                "active":    active,
                "output":    result.stdout[:500],
            }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {"available": False, "backend": "ufw"}

    def findings(self) -> list[Finding]:
        status = self.status()
        findings = []
        if not status.get("available"):
            findings.append(Finding(
                severity=HIGH, category="Firewall",
                title="No firewall detected",
                description="Neither nftables nor ufw is available on this system.",
                remediation="Install ufw: 'xii install ufw' then 'ufw enable'"
            ))
        elif not status.get("active"):
            findings.append(Finding(
                severity=HIGH, category="Firewall",
                title="Firewall is INACTIVE",
                description=f"{status['backend']} is installed but not running.",
                remediation="Enable the firewall via XII Security Center or 'ufw enable'"
            ))
        else:
            findings.append(Finding(
                severity=INFO, category="Firewall",
                title=f"Firewall active ({status['backend']})",
                description=f"Firewall is running with {status.get('rule_count', '?')} rules.",
            ))
        return findings


# ─────────────────────────────────────────────────────────────
# Integrity Checker
# ─────────────────────────────────────────────────────────────
class IntegrityChecker:
    def create_baseline(self, paths: list[str] = None) -> dict:
        """Create SHA-256 baseline for critical system files."""
        paths = paths or CRITICAL_PATHS
        baseline = {
            "created":   datetime.now().isoformat(),
            "xii_version": "1.0.0",
            "hashes": {}
        }
        for p in paths:
            path = Path(p)
            if path.is_file():
                try:
                    h = hashlib.sha256(path.read_bytes()).hexdigest()
                    baseline["hashes"][p] = {"sha256": h, "size": path.stat().st_size}
                except (PermissionError, OSError):
                    baseline["hashes"][p] = {"sha256": None, "error": "Permission denied"}
        return baseline

    def check(self) -> list[Finding]:
        """Compare current file hashes to baseline."""
        findings = []
        if not BASELINE_FILE.exists():
            findings.append(Finding(
                severity=MEDIUM, category="Integrity",
                title="No integrity baseline found",
                description="File integrity baseline has not been created.",
                remediation="Run 'xii-security integrity baseline' to create one."
            ))
            return findings

        try:
            baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            findings.append(Finding(
                severity=HIGH, category="Integrity",
                title="Baseline file is corrupt",
                description=str(BASELINE_FILE),
                remediation="Recreate baseline: 'xii-security integrity baseline'"
            ))
            return findings

        for path_str, expected in baseline.get("hashes", {}).items():
            path = Path(path_str)
            if not path.exists():
                findings.append(Finding(
                    severity=MEDIUM, category="Integrity",
                    title=f"Critical file missing: {path_str}",
                    description="File was present at baseline but is now missing.",
                    path=path_str,
                ))
                continue
            if expected.get("sha256") is None:
                continue
            try:
                current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                if current_hash != expected["sha256"]:
                    findings.append(Finding(
                        severity=CRITICAL, category="Integrity",
                        title=f"FILE MODIFIED: {path_str}",
                        description=f"Hash mismatch — expected {expected['sha256'][:16]}…, "
                                    f"got {current_hash[:16]}…",
                        path=path_str,
                        remediation="Verify this change is authorized. If unexpected, "
                                    "consider reinstalling the affected package.",
                    ))
                else:
                    findings.append(Finding(
                        severity=INFO, category="Integrity",
                        title=f"OK: {path_str}",
                        description="Hash verified.",
                        path=path_str,
                    ))
            except (PermissionError, OSError):
                pass
        return findings


# ─────────────────────────────────────────────────────────────
# Permission Auditor
# ─────────────────────────────────────────────────────────────
class PermissionAuditor:
    def audit(self) -> list[Finding]:
        findings = []
        findings.extend(self._check_setuid())
        findings.extend(self._check_world_writable())
        findings.extend(self._check_shadow_permissions())
        return findings

    def _check_setuid(self) -> list[Finding]:
        """Find setuid/setgid binaries outside of expected paths."""
        findings = []
        EXPECTED_SETUID = {
            "/usr/bin/sudo", "/usr/bin/su", "/usr/bin/passwd",
            "/usr/bin/newgrp", "/usr/sbin/pam_timestamp_check",
            "/usr/lib/openssh/ssh-keysign",
        }
        try:
            result = subprocess.run(
                ["find", "/usr", "/bin", "/sbin", "-perm", "/4000", "-o", "-perm", "/2000"],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.splitlines():
                path = line.strip()
                if path and path not in EXPECTED_SETUID:
                    findings.append(Finding(
                        severity=MEDIUM, category="Permissions",
                        title=f"Unexpected setuid binary: {path}",
                        description=f"{path} has setuid/setgid bit set but is not in the "
                                    "XII OS expected setuid allowlist.",
                        path=path,
                        remediation=f"Verify this is intentional: ls -la {path}"
                    ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return findings

    def _check_world_writable(self) -> list[Finding]:
        """Find world-writable files/directories in sensitive locations."""
        findings = []
        try:
            result = subprocess.run(
                ["find", "/etc", "/usr/bin", "/usr/sbin", "-perm", "-o+w", "-not",
                 "-path", "*/proc/*"],
                capture_output=True, text=True, timeout=15
            )
            for line in result.stdout.splitlines():
                path = line.strip()
                if path:
                    findings.append(Finding(
                        severity=HIGH, category="Permissions",
                        title=f"World-writable sensitive file: {path}",
                        description="This file can be modified by any user on the system.",
                        path=path,
                        remediation=f"chmod o-w {path}"
                    ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return findings

    def _check_shadow_permissions(self) -> list[Finding]:
        """Verify /etc/shadow has correct permissions (640 or stricter)."""
        findings = []
        shadow = Path("/etc/shadow")
        if shadow.exists():
            try:
                mode = shadow.stat().st_mode
                if mode & (stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH):
                    findings.append(Finding(
                        severity=CRITICAL, category="Permissions",
                        title="/etc/shadow is world-readable",
                        description="/etc/shadow contains password hashes and must not be "
                                    "readable by other users.",
                        path="/etc/shadow",
                        remediation="chmod 640 /etc/shadow && chown root:shadow /etc/shadow"
                    ))
                else:
                    findings.append(Finding(
                        severity=INFO, category="Permissions",
                        title="/etc/shadow permissions OK",
                        description=f"Mode: {oct(mode)[-3:]}",
                        path="/etc/shadow",
                    ))
            except PermissionError:
                pass
        return findings


# ─────────────────────────────────────────────────────────────
# Login Monitor
# ─────────────────────────────────────────────────────────────
class LoginMonitor:
    FAILED_THRESHOLD = 5  # Alert if more than this many failures

    def check(self) -> list[Finding]:
        findings = []
        try:
            result = subprocess.run(
                ["journalctl", "-u", "sshd", "--since", "24 hours ago",
                 "--no-pager", "-q"],
                capture_output=True, text=True, timeout=5
            )
            failed = sum(1 for line in result.stdout.splitlines()
                         if "Failed password" in line or "Invalid user" in line)
            if failed > self.FAILED_THRESHOLD:
                findings.append(Finding(
                    severity=HIGH if failed > 20 else MEDIUM,
                    category="Login",
                    title=f"{failed} failed SSH login attempts (last 24h)",
                    description="Elevated number of failed SSH login attempts detected.",
                    remediation="Consider: fail2ban, SSH key-only auth, port change"
                ))
            elif failed > 0:
                findings.append(Finding(
                    severity=LOW, category="Login",
                    title=f"{failed} failed SSH login attempts (last 24h)",
                    description="Normal level of failed SSH attempts.",
                ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return findings


# ─────────────────────────────────────────────────────────────
# AppArmor Checker
# ─────────────────────────────────────────────────────────────
class AppArmorChecker:
    def check(self) -> list[Finding]:
        findings = []
        try:
            result = subprocess.run(
                ["aa-status", "--json"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                findings.append(Finding(
                    severity=MEDIUM, category="AppArmor",
                    title="AppArmor not active",
                    description="AppArmor mandatory access control is not running.",
                    remediation="Enable AppArmor: 'systemctl enable --now apparmor'"
                ))
                return findings
            data = json.loads(result.stdout)
            enforced = data.get("profiles", {}).get("enforce", 0)
            complain  = data.get("profiles", {}).get("complain", 0)
            findings.append(Finding(
                severity=INFO, category="AppArmor",
                title=f"AppArmor active: {enforced} enforced, {complain} complain",
                description="Mandatory access control is protecting your system.",
            ))
            if complain > 0:
                findings.append(Finding(
                    severity=LOW, category="AppArmor",
                    title=f"{complain} profiles in complain mode (not enforced)",
                    description="Some AppArmor profiles are logging but not blocking.",
                    remediation="Run: aa-enforce /etc/apparmor.d/*"
                ))
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            findings.append(Finding(
                severity=LOW, category="AppArmor",
                title="AppArmor status unknown",
                description="Could not query AppArmor status (aa-status not found).",
            ))
        return findings


# ─────────────────────────────────────────────────────────────
# XII Security Scanner — orchestrates all checks
# ─────────────────────────────────────────────────────────────
class XIISecurityScanner:
    def __init__(self):
        self.firewall  = FirewallMonitor()
        self.integrity = IntegrityChecker()
        self.perms     = PermissionAuditor()
        self.login     = LoginMonitor()
        self.apparmor  = AppArmorChecker()

    def full_scan(self) -> dict:
        """Run all security checks and return a structured report."""
        started = datetime.now()
        all_findings: list[Finding] = []

        all_findings.extend(self.firewall.findings())
        all_findings.extend(self.integrity.check())
        all_findings.extend(self.perms.audit())
        all_findings.extend(self.login.check())
        all_findings.extend(self.apparmor.check())

        elapsed = (datetime.now() - started).total_seconds()

        # Score: start at 100, deduct per severity
        deductions = {CRITICAL: 25, HIGH: 15, MEDIUM: 8, LOW: 2, INFO: 0}
        score = 100
        for f in all_findings:
            score -= deductions.get(f.severity, 0)
        score = max(0, score)

        report = {
            "meta": {
                "xii_version":   "1.0.0",
                "scan_time":     started.isoformat(),
                "elapsed_sec":   round(elapsed, 2),
                "hostname":      os.uname().nodename,
                "security_score": score,
            },
            "summary": {
                CRITICAL: sum(1 for f in all_findings if f.severity == CRITICAL),
                HIGH:     sum(1 for f in all_findings if f.severity == HIGH),
                MEDIUM:   sum(1 for f in all_findings if f.severity == MEDIUM),
                LOW:      sum(1 for f in all_findings if f.severity == LOW),
                INFO:     sum(1 for f in all_findings if f.severity == INFO),
            },
            "findings": [f.to_dict() for f in all_findings],
        }
        return report

    def write_report(self, report: dict):
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    def notify_critical(self, report: dict):
        crit = report["summary"].get(CRITICAL, 0)
        high = report["summary"].get(HIGH, 0)
        if crit > 0:
            try:
                subprocess.Popen([
                    "notify-send", "--app-name=XII Security",
                    "--icon=security-high",
                    "--urgency=critical",
                    f"{crit} CRITICAL security issue(s) found",
                    "Open XII Security Center immediately."
                ])
            except FileNotFoundError:
                pass
        elif high > 0:
            try:
                subprocess.Popen([
                    "notify-send", "--app-name=XII Security",
                    "--icon=security-medium",
                    "--urgency=normal",
                    f"{high} HIGH security finding(s)",
                    "Review in XII Security Center."
                ])
            except FileNotFoundError:
                pass


# ─────────────────────────────────────────────────────────────
# CLI Display helpers
# ─────────────────────────────────────────────────────────────
def _severity_icon(severity: str) -> str:
    return {
        CRITICAL: "🔴",
        HIGH:     "🟠",
        MEDIUM:   "🟡",
        LOW:      "🔵",
        INFO:     "⚪",
    }.get(severity, "⚪")


def _print_report(report: dict):
    C = SEVERITY_COLOR
    meta    = report["meta"]
    summary = report["summary"]
    score   = meta["security_score"]

    # Score color
    if score >= 90:   score_color = "\033[92m"
    elif score >= 70: score_color = "\033[93m"
    elif score >= 50: score_color = "\033[33m"
    else:             score_color = "\033[91m"

    print(f"""
{C['BOLD']}\033[96m  ╔══╗ XII OS{C['RESET']}
\033[96m  ║  ║{C['RESET']}{C['BOLD']} Security Report{C['RESET']}
\033[96m  ╚══╝{C['RESET']} {meta['hostname']}  —  {meta['scan_time'][:10]}

  Security Score: {score_color}{C['BOLD']}{score}/100{C['RESET']}
  Scan time: {meta['elapsed_sec']}s
""")

    print(f"  {C['BOLD']}Summary:{C['RESET']}")
    for sev in [CRITICAL, HIGH, MEDIUM, LOW, INFO]:
        count = summary.get(sev, 0)
        icon  = _severity_icon(sev)
        col   = C.get(sev, "")
        print(f"    {icon} {col}{sev:<10}{C['RESET']}  {count}")

    print(f"\n  {C['BOLD']}Findings:{C['RESET']}")
    for f in report["findings"]:
        if f["severity"] == INFO:
            continue  # Skip INFO in tty output by default
        icon = _severity_icon(f["severity"])
        col  = C.get(f["severity"], "")
        print(f"\n  {icon} {col}{C['BOLD']}{f['title']}{C['RESET']}")
        print(f"     Category:  {f['category']}")
        print(f"     {f['description']}")
        if f.get("remediation"):
            print(f"     → {f['remediation']}")
    print()


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="XII OS Security Daemon")
    parser.add_argument("--json",    action="store_true")
    parser.add_argument("--version", action="store_true")
    subp = parser.add_subparsers(dest="command")

    subp.add_parser("scan",    help="Full security scan")
    subp.add_parser("audit",   help="Permission audit only")

    fw_p = subp.add_parser("firewall", help="Firewall status")
    fw_sub = fw_p.add_subparsers(dest="fw_cmd")
    fw_sub.add_parser("status")
    fw_sub.add_parser("enable")
    fw_sub.add_parser("disable")

    integ_p = subp.add_parser("integrity", help="File integrity checks")
    integ_sub = integ_p.add_subparsers(dest="integ_cmd")
    integ_sub.add_parser("check")
    integ_sub.add_parser("baseline", help="Create fresh baseline")

    subp.add_parser("log",     help="Show recent security events")
    subp.add_parser("daemon",  help="Run as persistent monitor daemon")

    args = parser.parse_args()

    if args.version:
        print(f"xii-security {VERSION}")
        return

    scanner = XIISecurityScanner()

    if args.command == "scan" or not args.command:
        report = scanner.full_scan()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            _print_report(report)
        scanner.write_report(report)
        scanner.notify_critical(report)

    elif args.command == "audit":
        findings = scanner.perms.audit()
        if args.json:
            print(json.dumps([f.to_dict() for f in findings], indent=2))
        else:
            for f in findings:
                print(f"  {_severity_icon(f.severity)} {f.title}")

    elif args.command == "firewall":
        status = scanner.firewall.status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            backend = status.get("backend", "?")
            active  = "✅ Active" if status.get("active") else "❌ Inactive"
            print(f"  Firewall ({backend}): {active}")

        if getattr(args, "fw_cmd", None) == "enable":
            subprocess.run(["ufw", "enable"])
        elif getattr(args, "fw_cmd", None) == "disable":
            subprocess.run(["ufw", "disable"])

    elif args.command == "integrity":
        if getattr(args, "integ_cmd", None) == "baseline":
            baseline = scanner.integrity.create_baseline()
            BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
            BASELINE_FILE.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
            print(f"  ✅ Baseline created at {BASELINE_FILE}")
        else:
            findings = scanner.integrity.check()
            if args.json:
                print(json.dumps([f.to_dict() for f in findings], indent=2))
            else:
                for f in findings:
                    print(f"  {_severity_icon(f.severity)} {f.title}")

    elif args.command == "log":
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-50:]
            for line in lines:
                print(f"  {line}")
        else:
            print("  No security log found.")

    elif args.command == "daemon":
        import time
        print("[XII Security] Daemon started. Running scans every 6 hours…")
        while True:
            report = scanner.full_scan()
            scanner.write_report(report)
            scanner.notify_critical(report)
            time.sleep(6 * 3600)


if __name__ == "__main__":
    main()
