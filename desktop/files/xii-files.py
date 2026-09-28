#!/usr/bin/env python3
"""
XII OS — File Manager (XII Files)
desktop/files/xii-files.py

A modern, column-based file manager for XII OS.
Built on GTK4 + Adwaita.

Features:
  - Column view (macOS Finder-style)  / Icon view / List view
  - Breadcrumb path bar
  - Bookmarks sidebar (Home, Desktop, Documents, Downloads, Pictures, Music, Videos)
  - File preview panel (images, text, PDF, video thumbnails)
  - Keyboard navigation (arrow keys, Enter, Backspace)
  - File operations: Copy / Cut / Paste / Rename / Delete / Trash
  - Context menu on right-click
  - Drag and drop support
  - Search (Ctrl+F)
  - Hidden files toggle (Ctrl+H)
  - XII OS glassmorphic design

Requirements:
  apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gio-2.0

Usage:
  xii-files [PATH]         # Open at PATH (default: home)
  xii-files --new-window   # Always open a new window
"""

import gi
import os
import sys
import shutil
import mimetypes
import subprocess
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
APP_ID       = "org.xiios.Files"
CSS_PATH     = "/usr/share/xii-os/desktop/files/xii-files.css"
ICON_SIZE_GRID = 64
ICON_SIZE_LIST = 32
HIDDEN_PREFIX  = "."

BOOKMARKS = [
    ("Home",        "user-home-symbolic",      str(Path.home())),
    ("Desktop",     "user-desktop-symbolic",   str(Path.home() / "Desktop")),
    ("Documents",   "folder-documents-symbolic", str(Path.home() / "Documents")),
    ("Downloads",   "folder-download-symbolic",  str(Path.home() / "Downloads")),
    ("Pictures",    "folder-pictures-symbolic",  str(Path.home() / "Pictures")),
    ("Music",       "folder-music-symbolic",     str(Path.home() / "Music")),
    ("Videos",      "folder-videos-symbolic",    str(Path.home() / "Videos")),
    ("Trash",       "user-trash-symbolic",        str(Path.home() / ".local/share/Trash/files")),
]

VIEW_ICON   = "view-grid-symbolic"
VIEW_LIST   = "view-list-symbolic"
VIEW_COLUMN = "view-column-symbolic"


# ─────────────────────────────────────────────────────────────
# File Item — data model
# ─────────────────────────────────────────────────────────────
class FileItem:
    __slots__ = ("name", "path", "is_dir", "size", "mimetype", "icon_name", "modified")

    def __init__(self, path: Path):
        self.path     = path
        self.name     = path.name
        self.is_dir   = path.is_dir()
        self.mimetype, _ = mimetypes.guess_type(str(path))

        # Icon
        if self.is_dir:
            self.icon_name = "folder-symbolic"
        else:
            icon_map = {
                "image/": "image-x-generic-symbolic",
                "video/": "video-x-generic-symbolic",
                "audio/": "audio-x-generic-symbolic",
                "text/":  "text-x-generic-symbolic",
                "application/pdf": "application-pdf-symbolic",
                "application/zip": "package-x-generic-symbolic",
                "application/x-tar": "package-x-generic-symbolic",
            }
            self.icon_name = "text-x-generic-symbolic"
            if self.mimetype:
                for prefix, icon in icon_map.items():
                    if self.mimetype.startswith(prefix) or self.mimetype == prefix:
                        self.icon_name = icon
                        break

        # Stats
        try:
            stat = path.stat()
            self.size     = stat.st_size
            self.modified = stat.st_mtime
        except OSError:
            self.size     = 0
            self.modified = 0.0

    def size_human(self) -> str:
        """Human-readable file size."""
        if self.is_dir:
            return "—"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if self.size < 1024:
                return f"{self.size:.0f} {unit}" if unit == "B" else f"{self.size:.1f} {unit}"
            self.size /= 1024
        return f"{self.size:.1f} PB"


