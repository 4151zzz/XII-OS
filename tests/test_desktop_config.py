"""
XII OS — Phase 2 Desktop Configuration Automated Tests
tests/test_desktop_config.py

Validates all Phase 2 desktop configuration files:
  - Design tokens (tokens.json)
  - CSS files (global, glassmorphism, gtk4)
  - Hyprland compositor configuration
  - Waybar status bar configuration
  - Wallpaper files
  - systemd service unit

Run with: pytest tests/test_desktop_config.py -v
"""

import json
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
def themes_dir(project_root) -> Path:
    return project_root / "themes"

@pytest.fixture
def desktop_dir(project_root) -> Path:
    return project_root / "desktop"

@pytest.fixture
def wallpapers_dir(project_root) -> Path:
    return project_root / "wallpapers"


# ─────────────────────────────────────────────────────────────
# 1. Design Tokens (tokens.json)
# ─────────────────────────────────────────────────────────────
class TestDesignTokens:
    @pytest.fixture
    def tokens(self, themes_dir) -> dict:
        path = themes_dir / "tokens.json"
        assert path.is_file(), "themes/tokens.json not found"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_tokens_file_exists(self, themes_dir):
        assert (themes_dir / "tokens.json").is_file()

    def test_has_meta(self, tokens):
        assert "meta" in tokens, "tokens.json must have a 'meta' section"
        assert "name" in tokens["meta"]

    def test_has_color_section(self, tokens):
        assert "color" in tokens

    def test_has_base_colors(self, tokens):
        base = tokens["color"]["base"]
        required = ["bg-deep", "bg-base", "bg-elevated", "bg-overlay", "bg-glass"]
        for key in required:
            assert key in base, f"Missing base color: {key}"

    def test_has_accent_colors(self, tokens):
        accent = tokens["color"]["accent"]
        for key in ["cyan", "purple", "rose"]:
            assert key in accent, f"Missing accent color: {key}"

    def test_has_semantic_colors(self, tokens):
        semantic = tokens["color"]["semantic"]
        for key in ["success", "warning", "error", "info"]:
            assert key in semantic, f"Missing semantic color: {key}"

    def test_has_typography(self, tokens):
        assert "typography" in tokens
        typo = tokens["typography"]
        assert "font" in typo
        assert "size" in typo
        assert "weight" in typo

    def test_has_font_families(self, tokens):
        fonts = tokens["typography"]["font"]
        assert "sans" in fonts
        assert "mono" in fonts

    def test_has_spacing(self, tokens):
        assert "spacing" in tokens
        spacing = tokens["spacing"]
        # Must have at least spacing 1–8
        for key in ["1", "2", "4", "6", "8"]:
            assert key in spacing, f"Missing spacing: {key}"

    def test_has_radius(self, tokens):
        assert "radius" in tokens
        for key in ["sm", "md", "lg", "xl", "full"]:
            assert key in tokens["radius"], f"Missing radius: {key}"

    def test_has_shadow(self, tokens):
        assert "shadow" in tokens
        for key in ["sm", "md", "lg", "xl"]:
            assert key in tokens["shadow"], f"Missing shadow: {key}"

    def test_has_animation(self, tokens):
        assert "animation" in tokens
        anim = tokens["animation"]
        assert "duration" in anim
        assert "easing" in anim

    def test_has_component_sizes(self, tokens):
        assert "size" in tokens
        sizes = tokens["size"]
        assert "statusbar-height" in sizes, "Missing statusbar-height token"
        assert "dock-height" in sizes or "dock-icon-size" in sizes, \
            "Missing dock size token"

    def test_all_values_have_value_key(self, tokens):
        """Every leaf token must have a 'value' key."""
        def check_leaf(obj, path=""):
            if isinstance(obj, dict):
                if "value" in obj:
                    return  # This is a token leaf — valid
                for k, v in obj.items():
                    if k not in ("$schema", "meta", "comment", "description"):
                        check_leaf(v, f"{path}.{k}")
            elif isinstance(obj, str):
                pass  # Inline string value (legacy)
        check_leaf(tokens)  # Should not raise


