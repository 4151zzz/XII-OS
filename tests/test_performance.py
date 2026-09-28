"""
XII OS — Phase 11 Performance Optimization Tests
tests/test_performance.py

Validates:
  - profiles.json schema & SLA thresholds
  - xii-bench.py profiler & benchmarks
  - xii-optimizer.py runtime tuner
  - SLA constraints: Boot time < 8s, Lite RAM < 350MB

Run with: python -m pytest tests/test_performance.py -v
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
def perf_dir(project_root) -> Path:
    return project_root / "system" / "performance"


# ─────────────────────────────────────────────────────────────
# 1. File Structure Checks
# ─────────────────────────────────────────────────────────────
class TestPerformanceFiles:
    def test_profiles_json_exists(self, perf_dir):
        assert (perf_dir / "profiles.json").is_file()

    def test_bench_script_exists(self, perf_dir):
        assert (perf_dir / "xii-bench.py").is_file()

    def test_optimizer_script_exists(self, perf_dir):
        assert (perf_dir / "xii-optimizer.py").is_file()


# ─────────────────────────────────────────────────────────────
# 2. Profiles JSON SLA Thresholds
# ─────────────────────────────────────────────────────────────
class TestProfilesConfig:
    @pytest.fixture
    def profiles_data(self, perf_dir) -> dict:
        path = perf_dir / "profiles.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_has_three_profiles(self, profiles_data):
        profs = profiles_data.get("profiles", {})
        assert "lite" in profs
        assert "standard" in profs
        assert "performance" in profs

    def test_lite_ram_sla(self, profiles_data):
        lite = profiles_data["profiles"]["lite"]
        assert lite.get("target_idle_ram_mb") <= 350, "Lite idle RAM target must be <= 350MB"

    def test_boot_sla_under_eight_seconds(self, profiles_data):
        for name, prof in profiles_data["profiles"].items():
            assert prof.get("max_boot_seconds") <= 8.0, f"{name} boot SLA must be <= 8.0s"

    def test_governor_assignments(self, profiles_data):
        profs = profiles_data["profiles"]
        assert profs["lite"]["cpu_governor"] == "powersave"
        assert profs["performance"]["cpu_governor"] == "performance"


# ─────────────────────────────────────────────────────────────
# 3. Benchmark Suite AST & Functionality
# ─────────────────────────────────────────────────────────────
class TestBenchAST:
    @pytest.fixture
    def tree(self, perf_dir) -> ast.AST:
        code = (perf_dir / "xii-bench.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_classes(self, tree):
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "PerformanceProfiler" in classes

    def test_methods(self, tree):
        methods = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and n.name == "PerformanceProfiler":
                methods = [m.name for m in n.body if isinstance(m, ast.FunctionDef)]
        assert "measure_boot_time" in methods
        assert "measure_memory_usage" in methods
        assert "benchmark_memory_bandwidth" in methods
        assert "run_full_benchmark" in methods


class TestBenchFunctionality:
    @pytest.fixture
    def profiler(self, perf_dir):
        import importlib.util
        spec = importlib.util.spec_from_file_location("xii_bench", perf_dir / "xii-bench.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.PerformanceProfiler(perf_dir / "profiles.json")

    def test_boot_measurement(self, profiler):
        res = profiler.measure_boot_time()
        assert "total_seconds" in res
        assert res["total_seconds"] < 8.0
        assert res["sla_passed"] is True

    def test_memory_measurement(self, profiler):
        res = profiler.measure_memory_usage()
        assert "used_mb" in res
        assert "lite_sla_passed" in res

    def test_bandwidth_measurement(self, profiler):
        bw = profiler.benchmark_memory_bandwidth(size_mb=8)
        assert bw > 0.0

    def test_full_benchmark(self, profiler):
        rep = profiler.run_full_benchmark()
        assert "boot_metrics" in rep
        assert "memory_metrics" in rep
        assert rep["all_slas_met"] is True


# ─────────────────────────────────────────────────────────────
# 4. Dynamic Optimizer AST & Functionality
# ─────────────────────────────────────────────────────────────
class TestOptimizer:
    @pytest.fixture
    def optimizer(self, perf_dir):
        import importlib.util
        spec = importlib.util.spec_from_file_location("xii_optimizer", perf_dir / "xii-optimizer.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.SystemOptimizer(perf_dir / "profiles.json")

    def test_apply_valid_profiles(self, optimizer):
        assert optimizer.apply_profile("lite") is True
        assert optimizer.apply_profile("standard") is True
        assert optimizer.apply_profile("performance") is True

    def test_apply_invalid_profile(self, optimizer):
        assert optimizer.apply_profile("ultra_turbo_invalid") is False
