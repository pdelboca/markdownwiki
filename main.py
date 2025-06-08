#!/usr/bin/env python3
import os
import sys
import markdown
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileSystemModel,
                               QTreeView, QSplitter, QTextEdit, QTextBrowser, QMessageBox,
                               QHBoxLayout, QVBoxLayout, QWidget, QStatusBar,
                               QInputDialog, QLineEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QFont, QAction
import re

from file_navigator import FileSystemNavigator

class MarkdownRenderer(QTextBrowser):
    """Widget to render Markdown content"""

    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)  # We'll handle link clicking ourselves
        self.setStyleSheet("""
            MarkdownRenderer {
                background-color: #F5F5F5;
                color: #333333;
                padding: 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                margin-left: auto;
                margin-right: auto;
                max-width: 800px; /* Limit width for better readability */
            }
            MarkdownRenderer h1 { font-size: 32px; color: #1a1a1a; margin-top: 24px; margin-bottom: 16px; }
            MarkdownRenderer h2 { font-size: 28px; color: #1a1a1a; margin-top: 22px; margin-bottom: 14px; }
            MarkdownRenderer h3 { font-size: 24px; color: #1a1a1a; margin-top: 20px; margin-bottom: 12px; }
            MarkdownRenderer h4 { font-size: 20px; color: #1a1a1a; margin-top: 18px; margin-bottom: 10px; }
            MarkdownRenderer p { line-height: 1.6; margin-bottom: 16px; }
            MarkdownRenderer a { color: #0078d7; text-decoration: none; }
            MarkdownRenderer a:hover { text-decoration: underline; }
            MarkdownRenderer code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: 'Courier New', monospace; }
            MarkdownRenderer pre { background-color: #f0f0f0; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace; overflow-x: auto; }
            MarkdownRenderer blockquote { border-left: 4px solid #cccccc; margin-left: 0; padding-left: 16px; color: #555555; }
            MarkdownRenderer img { max-width: 100%; }
            MarkdownRenderer table { border-collapse: collapse; }
            MarkdownRenderer th, td { border: 1px solid #ddd; padding: 8px; }
            MarkdownRenderer tr:nth-child(even) { background-color: #f2f2f2; }
        """)

        # Connect anchor click event
        self.anchorClicked.connect(self.on_link_clicked)

    def on_link_clicked(self, url):
        """Handle link clicking to navigate to other markdown files"""
        path = url.toString()
        if path.startswith('http://') or path.startswith('https://') or path.startswith('file://'):
            # Do nothing, we only handle relative paths.
            return

        # Emit signal to navigate to the document
        self.navigation_requested.emit(path)

    def render_markdown(self, text):
        """Convert markdown to HTML and display it"""
        # Convert markdown to HTML
        html = markdown.markdown(text, extensions=['extra', 'codehilite', 'tables'])
        html = f"""
        <html>
        <body>
          {html}
        </body>
        </html>
        """
        self.setHtml(html)


class MarkdownEditor(QTextEdit):
    """Widget for editing Markdown content"""

    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Courier New", 16, weight=500)
        self.setFont(font)

    def keyPressEvent(self, event):
        """Override keyPressEvent to handle navigation with Ctrl+Enter"""
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
            cursor = self.textCursor()
            block = cursor.block()
            line_text = block.text()

            # Check if the line contains a link
            link_match = re.search(r'\[.*?\]\((.*?)\)', line_text)
            if link_match:
                link_target = link_match.group(1)
                self.navigation_requested.emit(link_target)
                return

        # Default handling for other key events
        super().keyPressEvent(event)