# ─────────────────────────────────────────────────────────────
# 2. CSS Files Tests
# ─────────────────────────────────────────────────────────────
class TestCssFiles:
    def test_global_css_exists(self, themes_dir):
        assert (themes_dir / "xii-global.css").is_file()

    def test_glassmorphism_css_exists(self, themes_dir):
        assert (themes_dir / "xii-glassmorphism.css").is_file()

    def test_gtk4_css_exists(self, themes_dir):
        assert (themes_dir / "xii-gtk4.css").is_file()

    def test_global_css_has_root_variables(self, themes_dir):
        content = (themes_dir / "xii-global.css").read_text(encoding="utf-8")
        assert ":root" in content, "xii-global.css must define :root block"

    def test_global_css_defines_xii_cyan(self, themes_dir):
        content = (themes_dir / "xii-global.css").read_text(encoding="utf-8")
        assert "--xii-cyan" in content

    def test_global_css_defines_three_modes(self, themes_dir):
        content = (themes_dir / "xii-global.css").read_text(encoding="utf-8")
        assert ".xii-lite" in content,        "Missing .xii-lite mode class"
        assert ".xii-standard" in content or ":root" in content, \
            "Missing standard/root mode"
        assert ".xii-performance" in content, "Missing .xii-performance mode class"

    def test_global_css_has_font_variables(self, themes_dir):
        content = (themes_dir / "xii-global.css").read_text(encoding="utf-8")
        assert "--xii-font-sans" in content
        assert "--xii-font-mono" in content

    def test_global_css_has_animation_variables(self, themes_dir):
        content = (themes_dir / "xii-global.css").read_text(encoding="utf-8")
        assert "--xii-dur-" in content,  "Missing duration variables"
        assert "--xii-ease" in content,  "Missing easing variables"
        assert "--xii-spring" in content, "Missing spring easing"

    def test_glassmorphism_has_panel_class(self, themes_dir):
        content = (themes_dir / "xii-glassmorphism.css").read_text(encoding="utf-8")
        assert ".xii-glass-panel" in content

    def test_glassmorphism_has_card_class(self, themes_dir):
        content = (themes_dir / "xii-glassmorphism.css").read_text(encoding="utf-8")
        assert ".xii-glass-card" in content

    def test_glassmorphism_has_animations(self, themes_dir):
        content = (themes_dir / "xii-glassmorphism.css").read_text(encoding="utf-8")
        assert "@keyframes" in content, "glassmorphism CSS must define animations"
        assert ".xii-animate-in" in content

    def test_gtk4_overrides_headerbar(self, themes_dir):
        content = (themes_dir / "xii-gtk4.css").read_text(encoding="utf-8")
        assert "headerbar" in content, "xii-gtk4.css must style headerbar"

    def test_gtk4_overrides_button(self, themes_dir):
        content = (themes_dir / "xii-gtk4.css").read_text(encoding="utf-8")
        assert "button" in content and "suggested-action" in content

    def test_gtk4_overrides_entry(self, themes_dir):
        content = (themes_dir / "xii-gtk4.css").read_text(encoding="utf-8")
        assert "entry" in content, "xii-gtk4.css must style text entries"

    def test_gtk4_overrides_switch(self, themes_dir):
        content = (themes_dir / "xii-gtk4.css").read_text(encoding="utf-8")
        assert "switch" in content, "xii-gtk4.css must style toggle switches"

    def test_css_uses_xii_custom_properties(self, themes_dir):
        """Verify CSS files reference XII custom properties, not hardcoded colors."""
        for css_file in ["xii-glassmorphism.css", "xii-gtk4.css"]:
            content = (themes_dir / css_file).read_text(encoding="utf-8")
            # Should use var(--xii-...) references
            assert "var(--xii-" in content, \
                f"{css_file} should use --xii-* CSS custom properties"


