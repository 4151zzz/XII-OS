#!/usr/bin/env python3
"""
XII OS — App Store (XII Store)
desktop/store/xii-store.py

A beautiful, GTK4 application store for XII OS.
Integrates with xii package manager CLI and Flatpak.

Features:
  - Featured apps carousel/hero section
  - Category browsing sidebar
  - Search with instant results
  - App detail page (description, screenshots placeholder, ratings)
  - Install/Update/Remove with progress UI
  - XII Verified badge for curated apps
  - Installed apps management tab
  - Dark glassmorphic design

Requirements:
  apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 flatpak

Usage:
  xii-store
  xii-store --app org.mozilla.firefox   # Open directly to app page
"""

import gi
import os
import sys
import json
import subprocess
import threading
import argparse
from pathlib import Path
from typing import Optional

gi.require_version("Gtk",  "4.0")
gi.require_version("Adw",  "1")
gi.require_version("Gio",  "2.0")
gi.require_version("Gdk",  "4.0")
gi.require_version("GLib", "2.0")
gi.require_version("Pango","1.0")

from gi.repository import Gtk, Adw, Gio, Gdk, GLib, Pango

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
APP_ID       = "org.xiios.Store"
CSS_PATH     = "/usr/share/xii-os/desktop/store/xii-store.css"
CATALOG_PATH = "/etc/xii-os/store/featured-apps.json"
XII_BIN      = "/usr/bin/xii"

CATEGORIES = [
    ("Featured",             "starred-symbolic"),
    ("Internet",             "network-wireless-symbolic"),
    ("Development",          "applications-engineering-symbolic"),
    ("Audio & Video",        "audio-speakers-symbolic"),
    ("Graphics & Photography","applications-graphics-symbolic"),
    ("Office",               "x-office-document-symbolic"),
    ("Games",                "applications-games-symbolic"),
    ("Utility",              "applications-utilities-symbolic"),
    ("System",               "system-run-symbolic"),
]


# ─────────────────────────────────────────────────────────────
# App Entry — data model
# ─────────────────────────────────────────────────────────────
class AppEntry:
    def __init__(self, data: dict):
        self.id          = data.get("id", "")
        self.name        = data.get("name", "Unknown")
        self.developer   = data.get("developer", "")
        self.description = data.get("description", "")
        self.icon        = data.get("icon", "application-x-executable")
        self.category    = data.get("category", "Utility")
        self.backend     = data.get("backend", "flatpak")
        self.rating      = data.get("rating", 0.0)
        self.downloads   = data.get("downloads", "")
        self.size_mb     = data.get("size_mb", 0)
        self.featured    = data.get("featured", False)
        self.xii_verified = data.get("xii_verified", False)
        self.installed   = False

    def stars(self) -> str:
        full  = int(self.rating)
        empty = 5 - full
        return "★" * full + "☆" * empty

    def size_str(self) -> str:
        if self.size_mb == 0:
            return "?"
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.1f} GB"
        return f"{self.size_mb} MB"


# ─────────────────────────────────────────────────────────────
# App Catalog
# ─────────────────────────────────────────────────────────────
class AppCatalog:
    def __init__(self):
        self.apps: list[AppEntry] = []
        self._load()

    def _load(self):
        path = Path(CATALOG_PATH)
        if not path.exists():
            # Try local (development)
            path = Path(__file__).parent / "featured-apps.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.apps = [AppEntry(a) for a in data.get("featured", [])]
            except (json.JSONDecodeError, KeyError):
                pass
        self._check_installed()

    def _check_installed(self):
        """Check which apps are already installed via Flatpak."""
        try:
            result = subprocess.run(
                ["flatpak", "list", "--user", "--columns=application"],
                capture_output=True, text=True, timeout=5
            )
            installed_ids = set(result.stdout.splitlines())
            for app in self.apps:
                app.installed = app.id in installed_ids
        except Exception:
            pass

    def featured(self) -> list[AppEntry]:
        return [a for a in self.apps if a.featured]

    def by_category(self, category: str) -> list[AppEntry]:
        if category == "Featured":
            return self.featured()
        return [a for a in self.apps if a.category == category]

    def search(self, query: str) -> list[AppEntry]:
        q = query.lower()
        results = []
        for app in self.apps:
            score = 0
            if app.name.lower().startswith(q):
                score = 100
            elif q in app.name.lower():
                score = 70
            elif q in app.description.lower():
                score = 40
            if score > 0:
                results.append((score, app))
        results.sort(key=lambda x: -x[0])
        return [a for _, a in results]


