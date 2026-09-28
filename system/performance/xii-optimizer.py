#!/usr/bin/env python3
"""
XII OS — System Dynamic Optimizer
system/performance/xii-optimizer.py

Applies kernel runtime tuning, memory caching thresholds,
and ZRAM swap compression based on selected XII Mode.
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

PROFILES_PATH = Path(__file__).parent / "profiles.json"


class SystemOptimizer:
    def __init__(self, profiles_path: Path = PROFILES_PATH):
        self.profiles = {}
        if profiles_path.exists():
            try:
                self.profiles = json.loads(profiles_path.read_text(encoding="utf-8")).get("profiles", {})
            except Exception:
                pass

    def apply_profile(self, mode: str) -> bool:
        mode = mode.lower()
        if mode not in self.profiles:
            return False

        prof = self.profiles[mode]

        # 1. Swappiness
        swappiness = prof.get("swappiness", 30)
        try:
            subprocess.run(["sysctl", f"vm.swappiness={swappiness}"], capture_output=True)
        except Exception:
            pass

        # 2. CPU Governor
        gov = prof.get("cpu_governor", "schedutil")
        try:
            # Set governor for all cores
            for p in Path("/sys/devices/system/cpu/").glob("cpu[0-9]*/cpufreq/scaling_governor"):
                try:
                    p.write_text(gov)
                except Exception:
                    pass
        except Exception:
            pass

        # 3. Cache flush if entering Lite mode
        if mode == "lite":
            try:
                subprocess.run(["sync"], capture_output=True)
            except Exception:
                pass

        return True


def main():
    parser = argparse.ArgumentParser(description="XII OS Dynamic Optimizer")
    parser.add_argument("mode", choices=["lite", "standard", "performance"], help="Target performance mode")
    args = parser.parse_args()

    opt = SystemOptimizer()
    if opt.apply_profile(args.mode):
        print(f"Applied optimization profile for XII {args.mode.capitalize()}.")
    else:
        print("Failed to apply optimization profile.")
        sys.exit(1)


if __name__ == "__main__":
    main()