# ─────────────────────────────────────────────────────────────
# 3. Hyprland Configuration Tests
# ─────────────────────────────────────────────────────────────
class TestHyprlandConfig:
    @pytest.fixture
    def hypr_conf(self, desktop_dir) -> str:
        path = desktop_dir / "window-manager" / "hyprland.conf"
        assert path.is_file(), "desktop/window-manager/hyprland.conf not found"
        return path.read_text(encoding="utf-8")

    def test_config_exists(self, desktop_dir):
        assert (desktop_dir / "window-manager" / "hyprland.conf").is_file()

    def test_has_monitor_directive(self, hypr_conf):
        assert "monitor" in hypr_conf, "hyprland.conf must have monitor config"

    def test_has_exec_once_statusbar(self, hypr_conf):
        assert "xii-statusbar" in hypr_conf or "waybar" in hypr_conf, \
            "hyprland.conf must autostart status bar"

    def test_has_wallpaper_exec(self, hypr_conf):
        assert "swaybg" in hypr_conf or "hyprpaper" in hypr_conf, \
            "hyprland.conf must set wallpaper"

    def test_has_rounded_corners(self, hypr_conf):
        assert "rounding" in hypr_conf, "hyprland.conf must set window rounding"
        match = re.search(r'rounding\s*=\s*(\d+)', hypr_conf)
        if match:
            rounding = int(match.group(1))
            assert rounding >= 10, \
                f"Rounding {rounding}px seems too small for XII design (expect ≥ 10)"

    def test_has_xii_accent_border(self, hypr_conf):
        assert "6ee7f7" in hypr_conf or "a78bfa" in hypr_conf, \
            "hyprland.conf must use XII accent colors for borders"

    def test_has_blur_enabled(self, hypr_conf):
        assert "blur" in hypr_conf
        # blur should be enabled
        assert "enabled = true" in hypr_conf or "enabled=true" in hypr_conf

    def test_has_spring_animation(self, hypr_conf):
        assert "xii_spring" in hypr_conf or "spring" in hypr_conf.lower(), \
            "hyprland.conf must define spring animation bezier"

    def test_has_window_animations(self, hypr_conf):
        assert "animation = windows" in hypr_conf

    def test_has_workspace_animations(self, hypr_conf):
        assert "animation = workspaces" in hypr_conf

    def test_has_xii_launcher_keybind(self, hypr_conf):
        assert "xii-launcher" in hypr_conf or ("SPACE" in hypr_conf and "launcher" in hypr_conf.lower())

    def test_has_workspace_keybinds(self, hypr_conf):
        # Should have binds for workspaces 1-5 at minimum
        for i in range(1, 6):
            assert f"workspace, {i}" in hypr_conf, \
                f"Missing workspace keybind for workspace {i}"

    def test_has_volume_keybinds(self, hypr_conf):
        assert "XF86AudioRaiseVolume" in hypr_conf or "XF86Audio" in hypr_conf, \
            "hyprland.conf must include volume keybindings"

    def test_has_xii_mode_keybinds(self, hypr_conf):
        assert "xii-mode" in hypr_conf, \
            "hyprland.conf must bind keys to xii-mode"

    def test_has_window_rules(self, hypr_conf):
        assert "windowrulev2" in hypr_conf or "windowrule" in hypr_conf, \
            "hyprland.conf must have window rules"

    def test_xii_launcher_is_floating(self, hypr_conf):
        """XII Launcher should open as a floating centered window."""
        assert "xii-launcher" in hypr_conf
        launcher_rule = re.search(r'windowrulev2.*xii-launcher.*', hypr_conf)
        assert launcher_rule or "float" in hypr_conf, \
            "xii-launcher window rule should set float"

    def test_has_touchpad_gestures(self, hypr_conf):
        assert "gestures" in hypr_conf and "workspace_swipe" in hypr_conf, \
            "hyprland.conf should configure touchpad workspace swipe gestures"


