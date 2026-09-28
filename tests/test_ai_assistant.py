"""
XII OS — Phase 9 AI Assistant & Permission Gate Tests
tests/test_ai_assistant.py

Validates:
  - xii-ai-core.py (IntentMatcher, PermissionGate, SystemDiagnostics)
  - xii-ai-intents.json schema & patterns
  - xii-ai.service systemd unit
  - xii-ai-assistant.py HUD widget
  - Permission gating mechanisms & Thai NLP matching

Run with: python -m pytest tests/test_ai_assistant.py -v
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
def ai_sys_dir(project_root) -> Path:
    return project_root / "system" / "ai"

@pytest.fixture
def ai_desk_dir(project_root) -> Path:
    return project_root / "desktop" / "ai"


# ─────────────────────────────────────────────────────────────
# 1. File Structure Checks
# ─────────────────────────────────────────────────────────────
class TestAIFiles:
    def test_core_engine_exists(self, ai_sys_dir):
        assert (ai_sys_dir / "xii-ai-core.py").is_file()

    def test_intents_json_exists(self, ai_sys_dir):
        assert (ai_sys_dir / "xii-ai-intents.json").is_file()

    def test_service_exists(self, ai_sys_dir):
        assert (ai_sys_dir / "xii-ai.service").is_file()

    def test_gui_assistant_exists(self, ai_desk_dir):
        assert (ai_desk_dir / "xii-ai-assistant.py").is_file()

    def test_gui_css_exists(self, ai_desk_dir):
        assert (ai_desk_dir / "xii-ai-assistant.css").is_file()

    def test_desktop_file_exists(self, ai_desk_dir):
        assert (ai_desk_dir / "xii-ai-assistant.desktop").is_file()


# ─────────────────────────────────────────────────────────────
# 2. Intents Schema & Patterns
# ─────────────────────────────────────────────────────────────
class TestIntentsSchema:
    @pytest.fixture
    def intents_data(self, ai_sys_dir) -> dict:
        path = ai_sys_dir / "xii-ai-intents.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_has_version(self, intents_data):
        assert "version" in intents_data

    def test_has_intents_list(self, intents_data):
        assert "intents" in intents_data
        assert len(intents_data["intents"]) >= 4

    def test_gated_actions_present(self, intents_data):
        gated = [i for i in intents_data["intents"] if i.get("gate_required") is True]
        assert len(gated) >= 1, "Must contain gated high-impact actions"


# ─────────────────────────────────────────────────────────────
# 3. Core Engine AST Validation
# ─────────────────────────────────────────────────────────────
class TestAICoreAST:
    @pytest.fixture
    def tree(self, ai_sys_dir) -> ast.AST:
        code = (ai_sys_dir / "xii-ai-core.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_classes(self, tree):
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "PermissionGate" in classes
        assert "SystemDiagnostics" in classes
        assert "IntentMatcher" in classes
        assert "XIIAssistantEngine" in classes

    def test_gate_methods(self, tree):
        methods = []
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and n.name == "PermissionGate":
                methods = [m.name for m in n.body if isinstance(m, ast.FunctionDef)]
        assert "requires_confirmation" in methods
        assert "request_approval" in methods
        assert "verify_and_execute" in methods


# ─────────────────────────────────────────────────────────────
# 4. Engine Functionality & Permission Gate Logic
# ─────────────────────────────────────────────────────────────
class TestAIFunctionality:
    @pytest.fixture
    def engine(self, project_root):
        import importlib.util
        spec_path = project_root / "system" / "ai" / "xii-ai-core.py"
        spec = importlib.util.spec_from_file_location("xii_ai_core", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.XIIAssistantEngine()

    def test_ram_query_matching(self, engine):
        res = engine.handle_query("ใครกิน ram")
        assert res["type"] == "text"
        assert res["requires_gate"] is False
        assert "RAM" in res["response"] or "processes" in res["response"]

    def test_wifi_query_matching(self, engine):
        res = engine.handle_query("ทำไม wifi ใช้ไม่ได้")
        assert res["type"] == "text"
        assert res["requires_gate"] is False

    def test_install_requires_gate(self, engine):
        res = engine.handle_query("ติดตั้งโปรแกรม vlc")
        assert res["type"] == "gate_prompt"
        assert res["requires_gate"] is True
        assert "gate_data" in res

    def test_permission_gate_approval(self, engine):
        token = "gate_test_1"
        action = {"description": "Test action", "requires_root": True, "impact": "high"}
        engine.gate.request_approval(token, action)

        # Cancel
        ok, msg = engine.gate.verify_and_execute(token, approved=False)
        assert ok is False

        # Re-request and approve
        engine.gate.request_approval(token, action)
        ok, msg = engine.gate.verify_and_execute(token, approved=True)
        assert ok is True


# ─────────────────────────────────────────────────────────────
# 5. Desktop Assistant AST & Desktop Entry
# ─────────────────────────────────────────────────────────────
class TestDesktopAssistant:
    @pytest.fixture
    def tree(self, ai_desk_dir) -> ast.AST:
        code = (ai_desk_dir / "xii-ai-assistant.py").read_text(encoding="utf-8")
        return ast.parse(code)

    def test_gui_classes(self, tree):
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "AssistantClient" in classes
        assert "XIIAssistantApp" in classes
        assert "XIIAssistantWindow" in classes

    def test_desktop_file(self, ai_desk_dir):
        df = (ai_desk_dir / "xii-ai-assistant.desktop").read_text(encoding="utf-8")
        assert "[Desktop Entry]" in df
        assert "Name=XII AI Assistant" in df
        assert "Exec=" in df
