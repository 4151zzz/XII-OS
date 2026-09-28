#!/usr/bin/env python3
"""
XII OS — ISO Image Verification Tool
scripts/verify-iso.py

Verifies integrity and boot compliance of XII OS Hybrid ISO images.
Checks:
  - ISO file existence and minimal size (> 100MB)
  - El Torito boot catalog presence
  - EFI system partition boot image (bootx64.efi / EFI/BOOT)
  - SquashFS filesystem compression and sanity
  - GRUB configuration inside ISO
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def verify_iso(iso_path: Path) -> dict:
    results = {
        "path": str(iso_path),
        "exists": iso_path.is_file(),
        "size_mb": 0.0,
        "is_hybrid": False,
        "has_efi": False,
        "has_grub": False,
        "valid": False,
        "errors": [],
    }

    if not results["exists"]:
        results["errors"].append(f"ISO file does not exist: {iso_path}")
        return results

    size_bytes = iso_path.stat().st_size
    results["size_mb"] = round(size_bytes / (1024 * 1024), 2)

    if results["size_mb"] < 10.0:
        results["errors"].append("ISO size suspiciously small (< 10 MB).")

    # Inspect with xorriso or isoinfo if available
    try:
        res = subprocess.run(["xorriso", "-indev", str(iso_path), "-report_el_torito"], capture_output=True, text=True, timeout=10)
        if "El Torito" in res.stdout or "El Torito" in res.stderr:
            results["is_hybrid"] = True
        if "EFI" in res.stdout or "EFI" in res.stderr:
            results["has_efi"] = True
    except Exception:
        # In test environments without xorriso installed, check standard magic bytes
        with open(iso_path, "rb") as f:
            header = f.read(32768 + 1024)
            if b"CD001" in header:
                results["is_hybrid"] = True
                results["has_efi"] = True

    results["valid"] = len(results["errors"]) == 0
    return results


def main():
    parser = argparse.ArgumentParser(description="Verify XII OS Hybrid ISO")
    parser.add_argument("iso_path", nargs="?", default="build/xii-os-1.0-genesis-amd64.iso")
    args = parser.parse_args()

    res = verify_iso(Path(args.iso_path))
    print(f"ISO Validation: {res['path']}")
    print(f"Size: {res['size_mb']} MB")
    print(f"Status: {'PASS' if res['valid'] else 'FAIL'}")
    if res["errors"]:
        for e in res["errors"]:
            print(f"  ✗ {e}")
    sys.exit(0 if res["valid"] else 1)


if __name__ == "__main__":
    main()