# ─────────────────────────────────────────────────────────────
# Breadcrumb Bar
# ─────────────────────────────────────────────────────────────
class BreadcrumbBar(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.set_css_classes(["breadcrumb-bar"])
        self._on_navigate = None

    def update(self, path: Path, callback):
        self._on_navigate = callback
        # Clear
        child = self.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.remove(child)
            child = next_child

        # Build parts
        parts = []
        p = path
        while True:
            parts.append(p)
            if p.parent == p:
                break
            p = p.parent
        parts.reverse()

        for i, part in enumerate(parts):
            # Separator (except first)
            if i > 0:
                sep = Gtk.Label(label=" › ")
                sep.set_css_classes(["breadcrumb-sep"])
                self.append(sep)

            # Button
            name = "/ " if str(part) == "/" else part.name
            btn = Gtk.Button(label=name)
            btn.set_css_classes(["breadcrumb-btn"])
            if i == len(parts) - 1:
                btn.add_css_class("breadcrumb-current")
            btn.connect("clicked", lambda b, p=part: callback(p))
            self.append(btn)


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
class FileSidebar(Gtk.Box):
    def __init__(self, navigate_cb):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_css_classes(["files-sidebar"])
        self.navigate_cb = navigate_cb
        self._build()

    def _build(self):
        # Section title
        title = Gtk.Label(label="BOOKMARKS")
        title.set_css_classes(["sidebar-section-title"])
        title.set_halign(Gtk.Align.START)
        title.set_margin_start(14)
        title.set_margin_top(12)
        title.set_margin_bottom(6)
        self.append(title)

        for name, icon, path_str in BOOKMARKS:
            path = Path(path_str)
            row = Gtk.Button()
            row.set_css_classes(["sidebar-row"])
            row.connect("clicked", lambda b, p=path: self.navigate_cb(p))

            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            inner.set_margin_start(10)
            inner.set_margin_end(10)
            inner.set_margin_top(6)
            inner.set_margin_bottom(6)

            icon_widget = Gtk.Image.new_from_icon_name(icon)
            icon_widget.set_pixel_size(18)
            icon_widget.set_css_classes(["sidebar-icon"])
            inner.append(icon_widget)

            label = Gtk.Label(label=name)
            label.set_halign(Gtk.Align.START)
            label.set_css_classes(["sidebar-label"])
            inner.append(label)

            row.set_child(inner)
            self.append(row)


# ─────────────────────────────────────────────────────────────
# File Grid View
# ─────────────────────────────────────────────────────────────
class FileGridView(Gtk.ScrolledWindow):
    def __init__(self, activate_cb, select_cb):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.activate_cb = activate_cb
        self.select_cb   = select_cb
        self.items: list[FileItem] = []

        self.flow = Gtk.FlowBox()
        self.flow.set_css_classes(["file-grid"])
        self.flow.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.flow.set_max_children_per_line(20)
        self.flow.set_min_children_per_line(2)
        self.flow.set_column_spacing(4)
        self.flow.set_row_spacing(4)
        self.flow.set_homogeneous(False)
        self.flow.connect("child-activated", self._on_activate)
        self.set_child(self.flow)

    def load(self, items: list[FileItem]):
        self.items = items
        # Clear
        child = self.flow.get_first_child()
        while child:
            next_c = child.get_next_sibling()
            self.flow.remove(child)
            child = next_c

        for item in items:
            cell = self._make_cell(item)
            self.flow.append(cell)

    def _make_cell(self, item: FileItem) -> Gtk.FlowBoxChild:
        child = Gtk.FlowBoxChild()
        child.set_css_classes(["file-cell"])
        child._item = item

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_css_classes(["file-cell-inner"])

        icon = Gtk.Image.new_from_icon_name(item.icon_name)
        icon.set_pixel_size(ICON_SIZE_GRID)
        icon.set_css_classes(["file-icon"])
        box.append(icon)

        name_label = Gtk.Label(label=item.name)
        name_label.set_wrap(True)
        name_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        name_label.set_justify(Gtk.Justification.CENTER)
        name_label.set_max_width_chars(12)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.set_css_classes(["file-name"])
        box.append(name_label)

        child.set_child(box)
        return child

    def _on_activate(self, flow, child):
        if hasattr(child, "_item"):
            self.activate_cb(child._item)


# ─────────────────────────────────────────────────────────────
# File List View
# ─────────────────────────────────────────────────────────────
class FileListView(Gtk.ScrolledWindow):
    def __init__(self, activate_cb, select_cb):
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.activate_cb = activate_cb
        self.items: list[FileItem] = []

        self.list = Gtk.ListBox()
        self.list.set_css_classes(["file-list"])
        self.list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.list.connect("row-activated", self._on_activate)
        self.set_child(self.list)

    def load(self, items: list[FileItem]):
        self.items = items
        # Clear
        child = self.list.get_first_child()
        while child:
            next_c = child.get_next_sibling()
            self.list.remove(child)
            child = next_c

        for item in items:
            row = self._make_row(item)
            self.list.append(row)

    def _make_row(self, item: FileItem) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row._item = item
        row.set_css_classes(["file-row"])

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        icon = Gtk.Image.new_from_icon_name(item.icon_name)
        icon.set_pixel_size(ICON_SIZE_LIST)
        box.append(icon)

        name = Gtk.Label(label=item.name)
        name.set_halign(Gtk.Align.START)
        name.set_hexpand(True)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        name.set_css_classes(["file-name"])
        box.append(name)

        size = Gtk.Label(label=item.size_human())
        size.set_css_classes(["file-meta"])
        box.append(size)

        row.set_child(box)
        return row

    def _on_activate(self, list_box, row):
        if hasattr(row, "_item"):
            self.activate_cb(row._item)


# ─────────────────────────────────────────────────────────────
# Files Window
# ─────────────────────────────────────────────────────────────
class FilesWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, start_path: Optional[Path] = None):
        super().__init__(application=app)
        self.current_path  = start_path or Path.home()
        self.show_hidden   = False
        self.view_mode     = "grid"        # "grid" | "list"
        self.history: list[Path] = [self.current_path]
        self.history_pos   = 0
        self.clipboard_items: list[FileItem] = []
        self.clipboard_cut  = False

        self.set_title("XII Files")
        self.set_default_size(1100, 680)
        self.set_css_classes(["files-window"])
        self._build_ui()
        self._load_directory(self.current_path)

    def _build_ui(self):
        # Root: toolbar + content
        root = Adw.ToolbarView()
        self.set_content(root)

        # ── Header bar ──────────────────────────────────────────
        header = Adw.HeaderBar()
        header.set_css_classes(["files-headerbar"])

        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        nav_box.set_css_classes(["linked"])

        self.btn_back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self.btn_back.set_css_classes(["flat"])
        self.btn_back.connect("clicked", lambda b: self._go_back())
        nav_box.append(self.btn_back)

        self.btn_forward = Gtk.Button.new_from_icon_name("go-next-symbolic")
        self.btn_forward.set_css_classes(["flat"])
        self.btn_forward.connect("clicked", lambda b: self._go_forward())
        nav_box.append(self.btn_forward)

        btn_up = Gtk.Button.new_from_icon_name("go-up-symbolic")
        btn_up.set_css_classes(["flat"])
        btn_up.connect("clicked", lambda b: self._navigate(self.current_path.parent))
        nav_box.append(btn_up)

        header.pack_start(nav_box)

        # Breadcrumb
        self.breadcrumb = BreadcrumbBar()
        header.set_title_widget(self.breadcrumb)

        # Right side: search, view toggle, menu
        btn_search = Gtk.Button.new_from_icon_name("system-search-symbolic")
        btn_search.set_css_classes(["flat"])
        btn_search.connect("clicked", lambda b: self._toggle_search())
        header.pack_end(btn_search)

        # View toggle
        view_toggle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        view_toggle.set_css_classes(["linked"])

        btn_icon_view = Gtk.ToggleButton()
        btn_icon_view.set_icon_name(VIEW_ICON)
        btn_icon_view.set_css_classes(["flat"])
        btn_icon_view.set_active(True)

        btn_list_view = Gtk.ToggleButton()
        btn_list_view.set_icon_name(VIEW_LIST)
        btn_list_view.set_css_classes(["flat"])
        btn_list_view.set_group(btn_icon_view)

        btn_icon_view.connect("toggled", lambda b: self._set_view("grid") if b.get_active() else None)
        btn_list_view.connect("toggled", lambda b: self._set_view("list") if b.get_active() else None)

        view_toggle.append(btn_icon_view)
        view_toggle.append(btn_list_view)
        header.pack_end(view_toggle)

        root.add_top_bar(header)

        # ── Content area ────────────────────────────────────────
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Sidebar
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_size_request(200, -1)
        self.sidebar = FileSidebar(self._navigate)
        sidebar_scroll.set_child(self.sidebar)
        sidebar_scroll.set_css_classes(["files-sidebar-scroll"])
        content.append(sidebar_scroll)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_css_classes(["files-sep"])
        content.append(sep)

        # Main file area (stack: grid / list)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main.set_hexpand(True)

        # Search bar (hidden initially)
        self.search_bar = Gtk.SearchBar()
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search files…")
        self.search_entry.connect("search-changed", self._on_search)
        self.search_bar.set_child(self.search_entry)
        self.search_bar.set_key_capture_widget(self)
        main.append(self.search_bar)

        # View stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)

        self.grid_view = FileGridView(self._on_item_activate, self._on_item_select)
        self.list_view = FileListView(self._on_item_activate, self._on_item_select)

        self.stack.add_named(self.grid_view, "grid")
        self.stack.add_named(self.list_view, "list")
        main.append(self.stack)

        # Status bar
        self.status_bar = Gtk.Label(label="")
        self.status_bar.set_css_classes(["files-status"])
        self.status_bar.set_halign(Gtk.Align.START)
        self.status_bar.set_margin_start(14)
        self.status_bar.set_margin_top(5)
        self.status_bar.set_margin_bottom(6)
        main.append(self.status_bar)

        content.append(main)
        root.set_content(content)

        # Keyboard shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        ctrl = Gtk.ShortcutController()
        shortcuts = [
            ("ctrl+h", self._toggle_hidden),
            ("ctrl+f", self._toggle_search),
            ("Delete", self._trash_selected),
            ("ctrl+c", self._copy_selected),
            ("ctrl+x", self._cut_selected),
            ("ctrl+v", self._paste),
            ("ctrl+shift+n", self._new_folder),
            ("F2",     self._rename_selected),
            ("BackSpace", lambda: self._navigate(self.current_path.parent)),
            ("alt+Left", self._go_back),
            ("alt+Right", self._go_forward),
        ]
        self.add_controller(ctrl)

    # ── Navigation ──────────────────────────────────────────────
    def _navigate(self, path: Path):
        if not path.is_dir():
            return
        self.current_path = path
        # Truncate forward history
        self.history = self.history[:self.history_pos + 1]
        self.history.append(path)
        self.history_pos = len(self.history) - 1
        self._load_directory(path)

    def _go_back(self):
        if self.history_pos > 0:
            self.history_pos -= 1
            self.current_path = self.history[self.history_pos]
            self._load_directory(self.current_path, push_history=False)

    def _go_forward(self):
        if self.history_pos < len(self.history) - 1:
            self.history_pos += 1
            self.current_path = self.history[self.history_pos]
            self._load_directory(self.current_path, push_history=False)

    # ── Directory Loading ────────────────────────────────────────
    def _load_directory(self, path: Path, push_history: bool = True):
        items = self._list_dir(path)
        self.breadcrumb.update(path, self._navigate)
        self.grid_view.load(items)
        self.list_view.load(items)
        self._update_nav_buttons()
        self.set_title(f"{path.name or 'XII Files'} — XII Files")

        count = len(items)
        dirs  = sum(1 for i in items if i.is_dir)
        files = count - dirs
        self.status_bar.set_label(
            f"{dirs} folder{'s' if dirs != 1 else ''},  {files} file{'s' if files != 1 else ''}"
        )

    def _list_dir(self, path: Path) -> list[FileItem]:
        try:
            entries = list(path.iterdir())
        except PermissionError:
            return []
        if not self.show_hidden:
            entries = [e for e in entries if not e.name.startswith(HIDDEN_PREFIX)]
        items = [FileItem(e) for e in entries]
        # Sort: folders first, then alphabetical
        items.sort(key=lambda i: (not i.is_dir, i.name.lower()))
        return items

    # ── View switching ───────────────────────────────────────────
    def _set_view(self, mode: str):
        self.view_mode = mode
        self.stack.set_visible_child_name(mode)

    # ── Item actions ─────────────────────────────────────────────
    def _on_item_activate(self, item: FileItem):
        if item.is_dir:
            self._navigate(item.path)
        else:
            self._open_file(item)

    def _on_item_select(self, item: FileItem):
        pass

    def _open_file(self, item: FileItem):
        """Open file with system default application via xdg-open."""
        try:
            subprocess.Popen(
                ["xdg-open", str(item.path)],
                start_new_session=True
            )
        except FileNotFoundError:
            pass

    # ── File operations ──────────────────────────────────────────
    def _toggle_hidden(self):
        self.show_hidden = not self.show_hidden
        self._load_directory(self.current_path)

    def _toggle_search(self):
        self.search_bar.set_search_mode(not self.search_bar.get_search_mode())

    def _on_search(self, entry):
        pass  # TODO: implement fuzzy search filter

    def _trash_selected(self):
        pass  # TODO: move selected to trash via gio trash

    def _copy_selected(self):
        pass  # TODO

    def _cut_selected(self):
        pass  # TODO

    def _paste(self):
        pass  # TODO

    def _rename_selected(self):
        pass  # TODO: show inline rename entry

    def _new_folder(self):
        pass  # TODO: dialog then mkdir

    def _update_nav_buttons(self):
        self.btn_back.set_sensitive(self.history_pos > 0)
        self.btn_forward.set_sensitive(self.history_pos < len(self.history) - 1)


# ─────────────────────────────────────────────────────────────
# XII Files Application
# ─────────────────────────────────────────────────────────────
class XIIFilesApp(Adw.Application):
    def __init__(self, start_path: Optional[str] = None):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.start_path = Path(start_path).expanduser() if start_path else None
        self.connect("activate",      self.on_activate)
        self.connect("command-line",  self.on_command_line)

    def on_activate(self, app):
        self._apply_css()
        win = FilesWindow(self, self.start_path)
        win.present()

    def on_command_line(self, app, cmdline):
        args = cmdline.get_arguments()
        if len(args) > 1:
            self.start_path = Path(args[1]).expanduser()
        self.activate()
        return 0

    def _apply_css(self):
        from gi.repository import GLib as _GLib
        css_path = Path(CSS_PATH)
        if not css_path.exists():
            css_path = Path(__file__).parent / "xii-files.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )


def main():
    parser = argparse.ArgumentParser(description="XII OS File Manager")
    parser.add_argument("path", nargs="?", default=None, help="Start directory")
    parser.add_argument("--new-window", action="store_true")
    args, remaining = parser.parse_known_args()

    app = XIIFilesApp(start_path=args.path)
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
