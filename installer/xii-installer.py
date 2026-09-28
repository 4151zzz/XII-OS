#!/usr/bin/env python3
"""
XII OS — Live Graphical Installer
installer/xii-installer.py

A modern wizard-based OS installer for XII OS.
Guides user through:
  1. Welcome & Language
  2. Installation Target Drive (Automatic GPT / Btrfs)
  3. User & Machine Account Setup
  4. Performance Mode Selection (Lite / Standard / Performance)
  5. Installation Progress & Feature Showcase
  6. Completion & Reboot Prompt
"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional

APP_ID = "org.xiios.Installer"
CSS_PATH = Path("/usr/share/xii-os/installer/xii-installer.css")
LOCAL_CSS = Path(__file__).parent / "xii-installer.css"


try:
    from installer.installer_backend import InstallerBackend, DiskDevice
except ImportError:
    # If run standalone
    sys.path.insert(0, str(Path(__file__).parent))
    from installer_backend import InstallerBackend, DiskDevice


try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw, GLib, Gio
    HAS_GTK = True
except Exception:
    HAS_GTK = False


if HAS_GTK:
    class XIIInstallerApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
            self.backend = InstallerBackend()

        def do_startup(self):
            super().do_startup()
            self._load_css()

        def _load_css(self):
            css_file = LOCAL_CSS if LOCAL_CSS.exists() else CSS_PATH
            if css_file.exists():
                provider = Gtk.CssProvider()
                provider.load_from_path(str(css_file))
                from gi.repository import Gdk
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(),
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )

        def do_activate(self):
            win = self.props.active_window
            if not win:
                win = XIIInstallerWindow(application=self, backend=self.backend)
            win.present()


    class XIIInstallerWindow(Adw.ApplicationWindow):
        def __init__(self, backend: InstallerBackend, **kwargs):
            super().__init__(**kwargs)
            self.backend = backend
            self.set_title("Install XII OS 1.0 (Genesis)")
            self.set_default_size(840, 580)
            self.add_css_class("xii-installer-window")

            self._current_step = 0
            self._build_ui()

        def _build_ui(self):
            self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.set_content(self.main_box)

            # Header
            header = Adw.HeaderBar()
            header.add_css_class("installer-header")
            self.title_widget = Adw.WindowTitle(title="Install XII OS", subtitle="Step 1 of 5: Welcome")
            header.set_title_widget(self.title_widget)
            self.main_box.append(header)

            # View stack
            self.stack = Gtk.Stack()
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            self.main_box.append(self.stack)

            # Step 1: Welcome
            self.stack.add_named(self._build_welcome_step(), "step_welcome")
            # Step 2: Disk Selection
            self.stack.add_named(self._build_disk_step(), "step_disk")
            # Step 3: User Setup
            self.stack.add_named(self._build_user_step(), "step_user")
            # Step 4: Mode Selection
            self.stack.add_named(self._build_mode_step(), "step_mode")
            # Step 5: Progress
            self.stack.add_named(self._build_progress_step(), "step_progress")

            # Bottom action bar
            self.action_bar = Gtk.ActionBar()
            self.btn_back = Gtk.Button(label="Back")
            self.btn_back.add_css_class("btn-back")
            self.btn_back.connect("clicked", self._on_back_clicked)
            self.btn_back.set_sensitive(False)
            self.action_bar.pack_start(self.btn_back)

            self.btn_next = Gtk.Button(label="Next")
            self.btn_next.add_css_class("btn-primary")
            self.btn_next.connect("clicked", self._on_next_clicked)
            self.action_bar.pack_end(self.btn_next)

            self.main_box.append(self.action_bar)

        def _build_welcome_step(self) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            hero.add_css_class("installer-hero")

            title = Gtk.Label(label="Welcome to XII OS")
            title.add_css_class("hero-title")
            hero.append(title)

            sub = Gtk.Label(label="Beautiful. Lightweight. Intelligent.\nExperience next-generation computing on x86-64.")
            sub.add_css_class("hero-subtitle")
            hero.append(sub)
            box.append(hero)

            # Language choice
            group = Adw.PreferencesGroup(title="Select System Language")
            box.append(group)

            row_th = Adw.ActionRow(title="ภาษาไทย (Thai)", subtitle="คีย์บอร์ดเกษมณี และฟอนต์ภาษาไทย")
            group.add(row_th)

            row_en = Adw.ActionRow(title="English (US)", subtitle="Default English interface")
            group.add(row_en)

            return box

        def _build_disk_step(self) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            group = Adw.PreferencesGroup(title="Target Storage Drive")
            box.append(group)

            disks = self.backend.list_disks()
            if disks:
                self.backend.target_disk = disks[0]

            for d in disks:
                row = Adw.ActionRow(title=f"{d.model} ({d.size_gb} GB)", subtitle=f"Device: {d.path}")
                row.add_css_class("disk-select-box")
                group.add(row)

            fs_group = Adw.PreferencesGroup(title="Filesystem Scheme")
            box.append(fs_group)
            btrfs_row = Adw.ActionRow(title="Btrfs (Recommended)", subtitle="Enables instant snapshots and rollback")
            fs_group.add(btrfs_row)

            return box

        def _build_user_step(self) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            group = Adw.PreferencesGroup(title="User & Machine Configuration")
            box.append(group)

            self.user_entry = Adw.EntryRow(title="Your Name / Username")
            self.user_entry.set_text("xii")
            group.add(self.user_entry)

            self.host_entry = Adw.EntryRow(title="Computer Name")
            self.host_entry.set_text("xii-workstation")
            group.add(self.host_entry)

            self.pass_entry = Adw.PasswordEntryRow(title="Password")
            self.pass_entry.set_text("xii123")
            group.add(self.pass_entry)

            return box

        def _build_mode_step(self) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
            group = Adw.PreferencesGroup(title="Select Default Performance Mode")
            box.append(group)

            row_std = Adw.ActionRow(title="XII Standard (Recommended)", subtitle="Balanced animations, modern glassmorphism, responsive.")
            group.add(row_std)

            row_lite = Adw.ActionRow(title="XII Lite", subtitle="Minimal memory footprint (< 350 MB RAM), faster for older machines.")
            group.add(row_lite)

            row_perf = Adw.ActionRow(title="XII Performance", subtitle="Full GPU acceleration, rich spring physics and blur.")
            group.add(row_perf)

            return box

        def _build_progress_step(self) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
            box.set_margin_top(40)
            box.set_margin_start(40)
            box.set_margin_end(40)

            self.prog_title = Gtk.Label(label="Installing XII OS...")
            self.prog_title.add_css_class("hero-title")
            box.append(self.prog_title)

            self.progress_bar = Gtk.ProgressBar()
            self.progress_bar.set_fraction(0.1)
            self.progress_bar.add_css_class("progress-bar-custom")
            box.append(self.progress_bar)

            self.prog_status = Gtk.Label(label="Preparing target drive...")
            box.append(self.prog_status)

            return box

        def _on_next_clicked(self, btn):
            if self._current_step == 0:
                self._current_step = 1
                self.stack.set_visible_child_name("step_disk")
                self.title_widget.set_subtitle("Step 2 of 5: Target Drive")
                self.btn_back.set_sensitive(True)
            elif self._current_step == 1:
                self._current_step = 2
                self.stack.set_visible_child_name("step_user")
                self.title_widget.set_subtitle("Step 3 of 5: User Setup")
            elif self._current_step == 2:
                self.backend.username = self.user_entry.get_text()
                self.backend.hostname = self.host_entry.get_text()
                self.backend.password = self.pass_entry.get_text()
                self._current_step = 3
                self.stack.set_visible_child_name("step_mode")
                self.title_widget.set_subtitle("Step 4 of 5: Performance Mode")
            elif self._current_step == 3:
                self._current_step = 4
                self.stack.set_visible_child_name("step_progress")
                self.title_widget.set_subtitle("Step 5 of 5: Installing")
                self.btn_back.set_sensitive(False)
                self.btn_next.set_sensitive(False)
                self._start_install()

        def _on_back_clicked(self, btn):
            if self._current_step == 1:
                self._current_step = 0
                self.stack.set_visible_child_name("step_welcome")
                self.title_widget.set_subtitle("Step 1 of 5: Welcome")
                self.btn_back.set_sensitive(False)
            elif self._current_step == 2:
                self._current_step = 1
                self.stack.set_visible_child_name("step_disk")
                self.title_widget.set_subtitle("Step 2 of 5: Target Drive")
            elif self._current_step == 3:
                self._current_step = 2
                self.stack.set_visible_child_name("step_user")
                self.title_widget.set_subtitle("Step 3 of 5: User Setup")

        def _start_install(self):
            def worker():
                def cb(pct, msg):
                    GLib.idle_add(self._update_progress, pct, msg)
                self.backend.simulate_install(progress_callback=cb)
                GLib.idle_add(self._on_install_finished)

            threading.Thread(target=worker, daemon=True).start()

        def _update_progress(self, pct: int, msg: str):
            self.progress_bar.set_fraction(pct / 100.0)
            self.prog_status.set_text(msg)

        def _on_install_finished(self):
            self.prog_title.set_text("Installation Complete!")
            self.btn_next.set_label("Reboot Now")
            self.btn_next.set_sensitive(True)
            self.btn_next.connect("clicked", lambda b: sys.exit(0))


def main():
    if not HAS_GTK:
        print("[XII Installer] Running in CLI mode.")
        backend = InstallerBackend()
        disks = backend.list_disks()
        print(f"Disks found: {len(disks)}")
        backend.target_disk = disks[0] if disks else None
        backend.simulate_install(lambda p, m: print(f"[{p}%] {m}"))
        return 0

    app = XIIInstallerApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
