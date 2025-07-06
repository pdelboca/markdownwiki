import os

from pathlib import Path

from PySide6.QtWidgets import (QWidget, QTreeView, QFileSystemModel, QVBoxLayout,
                               QMenu, QApplication, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, QDir, Signal, QFile
from PySide6.QtGui import QAction, QKeySequence


class WikiTreeView(QTreeView):
    """Custom TreeView for file navigation with specific keyboard handling"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        """Override keyPressEvent to handle Enter key for opening files/folders"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            index = self.currentIndex()
            if index.isValid():
                if self.isExpanded(index):
                    self.collapse(index)
                else:
                    self.expand(index)

                if index.data().endswith(".md") and not self.model().isDir(index):
                    self.window().set_edit_mode()
                return

        super().keyPressEvent(event)


class FileSystemNavigator(QWidget):
    status_message = Signal(str)
    selected_item = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cut_source_path = None

        self.tree_view = WikiTreeView(self)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_view.setHeaderHidden(True)

        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        self.model.setNameFilters(["*"])
        self.model.setNameFilterDisables(False)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tree_view)
        self.setLayout(self.layout)

        # Create actions
        self.create_actions()

    def setup_navigator(self, folder: str) -> None:
        """Sets the root path for the model and the tree view.

        Column names depends on model, so we are hiding it here.
        """
        root_index = self.model.setRootPath(folder)
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(root_index)
        self.tree_view.selectionModel().selectionChanged.connect(self.handle_selection_change)

        # Hide columns except name
        for col in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(col)

    def create_actions(self):
        # New File action
        self.new_file_action = QAction("New File", self)
        self.new_file_action.setShortcut(QKeySequence.New)
        self.new_file_action.triggered.connect(self.create_new_file)

        # Delete action
        self.delete_action = QAction("Delete", self)
        self.delete_action.setShortcut(QKeySequence.Delete)
        self.delete_action.triggered.connect(self.delete_selected)

        # Rename action
        self.rename_action = QAction("Rename", self)
        self.rename_action.setShortcut(Qt.Key_F2)
        self.rename_action.triggered.connect(self.rename_selected)

        # Cut action
        self.cut_action = QAction("Cut", self)
        self.cut_action.setShortcut(QKeySequence.Cut)
        self.cut_action.triggered.connect(self.cut_selected)

        # Paste action
        self.paste_action = QAction("Paste", self)
        self.paste_action.setShortcut(QKeySequence.Paste)
        self.paste_action.triggered.connect(self.paste_file)

        # Add actions to widget
        self.addAction(self.new_file_action)
        self.addAction(self.delete_action)
        self.addAction(self.rename_action)
        self.addAction(self.cut_action)
        self.addAction(self.paste_action)

    def update_status(self, message):
        self.window().statusBar().showMessage(message)

    def get_current_directory(self):
        """Gets the directory of the current selected element.

        If not selected element, it returns the rootPath of the model which is
        our Project Path.
        """
        index = self.tree_view.currentIndex()
        if index.isValid():
            if self.model.isDir(index):
                return self.model.filePath(index)
            return self.model.filePath(index.parent())
        return self.model.rootPath()

    def get_selected_path(self):
        """Gets the path of the selected item or None."""
        index = self.tree_view.currentIndex()
        return self.model.filePath(index) if index.isValid() else None

    def create_new_file(self):
        current_dir = self.get_current_directory()
        if not current_dir:
            return

        file_name, ok = QInputDialog.getText(self, "New File", "Enter file name:")

        if ok and file_name:
            try:
                new_file = Path(current_dir, file_name)
                new_file.touch(exist_ok=False)
                self.update_status(f"Created file: {new_file}")
            except FileExistsError:
                self.update_status("A file with that name already exist. Nothing has been done.")
            except Exception as e:
                self.update_status(f"Error creating file: {str(e)}")

    def delete_selected(self):
        path = self.get_selected_path()
        if not path:
            return

        confirm = QMessageBox.question(
            self, "Delete File",
            f"Are you sure you want to delete:\n{os.path.basename(path)}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            if os.path.isdir(path):
                success = QDir(path).removeRecursively()
            else:
                success = QFile.remove(path)

            if success:
                self.update_status(f"Deleted: {path}")
            else:
                self.update_status(f"Error deleting: {path}")

    def rename_selected(self):
        index = self.tree_view.currentIndex()
        if index.isValid():
            file = Path(self.model.filePath(index))
            name = file.stem
            folder = file.parent

            new_name, ok = QInputDialog.getText(self, "New File", "Enter file name:")

            if not ok:
                self.update_status("Nothing has been done.")
                return

            if not new_name:
                self.update_status("No new name has been given. Nothing has been done.")
                return

            if new_name == name:
                self.update_status("New name and old name are the same. Nothing has been done.")
                return

            new_file = Path.joinpath(folder, new_name)

            if new_file.exists():
                self.update_status("File with this name already exists. Nothing has been done.")
                return

            try:
                file.rename(new_file)
            except IsADirectoryError:
                QMessageBox.warning(self, "Error", "Source is a file but destination a directory.")
            except NotADirectoryError:
                QMessageBox.warning(self, "Error", "Source is a directory but destination a file.")
            except PermissionError:
                # Since we have a managed PROJECT_PATH this should never happen.
                QMessageBox.warning(self, "Error", "Operation not permitted.")
            except OSError:
                QMessageBox.warning(self, "Error", "File with this name already exists.")
            else:
                self.update_status("Item renamed successfuly.")

    def cut_selected(self):
        path = self.get_selected_path()
        if not path:
            return

        self.cut_source_path = path
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
        self.update_status(f"Cut: {os.path.basename(path)}")

    def paste_file(self):
        if not self.cut_source_path:
            return

        dest_dir = self.get_current_directory()
        if not dest_dir:
            return

        source_path = self.cut_source_path
        file_name = os.path.basename(source_path)
        dest_path = os.path.join(dest_dir, file_name)

        if source_path == dest_path:
            self.update_status("Source and destination are the same")
            return

        if os.path.exists(dest_path):
            self.update_status(f"File already exists: {dest_path}")
            return

        # Move the file
        if QFile.rename(source_path, dest_path):
            self.update_status(f"Moved to: {dest_path}")
        else:
            # Fallback to copy+delete if rename fails (different filesystems)
            if QFile.copy(source_path, dest_path):
                QFile.remove(source_path)
                self.update_status(f"Moved to: {dest_path}")
            else:
                self.update_status("Failed to move file")

        self.cut_source_path = None

    def handle_selection_change(self):
        """Emits a selected_item event with the selected item's path."""
        path = self.get_selected_path()
        if path:
            self.selected_item.emit(path)
            self.update_status(f"Selected: {os.path.basename(path)}")

    def show_context_menu(self, position):
        menu = QMenu()
        menu.addAction(self.new_file_action)

        if self.get_selected_path():
            menu.addAction(self.delete_action)
            menu.addAction(self.rename_action)
            menu.addAction(self.cut_action)

        if self.cut_source_path:
            menu.addAction(self.paste_action)

        menu.exec_(self.tree_view.viewport().mapToGlobal(position))