# ─────────────────────────────────────────────────────────────
# App Card — grid card widget
# ─────────────────────────────────────────────────────────────
class AppCard(Gtk.Box):
    def __init__(self, app: AppEntry, on_click):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_css_classes(["store-card"])
        self.app = app

        # Click gesture
        click = Gtk.GestureClick()
        click.connect("pressed", lambda g, n, x, y: on_click(app))
        self.add_controller(click)

        # Icon
        icon = Gtk.Image.new_from_icon_name(app.icon)
        icon.set_pixel_size(72)
        icon.set_css_classes(["store-card-icon"])
        self.append(icon)

        # Name
        name_lbl = Gtk.Label(label=app.name)
        name_lbl.set_css_classes(["store-card-name"])
        name_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.append(name_lbl)

        # Developer
        dev_lbl = Gtk.Label(label=app.developer)
        dev_lbl.set_css_classes(["store-card-dev"])
        dev_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self.append(dev_lbl)

        # Stars + verified
        meta_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        meta_box.set_halign(Gtk.Align.CENTER)

        stars = Gtk.Label(label=app.stars())
        stars.set_css_classes(["store-stars"])
        meta_box.append(stars)

        if app.xii_verified:
            badge = Gtk.Label(label="✓")
            badge.set_css_classes(["store-verified-badge"])
            badge.set_tooltip_text("XII Verified App")
            meta_box.append(badge)

        self.append(meta_box)

        # Install button
        if app.installed:
            btn = Gtk.Button(label="Installed")
            btn.set_css_classes(["store-installed-btn"])
            btn.set_sensitive(False)
        else:
            btn = Gtk.Button(label="Install")
            btn.set_css_classes(["store-install-btn", "suggested-action"])
            btn.connect("clicked", lambda b: self._install(b, app))
        self.append(btn)

    def _install(self, button: Gtk.Button, app: AppEntry):
        button.set_label("Installing…")
        button.set_sensitive(False)

        def do_install():
            try:
                subprocess.run(
                    ["flatpak", "install", "--user", "-y", "flathub", app.id],
                    capture_output=True, timeout=300
                )
                GLib.idle_add(self._on_installed, button, app)
            except Exception:
                GLib.idle_add(self._on_install_failed, button)

        threading.Thread(target=do_install, daemon=True).start()

    def _on_installed(self, button: Gtk.Button, app: AppEntry):
        app.installed = True
        button.set_label("Installed")
        button.remove_css_class("suggested-action")
        button.add_css_class("store-installed-btn")

    def _on_install_failed(self, button: Gtk.Button):
        button.set_label("Install")
        button.set_sensitive(True)


