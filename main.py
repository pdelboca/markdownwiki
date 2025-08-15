#!/usr/bin/env python3
import os
import sys

from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QMessageBox,
    QMenu,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QStatusBar,
    QFileDialog,
)
from PySide6.QtCore import Qt, QStandardPaths, QSettings, Slot
from PySide6.QtGui import QKeySequence, QAction, QIcon

from superqt.utils import CodeSyntaxHighlight

from widgets.file_navigator import FileSystemNavigator
from widgets.renderer import MarkdownRenderer
from widgets.editor import MarkdownEditor

from assets import resources # noqa: F401 # Required for building process.
from pygments.lexers import markup # noqa: F401 # Required for building process.

# Hardcoded and updated automatically when running do_release.sh
__VERSION__ = "0.2.5"

class MarkdownWiki(QMainWindow):
    """Main application window for Markdown Wiki"""

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.project_dir = None
        self.is_view_mode = False
        self.settings = QSettings()
        self.init_ui()
        recent_folders = self.settings.value("recent_folders", [], type=list)
        if len(recent_folders) > 0:
            self.file_navigator.setup_navigator(recent_folders[0])

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Markdown Wiki[*]")
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()

        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)

        # Create splitter for the sidebar and main area
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Add file tree sidebar
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        # Configure file system model and tree view
        self.file_navigator = FileSystemNavigator()
        self.file_navigator.selected_item.connect(self.open_selected_path)
        sidebar_layout.addWidget(self.file_navigator)

        # Create main editor area
        self.main_area = QWidget()
        main_area_layout = QVBoxLayout(self.main_area)
        main_area_layout.setContentsMargins(0, 0, 0, 0)

        # Create text editor for markdown
        self.md_editor = MarkdownEditor()
        CodeSyntaxHighlight(self.md_editor.document(), "markdown", "bw")
        self.md_editor.document().contentsChanged.connect(self.document_was_modified)
        self.md_editor.navigation_requested.connect(self.navigate_to_file)

        # Create markdown renderer
        self.md_renderer = MarkdownRenderer()
        self.md_renderer.navigation_requested.connect(self.navigate_to_file)

        # Add editor and renderer to layout
        main_area_layout.addWidget(self.md_editor)
        main_area_layout.addWidget(self.md_renderer)

        # Initially hide the renderer
        self.md_renderer.hide()

        # Add widgets to splitter
        splitter.addWidget(self.sidebar_widget)
        splitter.addWidget(self.main_area)

        # Set splitter proportions (20% for sidebar)
        splitter.setSizes([int(self.width() * 0.2), int(self.width() * 0.8)])

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self.setup_actions()

        self.setup_menu_bar()

    def setup_menu_bar(self):
        self.menu_file = QMenu("File")
        self.menu_file.addAction(self.file_navigator.new_file_action)
        self.menu_file.addAction(self.file_navigator.new_folder_action)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.open_folder_action)
        self.recent_menu = self.menu_file.addMenu("Open &Recent")
        self.recent_menu.aboutToShow.connect(self.update_recent_menu)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.file_navigator.delete_action)
        self.menu_file.addAction(self.file_navigator.rename_action)
        self.menu_file.addAction(self.save_file_action)
        self.menuBar().addMenu(self.menu_file)

        self.menu_view = QMenu("View")
        self.menu_view.addAction(self.toggle_view_action)
        self.menuBar().addMenu(self.menu_view)

        self.menu_help = QMenu("Help")
        self.menu_help.addAction(self.about_dialog_action)
        self.menuBar().addMenu(self.menu_help)

    def setup_actions(self):
        """Setup keyboard shortcuts and actions"""
        # Open Folder
        self.open_folder_action = QAction("Open Folder", self)
        self.open_folder_action.triggered.connect(self.open_wiki_folder)
        self.addAction(self.open_folder_action)

        # Switch between edit/view mode (Ctrl+`)
        self.toggle_view_action = QAction("Toggle View Mode", self)
        self.toggle_view_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_QuoteLeft))
        self.toggle_view_action.triggered.connect(self.toggle_view_mode)
        self.addAction(self.toggle_view_action)

        # Save file (Ctrl+S)
        self.save_file_action = QAction("Save File", self)
        self.save_file_action.setShortcut(QKeySequence.Save)
        self.save_file_action.triggered.connect(self.save_file)
        self.addAction(self.save_file_action)

        # ESC to focus sidebar
        self.focus_sidebar_action = QAction("Focus Sidebar", self)
        self.focus_sidebar_action.setShortcut(QKeySequence(Qt.Key_Escape))
        self.focus_sidebar_action.triggered.connect(self.focus_sidebar)
        self.addAction(self.focus_sidebar_action)

        # About Dialog
        self.about_dialog_action = QAction("About", self)
        self.about_dialog_action.triggered.connect(self.display_about)
        self.addAction(self.about_dialog_action)

    def update_recent_menu(self):
        """Update recent menu items before showing it."""
        self.recent_menu.clear()

        self.recent_folders = self.settings.value("recent_folders", [], type=list)

        for i, folder in enumerate(self.recent_folders):
            name = os.path.basename(folder)
            action = QAction(f"&{i + 1} {name}", self)
            action.setData(folder)
            action.triggered.connect(
                lambda checked, f=folder: self.open_wiki_by_path(f)
            )
            self.recent_menu.addAction(action)

    def display_about(self):
        version = QApplication.applicationVersion()
        QMessageBox.about(
            self, "MarkdownWiki", f"Desktop Application for handling Markdown Wikis.\nVersion: {version}"
        )

    def open_wiki_by_path(self, folder):
        """Process and store selected folder"""
        if self.isWindowModified():
            if not self.confirm_discard_changes():
                return

        if not os.path.exists(folder):
            QMessageBox.warning(
                self, "Invalid Folder", "Selected folder does not exist!"
            )
            return

        if self.current_file:
            self.current_file = None
            self.md_editor.setPlainText("")
            self.md_renderer.render_markdown("")

        self.file_navigator.setup_navigator(folder)
        self._add_to_recent_folders(folder)
        self.status_bar.showMessage(f"Project opened: {folder}")

    def open_wiki_folder(self):
        """Selects and open a new folder as a Wiki project."""
        if self.isWindowModified():
            if not self.confirm_discard_changes():
                return

        default_dir = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        folder = QFileDialog.getExistingDirectory(
            self, "Select Wiki Folder", default_dir
        )

        if not folder:
            self.status_bar.showMessage("No folder selected. Nothing has been done.")
            return

        if self.current_file:
            self.current_file = None
            self.md_editor.setPlainText("")
            self.md_renderer.render_markdown("")

        self.file_navigator.setup_navigator(folder)
        self._add_to_recent_folders(folder)
        self.status_bar.showMessage(f"Project opened: {folder}")

    def _add_to_recent_folders(self, folder):
        """Add a folder to the recent_folder settings up to a max of 5."""
        recent_folders = self.settings.value("recent_folders", [], type=list)
        if folder in recent_folders:
            recent_folders.remove(folder)
        recent_folders.insert(0, folder)
        recent_folders = recent_folders[:5]
        self.settings.setValue("recent_folders", recent_folders)

    def open_selected_path(self, path):
        """Open the file selected in the tree view"""
        path = Path(path)
        # If it's a directory, just expand/collapse it
        if path.is_dir():
            return
        self.open_file(path)

    def open_file(self, file_path):
        """Open and display a markdown file"""
        if self.isWindowModified():
            if not self.confirm_discard_changes():
                return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.md_editor.setPlainText(content)
            self.md_renderer.render_markdown(content)

            self.current_file = file_path
            self.setWindowTitle(f"Markdown Wiki - {os.path.basename(file_path)}[*]")

            self.md_editor.document().setModified(False)
            self.setWindowModified(False)

            self.status_bar.showMessage(f"Opened file: {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def save_file(self):
        """Save the current file"""
        if not self.current_file:
            self.status_bar.showMessage("No file to save")
            return

        try:
            content = self.md_editor.toPlainText()

            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)

            self.md_editor.document().setModified(False)
            self.setWindowModified(False)
            self.status_bar.showMessage(
                f"Saved file: {os.path.basename(self.current_file)}"
            )

            if self.is_view_mode:
                self.md_renderer.render_markdown(content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def focus_sidebar(self):
        """Handle Escape key to focus sidebar"""
        self.file_navigator.tree_view.setFocus()
        self.status_bar.showMessage("Sidebar focused")

    def set_view_mode(self):
        """Switch to View Mode and update the Markdown Rendered with latest changes."""
        self.md_editor.hide()
        self.md_renderer.show()
        self.md_renderer.render_markdown(self.md_editor.toPlainText())
        self.status_bar.showMessage("View mode")

    def set_edit_mode(self):
        """Switch to edit mode."""
        self.md_renderer.hide()
        self.md_editor.show()
        self.md_editor.setFocus()
        self.status_bar.showMessage("Edit mode")

    def toggle_view_mode(self):
        """Switch between edit and view mode"""
        if not self.is_view_mode:
            self.set_view_mode()
        else:
            self.set_edit_mode()
        self.is_view_mode = not self.is_view_mode

    def navigate_to_file(self, target_path):
        """Navigate to a file based on a relative or absolute path.

        This method only allows to navigate to files that exist and are
        inside the wiki folder.
        """
        if self.isWindowModified():
            if not self.confirm_discard_changes():
                return

        abs_path = (self.project_dir / Path(target_path)).resolve()

        if not abs_path.exists():
            self.status_bar.showMessage(f"File: {abs_path.name} does not exist.")
            return

        try:
            self.open_file(str(abs_path))
        except Exception as e:
            self.status_bar.showMessage(f"Navigation error: {str(e)}")

    @Slot()
    def document_was_modified(self):
        self.setWindowModified(self.md_editor.document().isModified())

    def confirm_discard_changes(self):
        """Ask the user to confirm discarding unsaved changes"""
        response = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )

        if response == QMessageBox.Save:
            self.save_file()
            return True
        elif response == QMessageBox.Discard:
            self.setWindowModified(False)
            self.md_editor.document().setModified(False)
            return True
        else:  # Cancel
            return False

    def closeEvent(self, event):
        """Handle application closing"""
        if self.isWindowModified():
            if not self.confirm_discard_changes():
                event.ignore()
                return

        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon(':/icons/icon.ico'))
    app.setOrganizationName("me.pdelboca")
    app.setApplicationName("markdownwiki")
    app.setApplicationVersion(__VERSION__)
    app.setStyle("Fusion")
    wiki = MarkdownWiki()
    wiki.show()
    sys.exit(app.exec())
