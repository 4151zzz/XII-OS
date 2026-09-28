"""
XII OS — Phase 12 Release Candidate Tests
tests/test_release_candidate.py

Validates:
  - release-manifest.json specification & completeness
  - xii-validator.py end-to-end multi-phase verification
  - 100% readiness score across all 12 Phases
  - Documentation completeness (USER_GUIDE.md, RELEASE_NOTES_1.0.md, ROADMAP.md, README.md)

Run with: python -m pytest tests/test_release_candidate.py -v
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
def release_dir(project_root) -> Path:
    return project_root / "system" / "release"

@pytest.fixture
def doc_dir(project_root) -> Path:
    return project_root / "documentation"


# ─────────────────────────────────────────────────────────────
# 1. Release Manifest Validation
# ─────────────────────────────────────────────────────────────
class TestReleaseManifest:
    @pytest.fixture
    def manifest(self, release_dir) -> dict:
        path = release_dir / "release-manifest.json"
        assert path.is_file(), "release-manifest.json must exist"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_version_and_codename(self, manifest):
        assert manifest.get("version") == "1.0.0-rc1"
        assert manifest.get("codename") == "Genesis"
        assert manifest.get("target_architecture") == "x86-64"

    def test_system_requirements(self, manifest):
        req = manifest.get("system_requirements", {})
        assert "minimum" in req
        assert "recommended" in req
        assert req["minimum"]["ram_mb"] >= 2048

    def test_all_12_phases_complete_in_manifest(self, manifest):
        phases = manifest.get("phases_status", {})
        assert len(phases) == 12
        for phase_name, status in phases.items():
            assert status == "COMPLETE", f"Phase {phase_name} must be marked COMPLETE in manifest"


# ─────────────────────────────────────────────────────────────
# 2. End-to-End System Validator
# ─────────────────────────────────────────────────────────────
class TestSystemValidator:
    def test_validator_ast(self, release_dir):
        code = (release_dir / "xii-validator.py").read_text(encoding="utf-8")
        tree = ast.parse(code)
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "SystemReleaseValidator" in classes

    def test_validator_execution_100_percent(self, release_dir, project_root):
        import importlib.util
        spec = importlib.util.spec_from_file_location("xii_validator", release_dir / "xii-validator.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        val = mod.SystemReleaseValidator(project_root)
        rep = val.validate_all_phases()

        assert rep["readiness_pct"] == 100.0, f"Expected 100% readiness, got {rep['readiness_pct']}%"
        assert rep["all_passed"] is True


# ─────────────────────────────────────────────────────────────
# 3. Documentation Completeness
# ─────────────────────────────────────────────────────────────
class TestDocumentation:
    def test_user_guide_exists_and_populated(self, doc_dir):
        path = doc_dir / "USER_GUIDE.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "Keybindings" in text or "คีย์ลัด" in text
        assert "XII Lite" in text
        assert "XII Standard" in text
        assert "XII Performance" in text
        assert "AI Assistant" in text

    def test_release_notes_exists(self, doc_dir):
        path = doc_dir / "RELEASE_NOTES_1.0.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "Genesis" in text
        assert "Linux 6.8" in text
        assert "System Requirements" in text

    def test_roadmap_all_phases_complete(self, doc_dir):
        text = (doc_dir / "ROADMAP.md").read_text(encoding="utf-8")
        assert "Phase 1: Bootable Linux base" in text
        assert "Phase 12: XII OS 1.0 Release Candidate" in text
        assert "✅ COMPLETE" in text

    def test_readme_all_phases_complete(self, project_root):
        text = (project_root / "README.md").read_text(encoding="utf-8")
        assert "| **Phase 12** | XII OS 1.0 Release Candidate | **✅ COMPLETE** |" in text