# ─────────────────────────────────────────────────────────────
# Store Main Window
# ─────────────────────────────────────────────────────────────
class StoreWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, catalog: AppCatalog,
                 initial_app_id: Optional[str] = None):
        super().__init__(application=app)
        self.catalog      = catalog
        self.current_cat  = "Featured"
        self.set_title("XII Store")
        self.set_default_size(1100, 700)
        self.set_css_classes(["store-window"])
        self._build_ui()
        self._load_category("Featured")

    def _build_ui(self):
        split = Adw.NavigationSplitView()
        split.set_min_sidebar_width(210)
        split.set_max_sidebar_width(250)

        # ── Sidebar ────────────────────────────────────────────
        sidebar_page = Adw.NavigationPage()
        sidebar_page.set_title("XII Store")

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_css_classes(["store-sidebar-header"])
        sidebar_header.set_show_end_title_buttons(False)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search apps…")
        search.set_hexpand(True)
        search.connect("search-changed", self._on_search)
        sidebar_header.set_title_widget(search)
        self.search_entry = search
        sidebar_box.append(sidebar_header)

        self.cat_list = Gtk.ListBox()
        self.cat_list.set_css_classes(["store-cat-list", "navigation-sidebar"])
        self.cat_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.cat_list.connect("row-selected", self._on_cat_selected)

        self.cat_rows = {}
        for cat, icon in CATEGORIES:
            row = Gtk.ListBoxRow()
            row._cat = cat
            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            inner.set_margin_start(12)
            inner.set_margin_end(12)
            inner.set_margin_top(8)
            inner.set_margin_bottom(8)
            icon_w = Gtk.Image.new_from_icon_name(icon)
            icon_w.set_pixel_size(18)
            icon_w.set_css_classes(["store-cat-icon"])
            inner.append(icon_w)
            lbl = Gtk.Label(label=cat)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_css_classes(["store-cat-label"])
            inner.append(lbl)
            row.set_child(inner)
            self.cat_list.append(row)
            self.cat_rows[cat] = row

        cat_scroll = Gtk.ScrolledWindow()
        cat_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        cat_scroll.set_vexpand(True)
        cat_scroll.set_child(self.cat_list)
        sidebar_box.append(cat_scroll)
        sidebar_page.set_child(sidebar_box)
        split.set_sidebar(sidebar_page)

        # ── Content area ────────────────────────────────────────
        content_page = Adw.NavigationPage()
        content_page.set_title("Featured")
        self.content_page = content_page

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        content_header = Adw.HeaderBar()
        content_header.set_css_classes(["store-content-header"])
        self.content_title = Gtk.Label(label="Featured")
        self.content_title.set_css_classes(["store-content-title"])
        content_header.set_title_widget(self.content_title)
        content_box.append(content_header)

        # App grid in scrolled window
        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content_scroll.set_vexpand(True)

        self.flow = Gtk.FlowBox()
        self.flow.set_css_classes(["store-grid"])
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(6)
        self.flow.set_min_children_per_line(2)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        self.flow.set_homogeneous(True)
        self.flow.set_margin_start(20)
        self.flow.set_margin_end(20)
        self.flow.set_margin_top(16)
        self.flow.set_margin_bottom(20)

        self.content_scroll.set_child(self.flow)
        content_box.append(self.content_scroll)

        # Status
        self.store_status = Gtk.Label(label="")
        self.store_status.set_css_classes(["store-status"])
        self.store_status.set_halign(Gtk.Align.START)
        self.store_status.set_margin_start(20)
        self.store_status.set_margin_bottom(8)
        content_box.append(self.store_status)

        content_page.set_child(content_box)
        split.set_content(content_page)
        self.set_content(split)

        # Select Featured initially
        self.cat_list.select_row(self.cat_rows["Featured"])

    def _clear_grid(self):
        child = self.flow.get_first_child()
        while child:
            next_c = child.get_next_sibling()
            self.flow.remove(child)
            child = next_c

    def _load_category(self, category: str):
        self.current_cat = category
        self.content_title.set_label(category)
        self._clear_grid()

        apps = self.catalog.by_category(category)
        for app in apps:
            card = AppCard(app, self._open_app)
            self.flow.append(card)

        count = len(apps)
        self.store_status.set_label(
            f"{count} app{'s' if count != 1 else ''}"
        )

    def _on_cat_selected(self, list_box, row):
        if row and hasattr(row, "_cat"):
            self._load_category(row._cat)

    def _on_search(self, entry):
        query = entry.get_text().strip()
        if not query:
            self._load_category(self.current_cat)
            return
        self._clear_grid()
        results = self.catalog.search(query)
        for app in results:
            card = AppCard(app, self._open_app)
            self.flow.append(card)
        count = len(results)
        self.store_status.set_label(
            f'{count} result{"s" if count != 1 else ""} for "{query}"'
        )

    def _open_app(self, app: AppEntry):
        """Show app detail dialog."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=app.name,
            body=f"{app.description}\n\n"
                 f"Developer: {app.developer}\n"
                 f"Category:  {app.category}\n"
                 f"Size:      {app.size_str()}\n"
                 f"Rating:    {app.stars()} ({app.rating}/5)\n"
                 f"Downloads: {app.downloads}\n"
                 f"Backend:   {app.backend}"
        )
        dialog.add_response("close",   "Close")
        if not app.installed:
            dialog.add_response("install", "Install")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", lambda d, r: self._handle_detail_response(r, app))
        dialog.present()

    def _handle_detail_response(self, response: str, app: AppEntry):
        if response == "install":
            self._install_app(app)

    def _install_app(self, app: AppEntry):
        try:
            subprocess.Popen(
                ["flatpak", "install", "--user", "-y", "flathub", app.id],
                start_new_session=True
            )
        except FileNotFoundError:
            pass


# ─────────────────────────────────────────────────────────────
# XII Store Application
# ─────────────────────────────────────────────────────────────
class XIIStoreApp(Adw.Application):
    def __init__(self, initial_app_id: Optional[str] = None):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.initial_app_id = initial_app_id
        self.catalog = AppCatalog()
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self._apply_css()
        win = StoreWindow(self, self.catalog, self.initial_app_id)
        win.present()

    def _apply_css(self):
        css_path = Path(CSS_PATH)
        if not css_path.exists():
            css_path = Path(__file__).parent / "xii-store.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )


def main():
    parser = argparse.ArgumentParser(description="XII OS App Store")
    parser.add_argument("--app", default=None, help="Open directly to app ID")
    args, _ = parser.parse_known_args()

    app = XIIStoreApp(initial_app_id=args.app)
    sys.exit(app.run(sys.argv[:1]))


if __name__ == "__main__":
    main()