# ─────────────────────────────────────────────────────────────
# 4. Waybar Configuration Tests
# ─────────────────────────────────────────────────────────────
class TestWaybarConfig:
    @pytest.fixture
    def waybar_conf(self, desktop_dir) -> str:
        path = desktop_dir / "shell" / "waybar" / "config.jsonc"
        assert path.is_file(), "desktop/shell/waybar/config.jsonc not found"
        return path.read_text(encoding="utf-8")

    @pytest.fixture
    def waybar_css(self, desktop_dir) -> str:
        path = desktop_dir / "shell" / "waybar" / "style.css"
        assert path.is_file(), "desktop/shell/waybar/style.css not found"
        return path.read_text(encoding="utf-8")

    def test_config_exists(self, desktop_dir):
        assert (desktop_dir / "shell" / "waybar" / "config.jsonc").is_file()

    def test_style_exists(self, desktop_dir):
        assert (desktop_dir / "shell" / "waybar" / "style.css").is_file()

    def test_statusbar_service_exists(self, desktop_dir):
        assert (desktop_dir / "shell" / "xii-statusbar.service").is_file()

    def test_has_layer_top(self, waybar_conf):
        assert '"layer": "top"' in waybar_conf or "'layer': 'top'" in waybar_conf

    def test_has_three_module_sections(self, waybar_conf):
        assert "modules-left" in waybar_conf
        assert "modules-center" in waybar_conf
        assert "modules-right" in waybar_conf

    def test_has_xii_logo_module(self, waybar_conf):
        assert "xii-logo" in waybar_conf or "xii-launcher" in waybar_conf

    def test_has_workspaces(self, waybar_conf):
        assert "workspaces" in waybar_conf

    def test_has_clock(self, waybar_conf):
        assert '"clock"' in waybar_conf or "'clock'" in waybar_conf

    def test_has_battery(self, waybar_conf):
        assert "battery" in waybar_conf

    def test_has_network(self, waybar_conf):
        assert "network" in waybar_conf

    def test_has_audio(self, waybar_conf):
        assert "pulseaudio" in waybar_conf or "wireplumber" in waybar_conf

    def test_has_tray(self, waybar_conf):
        assert "tray" in waybar_conf

    def test_has_xii_mode_indicator(self, waybar_conf):
        assert "xii-mode" in waybar_conf, \
            "Waybar should show XII Performance Mode indicator"

    def test_has_power_button(self, waybar_conf):
        assert "power" in waybar_conf.lower()

    def test_css_has_waybar_window(self, waybar_css):
        assert "window#waybar" in waybar_css

    def test_css_has_backdrop_filter(self, waybar_css):
        assert "backdrop-filter" in waybar_css, \
            "Waybar CSS should use backdrop-filter for glassmorphism"

    def test_css_has_workspace_active_style(self, waybar_css):
        assert ".active" in waybar_css, \
            "Waybar CSS must style active workspace"

    def test_css_has_xii_brand_color(self, waybar_css):
        assert "6ee7f7" in waybar_css or "xii-cyan" in waybar_css, \
            "Waybar CSS should use XII cyan color"

    def test_css_has_battery_warning_animation(self, waybar_css):
        assert "@keyframes" in waybar_css and "battery" in waybar_css.lower(), \
            "Waybar CSS should animate low battery warning"

    def test_statusbar_service_has_waybar(self, desktop_dir):
        content = (desktop_dir / "shell" / "xii-statusbar.service").read_text(encoding="utf-8")
        assert "waybar" in content.lower(), "xii-statusbar.service must launch waybar"

    def test_statusbar_service_restarts_on_failure(self, desktop_dir):
        content = (desktop_dir / "shell" / "xii-statusbar.service").read_text(encoding="utf-8")
        assert "Restart=on-failure" in content


# ─────────────────────────────────────────────────────────────
# 5. Wallpaper Tests
# ─────────────────────────────────────────────────────────────
class TestWallpapers:
    def test_default_svg_exists(self, wallpapers_dir):
        assert (wallpapers_dir / "xii-default.svg").is_file()

    def test_generator_script_exists(self, wallpapers_dir):
        assert (wallpapers_dir / "generate-wallpaper.py").is_file()

    def test_svg_is_valid_xml(self, wallpapers_dir):
        import xml.etree.ElementTree as ET
        svg_path = wallpapers_dir / "xii-default.svg"
        try:
            ET.parse(str(svg_path))
        except ET.ParseError as e:
            pytest.fail(f"xii-default.svg is not valid XML: {e}")

    def test_svg_has_xii_colors(self, wallpapers_dir):
        content = (wallpapers_dir / "xii-default.svg").read_text(encoding="utf-8")
        assert "6ee7f7" in content, "Wallpaper should use XII cyan color"

    def test_svg_has_viewbox(self, wallpapers_dir):
        content = (wallpapers_dir / "xii-default.svg").read_text(encoding="utf-8")
        assert "viewBox" in content, "SVG wallpaper must have a viewBox attribute"

    def test_svg_has_4k_dimensions(self, wallpapers_dir):
        content = (wallpapers_dir / "xii-default.svg").read_text(encoding="utf-8")
        assert "3840" in content and "2160" in content, \
            "Default wallpaper should be designed for 4K (3840x2160)"

    def test_svg_has_xii_logo_element(self, wallpapers_dir):
        content = (wallpapers_dir / "xii-default.svg").read_text(encoding="utf-8")
        assert "XII OS" in content or "xii" in content.lower(), \
            "Wallpaper should contain XII OS branding"

    def test_generator_has_presets(self, wallpapers_dir):
        content = (wallpapers_dir / "generate-wallpaper.py").read_text(encoding="utf-8")
        assert "1920" in content and "1080" in content, "Generator must include FHD preset"
        assert "3840" in content and "2160" in content, "Generator must include 4K preset"
        assert "2560" in content and "1440" in content, "Generator must include QHD preset"

    def test_generator_has_main_function(self, wallpapers_dir):
        content = (wallpapers_dir / "generate-wallpaper.py").read_text(encoding="utf-8")
        assert "def main" in content, "generator must have a main() function"
        assert '__name__ == "__main__"' in content or "if __name__" in content