class MarkdownWiki(QMainWindow):
    """Main application window for Markdown Wiki"""

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.is_view_mode = False
        self.unsaved_changes = False
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Markdown Wiki")
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
        self.md_editor.textChanged.connect(self.on_text_changed)
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

        # Setup actions and shortcuts
        self.setup_actions()

    def setup_actions(self):
        """Setup keyboard shortcuts and actions"""
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

    def set_project_directory(self, directory_path):
        """Set the project directory for the wiki"""
        self.project_dir = Path(directory_path)
        # Create directory if it doesn't exist
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Set the file system model root to this directory
        self.file_navigator.model.setRootPath(str(self.project_dir))
        self.file_navigator.tree_view.setRootIndex(self.file_navigator.model.index(str(self.project_dir)))

        self.status_bar.showMessage(f"Project opened: {directory_path}")

    def open_selected_path(self, path):
        """Open the file selected in the tree view"""
        path = Path(path)
        # If it's a directory, just expand/collapse it
        if path.is_dir():
            return
        self.open_file(path)

    def open_file(self, file_path):
        """Open and display a markdown file"""
        # Check if there are unsaved changes
        if self.unsaved_changes:
            if not self.confirm_discard_changes():
                return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.md_editor.setPlainText(content)
            self.md_renderer.render_markdown(content)

            self.current_file = file_path
            self.setWindowTitle(f"Markdown Wiki - {os.path.basename(file_path)}")

            self.unsaved_changes = False

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

            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.unsaved_changes = False
            self.status_bar.showMessage(f"Saved file: {os.path.basename(self.current_file)}")

            # Update renderer if in view mode
            if self.is_view_mode:
                self.md_renderer.render_markdown(content)

            # Remove * from WindowTitle
            self.setWindowTitle(self.windowTitle()[1:])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def focus_sidebar(self):
        """Handle Escape key to focus sidebar"""
        self.tree_view.setFocus()
        self.status_bar.showMessage("Sidebar focused")

    def toggle_view_mode(self):
        """Switch between edit and view mode"""
        self.is_view_mode = not self.is_view_mode

        if self.is_view_mode:
            # Switch to view mode
            self.md_editor.hide()
            self.md_renderer.show()
            # Update renderer with current content
            self.md_renderer.render_markdown(self.md_editor.toPlainText())
            self.status_bar.showMessage("View mode")
        else:
            # Switch to edit mode
            self.md_renderer.hide()
            self.md_editor.show()
            self.md_editor.setFocus()
            self.status_bar.showMessage("Edit mode")

    def navigate_to_file(self, target_path):
        """Navigate to a file based on a relative or absolute path"""
        if self.unsaved_changes:
            if not self.confirm_discard_changes():
                return

        # Check if the path is absolute or relative
        path_obj = Path(target_path)

        if not path_obj.is_absolute() and self.current_file:
            # Calculate relative path from current file's directory
            current_dir = Path(self.current_file).parent
            path_obj = (current_dir / path_obj).resolve()

        # Ensure the path is within the project directory
        try:
            # Convert to absolute and resolve any .. parts
            path_obj = path_obj.resolve()

            # Check if it's within project directory
            if self.project_dir not in path_obj.parents and path_obj != self.project_dir:
                self.status_bar.showMessage("Cannot navigate outside project directory")
                return

            # Check if file exists, create it if necessary
            if not path_obj.exists():
                self.status_bar.showMessage(f"File: {path_obj.name} does not exist.")
                return

            self.open_file(str(path_obj))

        except Exception as e:
            self.status_bar.showMessage(f"Navigation error: {str(e)}")

    def on_text_changed(self):
        """Handle text changes in the editor"""
        if not self.unsaved_changes:
            self.unsaved_changes = True
            # Add * to window title to indicate unsaved changes
            self.setWindowTitle(f"*{self.windowTitle()}")

    def confirm_discard_changes(self):
        """Ask the user to confirm discarding unsaved changes"""
        response = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )

        if response == QMessageBox.Save:
            self.save_file()
            return True
        elif response == QMessageBox.Discard:
            return True
        else:  # Cancel
            return False

    def closeEvent(self, event):
        """Handle application closing"""
        if self.unsaved_changes:
            if not self.confirm_discard_changes():
                event.ignore()
                return

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    wiki = MarkdownWiki()

    # Set the project directory - we'll use the current directory for this example
    # In a real app, you might want to ask the user for this or use a config file
    # wiki.set_project_directory(os.path.join(os.path.expanduser("~"), "MarkdownWiki"))
    wiki.set_project_directory("./wiki/")

    wiki.show()
    sys.exit(app.exec())
